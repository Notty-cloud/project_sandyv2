"""
ai_engine/face_pipeline.py

Face embedding pipeline — fully self-contained, no C compilation required.

Uses ONNX Runtime to run:
  1. SCRFD-10GF  (det_10g.onnx)      — Face detection + 5-point landmarks
  2. ArcFace R50 (w600k_r50.onnx)  — 512-dimensional face embedding

Both models come from InsightFace's buffalo_l pack.
Model files must be placed at:
  ai_engine/models/det_10g.onnx        (~16 MB)
  ai_engine/models/w600k_r50.onnx     (~250 MB)

See ai_engine/models/.gitkeep for download instructions.

Pipeline
--------
Step 1 — Face Detection
    SCRFD-10GF (RetinaFace-class accuracy) detects all faces in the image and
    returns bounding boxes with confidence scores and 5-point facial landmarks.

Step 2 — Landmark Alignment
    A partial affine transform maps the 5 detected landmarks onto ArcFace's
    canonical reference positions, producing a 112×112 aligned BGR crop.

Step 3 — Pixel Normalization
    pixel = (pixel - 127.5) / 128.0  →  values ≈ [-1, 1]
    Transpose and batch: (H, W, C) → (1, C, H, W) float32.

Step 4 — ONNX Inference
    ResNet50 ArcFace produces a raw 512-dimensional embedding vector.

Step 5 — L2 Normalization
    Unit-normalize so cosine similarity equals the dot product.
"""

import io
import logging
import threading
import warnings
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ai_engine.exceptions import (
    FaceNotDetectedError,
    LowQualityFaceError,
    MultipleFacesWarning,
)

logger = logging.getLogger(__name__)

# ─── PATHS ────────────────────────────────────────────────────────────────────

MODELS_DIR = Path(__file__).parent / 'models'
DETECTOR_MODEL_PATH  = MODELS_DIR / 'det_10g.onnx'
RECOGNIZER_MODEL_PATH = MODELS_DIR / 'w600k_r50.onnx'

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

DETECTION_INPUT_SIZE = (640, 640)  # SCRFD-10GF fixed input resolution (W, H)
ALIGNED_SIZE = 112                 # ArcFace canonical face size in pixels
QUALITY_THRESHOLD = 0.6            # Minimum SCRFD confidence to accept a face
DET_SCORE_THRESHOLD = 0.5          # SCRFD per-anchor score threshold
NMS_IOU_THRESHOLD = 0.4            # IoU threshold for non-maximum suppression
NUM_ANCHORS_PER_CELL = 2           # SCRFD anchors generated per feature map cell
STRIDES = [8, 16, 32]              # SCRFD feature pyramid stride levels

# ArcFace canonical landmark positions in 112×112 space.
# Source: insightface/utils/face_align.py  (arcface_dst)
ARCFACE_DST = np.array([
    [38.2946, 51.6963],  # left eye
    [73.5318, 51.5014],  # right eye
    [56.0252, 71.7366],  # nose tip
    [41.5493, 92.3655],  # left mouth corner
    [70.7299, 92.2041],  # right mouth corner
], dtype=np.float32)

# ─── SINGLETON MODEL LOADERS ──────────────────────────────────────────────────

_detector_session = None
_detector_lock = threading.Lock()

_recognizer_session = None
_recognizer_lock = threading.Lock()


def _get_detector():
    """Thread-safe lazy loader for the SCRFD-10GF detection ONNX session."""
    global _detector_session
    if _detector_session is None:
        with _detector_lock:
            if _detector_session is None:
                if not DETECTOR_MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f'SCRFD detection model not found at: {DETECTOR_MODEL_PATH}\n'
                        'Download det_10g.onnx from the InsightFace buffalo_l pack.\n'
                        'See ai_engine/models/.gitkeep for instructions.'
                    )
                import onnxruntime as ort
                _detector_session = ort.InferenceSession(
                    str(DETECTOR_MODEL_PATH),
                    providers=['CPUExecutionProvider'],
                )
                logger.info('SCRFD detector loaded: %s', DETECTOR_MODEL_PATH.name)
    return _detector_session


def _get_recognizer():
    """Thread-safe lazy loader for the ArcFace R50 ONNX session."""
    global _recognizer_session
    if _recognizer_session is None:
        with _recognizer_lock:
            if _recognizer_session is None:
                if not RECOGNIZER_MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f'ArcFace model not found at: {RECOGNIZER_MODEL_PATH}\n'
                        'Download w600k_r50.onnx from the InsightFace model zoo.\n'
                        'See ai_engine/models/.gitkeep for instructions.'
                    )
                import onnxruntime as ort
                _recognizer_session = ort.InferenceSession(
                    str(RECOGNIZER_MODEL_PATH),
                    providers=['CPUExecutionProvider'],
                )
                logger.info('ArcFace recognizer loaded: %s', RECOGNIZER_MODEL_PATH.name)
    return _recognizer_session


# ─── IMAGE INPUT NORMALIZER ───────────────────────────────────────────────────

def _to_bgr_array(image_input):
    """
    Convert various image input types to a BGR uint8 np.ndarray.

    OpenCV and InsightFace models use the BGR channel convention throughout.

    Accepts:
        str or Path              — file path
        bytes                    — raw image bytes
        file-like with .read()   — Django UploadedFile or io.BytesIO
        PIL.Image                — any mode
        np.ndarray               — assumed BGR uint8 (OpenCV convention)
    """
    if isinstance(image_input, (str, Path)):
        img_rgb = np.array(Image.open(image_input).convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()

    if isinstance(image_input, bytes):
        img_rgb = np.array(Image.open(io.BytesIO(image_input)).convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()

    if hasattr(image_input, 'read'):
        if hasattr(image_input, 'seek'):
            image_input.seek(0)
        data = image_input.read()
        img_rgb = np.array(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()

    if isinstance(image_input, Image.Image):
        img_rgb = np.array(image_input.convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()

    if isinstance(image_input, np.ndarray):
        return image_input.astype(np.uint8, copy=False)

    raise TypeError(
        f'Unsupported image input type: {type(image_input).__name__}. '
        'Expected: str, Path, bytes, file-like, PIL.Image, or np.ndarray.'
    )


# ─── SCRFD POST-PROCESSING UTILITIES ─────────────────────────────────────────

def _generate_anchor_centers(input_h, input_w, stride):
    """
    Generate anchor center coordinates for one SCRFD stride level.

    SCRFD places NUM_ANCHORS_PER_CELL anchors at each feature map cell center.
    Cell (row, col) maps to pixel coordinate (col * stride, row * stride).

    Returns:
        centers (np.ndarray): shape (fh * fw * NUM_ANCHORS_PER_CELL, 2), float32
                              columns are (x_center, y_center) in input pixels
    """
    fh = input_h // stride
    fw = input_w // stride
    # np.mgrid[:fh, :fw] → shape (2, fh, fw): row indices, then col indices
    # [::-1] swaps order → (col_grid, row_grid) which is (x, y)
    centers = np.stack(np.mgrid[:fh, :fw][::-1], axis=-1).astype(np.float32)
    centers = centers.reshape(-1, 2) * stride                                # (fh*fw, 2)
    centers = np.tile(centers[:, np.newaxis, :], (1, NUM_ANCHORS_PER_CELL, 1)).reshape(-1, 2)
    return centers


def _distance2bbox(centers, bbox_pred):
    """
    Decode SCRFD distance predictions into (x1, y1, x2, y2) bounding boxes.
    bbox_pred columns: [left, top, right, bottom] distances from anchor center.
    """
    x1 = centers[:, 0] - bbox_pred[:, 0]
    y1 = centers[:, 1] - bbox_pred[:, 1]
    x2 = centers[:, 0] + bbox_pred[:, 2]
    y2 = centers[:, 1] + bbox_pred[:, 3]
    return np.stack([x1, y1, x2, y2], axis=-1)


def _distance2kps(centers, kps_pred):
    """
    Decode SCRFD landmark distance predictions into (x, y) coordinate pairs.
    kps_pred has 10 columns: [dx0, dy0, dx1, dy1, ..., dx4, dy4].
    """
    kps_list = []
    for i in range(0, kps_pred.shape[1], 2):
        kps_list.append(centers[:, 0] + kps_pred[:, i])
        kps_list.append(centers[:, 1] + kps_pred[:, i + 1])
    return np.stack(kps_list, axis=-1)


def _nms(bboxes, scores, iou_threshold):
    """IoU-based non-maximum suppression. Returns indices of surviving detections."""
    x1, y1, x2, y2 = bboxes[:, 0], bboxes[:, 1], bboxes[:, 2], bboxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[1:][iou <= iou_threshold]
    return keep


def _scrfd_detect(img_bgr):
    """
    Run SCRFD-10GF face detection.

    The model outputs 9 tensors (3 strides × score + bbox + kps):
        net_outs[0..2]  — sigmoid scores per stride  (shape: N×1)
        net_outs[3..5]  — bbox distance preds         (shape: N×4)
        net_outs[6..8]  — landmark distance preds     (shape: N×10)

    Returns:
        bboxes (np.ndarray): shape (M, 5)    — (x1, y1, x2, y2, score)
        kpss   (np.ndarray): shape (M, 5, 2) — 5 (x, y) landmarks per face
        Both in original image pixel coordinates.
    """
    orig_h, orig_w = img_bgr.shape[:2]
    det_w, det_h = DETECTION_INPUT_SIZE

    # Resize to model input size
    img_resized = cv2.resize(img_bgr, (det_w, det_h))

    # Preprocess: normalize to [-1, 1], transpose to NCHW
    blob = img_resized.astype(np.float32)
    blob = (blob - 127.5) / 128.0
    blob = blob.transpose(2, 0, 1)[np.newaxis]   # (1, 3, H, W)

    session = _get_detector()
    input_name = session.get_inputs()[0].name
    net_outs = session.run(None, {input_name: blob})

    # Scale factors to map detections back to original image coordinates
    scale_x = orig_w / det_w
    scale_y = orig_h / det_h

    fmc = len(STRIDES)   # 3 — separates score / bbox / kps output groups
    all_scores, all_bboxes, all_kpss = [], [], []

    for idx, stride in enumerate(STRIDES):
        # The ONNX outputs are already sigmoid-activated for scores
        scores    = net_outs[idx].reshape(-1)          # (N,)
        # Multiply predictions by stride to get pixel-space distances
        bbox_pred = net_outs[idx + fmc].reshape(-1, 4)   * stride  # (N, 4)
        kps_pred  = net_outs[idx + fmc * 2].reshape(-1, 10) * stride  # (N, 10)

        # Filter by detection score threshold
        pos_mask = scores >= DET_SCORE_THRESHOLD
        if not np.any(pos_mask):
            continue

        centers = _generate_anchor_centers(det_h, det_w, stride)
        all_scores.append(scores[pos_mask])
        all_bboxes.append(_distance2bbox(centers[pos_mask], bbox_pred[pos_mask]))
        all_kpss.append(_distance2kps(centers[pos_mask], kps_pred[pos_mask]).reshape(-1, 5, 2))

    if not all_scores:
        return np.empty((0, 5), dtype=np.float32), np.empty((0, 5, 2), dtype=np.float32)

    all_scores = np.concatenate(all_scores)
    all_bboxes = np.concatenate(all_bboxes)
    all_kpss   = np.concatenate(all_kpss)

    # Non-maximum suppression
    keep = _nms(all_bboxes, all_scores, NMS_IOU_THRESHOLD)
    all_bboxes = all_bboxes[keep]
    all_scores = all_scores[keep]
    all_kpss   = all_kpss[keep]

    # Map coordinates back to original image resolution
    all_bboxes[:, [0, 2]] *= scale_x
    all_bboxes[:, [1, 3]] *= scale_y
    all_kpss[:, :, 0]     *= scale_x
    all_kpss[:, :, 1]     *= scale_y

    bboxes_with_score = np.hstack([all_bboxes, all_scores[:, np.newaxis]])
    return bboxes_with_score, all_kpss


# ─── STEP 2: LANDMARK ALIGNMENT ──────────────────────────────────────────────

def _norm_crop(img_bgr, landmarks, image_size=ALIGNED_SIZE):
    """
    Step 2 — Landmark Alignment.

    Estimates a partial affine transform (rotation + uniform scale + translation)
    that maps the 5 detected facial landmarks onto the ArcFace canonical reference
    positions, then warps the image to produce a 112×112 aligned face crop.

    Args:
        img_bgr   (np.ndarray): full BGR image
        landmarks (np.ndarray): shape (5, 2), detected (x, y) landmark coordinates
        image_size (int):       output size in pixels (112 for ArcFace)

    Returns:
        aligned (np.ndarray): shape (image_size, image_size, 3), BGR uint8
    """
    dst = ARCFACE_DST * (image_size / 112.0)
    M, _ = cv2.estimateAffinePartial2D(landmarks.astype(np.float32), dst)
    return cv2.warpAffine(img_bgr, M, (image_size, image_size), borderValue=0)


# ─── STEPS 1 + 2: DETECT AND ALIGN ──────────────────────────────────────────

def detect_and_align(image_input):
    """
    Step 1 — Face Detection:
        Run SCRFD-10GF to locate faces and extract 5-point landmarks.

    Step 2 — Landmark Alignment:
        Affine-warp the largest detected face into the 112×112 ArcFace frame.

    Args:
        image_input: str, Path, bytes, file-like, PIL.Image, or np.ndarray

    Returns:
        aligned       (np.ndarray): shape (112, 112, 3), BGR uint8
        quality_score (float):      SCRFD detection confidence, 0.0–1.0

    Raises:
        FaceNotDetectedError:  no face found in the image
        MultipleFacesWarning:  more than one face detected (largest face is used)
    """
    img_bgr = _to_bgr_array(image_input)

    # Step 1: Detect
    bboxes, kpss = _scrfd_detect(img_bgr)

    if len(bboxes) == 0:
        raise FaceNotDetectedError(
            'No face detected in the image. '
            'Ensure good lighting, a front-facing pose, and no obstructions.'
        )

    if len(bboxes) > 1:
        warnings.warn(
            f'{len(bboxes)} faces detected. Using the largest bounding box.',
            MultipleFacesWarning,
            stacklevel=2,
        )
        logger.warning('Multiple faces detected (%d). Selecting the largest.', len(bboxes))

    # Select the face with the largest bounding box area
    areas = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
    idx = int(np.argmax(areas))
    quality_score = float(bboxes[idx, 4])
    landmarks = kpss[idx]  # (5, 2)

    # Step 2: Align
    aligned = _norm_crop(img_bgr, landmarks)

    return aligned, quality_score


# ─── STEP 3: PIXEL NORMALIZATION ─────────────────────────────────────────────

def _preprocess_for_arcface(aligned_bgr):
    """
    Step 3 — Pixel Normalization.

    1. Cast to float32.
    2. Normalize: pixel = (pixel - 127.5) / 128.0  →  range ≈ [-1, 1].
    3. Transpose (H, W, C) → (C, H, W).
    4. Add batch dim → (1, C, H, W).

    Note: InsightFace passes BGR (not RGB) into the ArcFace ONNX model.
    Do NOT convert to RGB before this step.
    """
    blob = aligned_bgr.astype(np.float32)
    blob = (blob - 127.5) / 128.0
    blob = blob.transpose(2, 0, 1)
    blob = np.expand_dims(blob, axis=0)   # (1, 3, 112, 112)
    return blob


# ─── STEPS 4 + 5: EMBEDDING EXTRACTION ──────────────────────────────────────

def extract_embedding(image_input):
    """
    Full pipeline: detection → alignment → normalization → inference → L2 norm.

    Args:
        image_input: str, Path, bytes, file-like, PIL.Image, or np.ndarray

    Returns:
        dict:
            embedding     (np.ndarray) — shape (512,), dtype float32, L2-normalized
            quality_score (float)      — SCRFD detection confidence, 0.0–1.0
            face_count    (int)        — number of faces found in image

    Raises:
        FaceNotDetectedError:   no face found in the image
        LowQualityFaceError:    detection confidence below QUALITY_THRESHOLD (0.6)
        MultipleFacesWarning:   more than one face detected (largest used, continues)
        FileNotFoundError:      an ONNX model file is missing from ai_engine/models/
    """
    # Steps 1–2: Detection + Alignment
    aligned_bgr, quality_score = detect_and_align(image_input)

    if quality_score < QUALITY_THRESHOLD:
        raise LowQualityFaceError(
            f'Detection confidence {quality_score:.3f} is below the minimum threshold '
            f'{QUALITY_THRESHOLD}. Provide a clearer, well-lit, front-facing image.'
        )

    # Step 3: Pixel normalization → (1, 3, 112, 112) float32
    blob = _preprocess_for_arcface(aligned_bgr)

    # Step 4: ONNX inference — ResNet100 ArcFace → (1, 512) raw embedding
    session = _get_recognizer()
    input_name  = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    raw_embedding = session.run([output_name], {input_name: blob})[0][0]  # (512,)

    # Step 5: L2 normalization → unit vector (cosine similarity == dot product)
    norm = np.linalg.norm(raw_embedding)
    embedding = (raw_embedding / norm) if norm > 0.0 else raw_embedding

    return {
        'embedding': embedding.astype(np.float32),
        'quality_score': round(quality_score, 4),
        'face_count': 1,
    }


# ─── STANDALONE TEST ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s  %(message)s')

    if len(sys.argv) < 2:
        print('Usage: python face_pipeline.py <image_path>')
        sys.exit(1)

    path = sys.argv[1]
    print(f'\nProcessing: {path}')

    result = extract_embedding(path)
    emb = result['embedding']

    print(f'  Embedding shape  : {emb.shape}')
    print(f'  Embedding dtype  : {emb.dtype}')
    print(f'  L2 norm          : {np.linalg.norm(emb):.6f}  (expected ~1.0)')
    print(f'  Quality score    : {result["quality_score"]}')
    print(f'  First 8 dims     : {emb[:8]}')


import io
import logging
import threading
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

from ai_engine.exceptions import (
    FaceNotDetectedError,
    LowQualityFaceError,
    MultipleFacesWarning,
)

logger = logging.getLogger(__name__)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

# Path to the ArcFace ONNX model (not committed — must be placed manually).
ONNX_MODEL_PATH = Path(__file__).parent / 'models' / 'w600k_r50.onnx'

# Aligned face size expected by ArcFace (do not change).
ALIGNED_SIZE = 112

# Minimum detection confidence accepted before raising LowQualityFaceError.
QUALITY_THRESHOLD = 0.6

# ─── SINGLETON: DETECTOR ──────────────────────────────────────────────────────

_detector = None
_detector_lock = threading.Lock()


def _get_detector():
    """
    Thread-safe lazy loader for the face detector.

    Loads InsightFace buffalo_l detection model (SCRFD-10GF / RetinaFace-class).
    Model weights are downloaded automatically on first call to ~/.insightface/.
    """
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                # allowed_modules=['detection'] loads only the detector, not the
                # recognizer — we handle recognition explicitly via ONNX Runtime.
                from insightface.app import FaceAnalysis

                app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection'])
                app.prepare(ctx_id=-1)  # ctx_id=-1 = CPU; set 0 for first GPU
                _detector = app.det_model
                logger.info('Face detector loaded: buffalo_l/det_10g.onnx (SCRFD)')
    return _detector


# ─── SINGLETON: RECOGNIZER ────────────────────────────────────────────────────

_recognizer = None
_recognizer_lock = threading.Lock()


def _get_recognizer():
    """
    Thread-safe lazy loader for the ArcFace ONNX recognition model.

    Expects w600k_r50.onnx at ai_engine/models/w600k_r50.onnx.
    Download from:
        https://github.com/deepinsight/insightface/tree/master/model_zoo
    """
    global _recognizer
    if _recognizer is None:
        with _recognizer_lock:
            if _recognizer is None:
                if not ONNX_MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f'ArcFace ONNX model not found at: {ONNX_MODEL_PATH}\n'
                        'Download w600k_r50.onnx from the InsightFace model zoo '
                        'and place it at ai_engine/models/w600k_r50.onnx'
                    )
                import onnxruntime as ort

                _recognizer = ort.InferenceSession(
                    str(ONNX_MODEL_PATH),
                    providers=['CPUExecutionProvider'],
                )
                logger.info('ArcFace ONNX model loaded: %s', ONNX_MODEL_PATH.name)
    return _recognizer


# ─── IMAGE INPUT NORMALIZER ───────────────────────────────────────────────────

def _to_bgr_array(image_input):
    """
    Convert various image input types to a BGR uint8 np.ndarray.

    InsightFace uses the OpenCV BGR convention throughout, so all inputs are
    converted to BGR before any processing.

    Accepts:
        str or Path  — file path
        bytes        — raw image bytes
        PIL.Image    — PIL image (any mode)
        np.ndarray   — assumed BGR uint8 (OpenCV convention)
    """
    if isinstance(image_input, (str, Path)):
        # Load via Pillow (handles JPEG, PNG, WEBP, etc.), then convert to BGR
        img_rgb = np.array(Image.open(image_input).convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()  # RGB → BGR

    if isinstance(image_input, bytes):
        img_rgb = np.array(Image.open(io.BytesIO(image_input)).convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()  # RGB → BGR

    if isinstance(image_input, Image.Image):
        img_rgb = np.array(image_input.convert('RGB'), dtype=np.uint8)
        return img_rgb[:, :, ::-1].copy()  # RGB → BGR

    if isinstance(image_input, np.ndarray):
        # Caller is responsible for passing BGR (OpenCV convention)
        return image_input.astype(np.uint8, copy=False)

    raise TypeError(
        f'Unsupported image input type: {type(image_input).__name__}. '
        'Expected: str, Path, bytes, PIL.Image, or np.ndarray.'
    )


# ─── STEP 1 + 2: DETECT AND ALIGN ────────────────────────────────────────────

def detect_and_align(image_input):
    """
    Step 1 — Face Detection
        Run RetinaFace (buffalo_l SCRFD) detector to locate faces and extract
        5-point landmarks (left eye, right eye, nose, left mouth, right mouth).

    Step 2 — Landmark Alignment
        Use insightface.utils.face_align.norm_crop() to apply an affine warp
        mapping the 5 detected landmarks to the ArcFace canonical reference
        positions, producing a 112×112 BGR aligned face crop.

    Args:
        image_input: str, Path, bytes, PIL.Image, or np.ndarray

    Returns:
        aligned (np.ndarray): shape (112, 112, 3), BGR uint8
        quality_score (float): detection confidence from SCRFD, 0.0–1.0

    Raises:
        FaceNotDetectedError:  no face found in image
        MultipleFacesWarning:  more than one face detected (largest used)
    """
    from insightface.utils.face_align import norm_crop

    img_bgr = _to_bgr_array(image_input)

    detector = _get_detector()

    # ── Step 1: Detection ─────────────────────────────────────────────────────
    # bboxes: (N, 5)   — x1, y1, x2, y2, confidence_score
    # kpss:   (N, 5, 2) — 5 landmarks, each as (x, y) pixel coordinates
    bboxes, kpss = detector.detect(img_bgr, input_size=(640, 640))

    if bboxes is None or len(bboxes) == 0:
        raise FaceNotDetectedError(
            'No face detected in the image. '
            'Ensure good lighting, a front-facing pose, and no obstructions.'
        )

    if len(bboxes) > 1:
        warnings.warn(
            f'{len(bboxes)} faces detected. Using the largest bounding box.',
            MultipleFacesWarning,
            stacklevel=2,
        )
        logger.warning('Multiple faces detected (%d). Selecting the largest.', len(bboxes))

    # Select the face with the largest bounding-box area
    areas = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
    idx = int(np.argmax(areas))

    # Confidence score reported by the SCRFD/RetinaFace detector
    detection_confidence = float(bboxes[idx, 4])

    # 5 landmark points for the selected face — shape (5, 2)
    kps = kpss[idx]

    # ── Step 2: Landmark Alignment ────────────────────────────────────────────
    # norm_crop applies an affine transform so the 5 detected landmarks map
    # to the arcface_dst reference coordinates in the 112×112 canonical frame.
    aligned = norm_crop(img_bgr, landmark=kps, image_size=ALIGNED_SIZE)

    return aligned, detection_confidence


# ─── STEP 3: PIXEL NORMALIZATION ─────────────────────────────────────────────

def _preprocess_for_arcface(aligned_bgr):
    """
    Step 3 — Pixel Normalization

    Prepares the aligned BGR face crop for ArcFace ONNX inference:
        1. Cast to float32
        2. Normalize:  pixel = (pixel - 127.5) / 128.0  → range ≈ [-1, 1]
        3. Transpose:  (H, W, C) → (C, H, W)
        4. Batch dim:  (C, H, W) → (1, C, H, W)

    Note: InsightFace keeps BGR channel order all the way through to the ONNX
    model. Do NOT convert to RGB before this step.

    Args:
        aligned_bgr (np.ndarray): shape (112, 112, 3), dtype uint8, BGR

    Returns:
        blob (np.ndarray): shape (1, 3, 112, 112), dtype float32
    """
    blob = aligned_bgr.astype(np.float32)        # uint8 → float32
    blob = (blob - 127.5) / 128.0                # center and scale to ≈ [-1, 1]
    blob = blob.transpose(2, 0, 1)               # (H, W, C) → (C, H, W)
    blob = np.expand_dims(blob, axis=0)          # (C, H, W) → (1, C, H, W)
    return blob


# ─── STEP 4 + 5: EMBEDDING EXTRACTION ────────────────────────────────────────

def extract_embedding(image_input):
    """
    Full pipeline: detection → alignment → normalization → ONNX inference → L2 norm.

    Args:
        image_input: str, Path, bytes, PIL.Image, or np.ndarray

    Returns:
        dict:
            embedding     (np.ndarray) — shape (512,), dtype float32, L2-normalized unit vector
            quality_score (float)      — detection confidence from RetinaFace, 0.0–1.0
            face_count    (int)        — number of faces found (pipeline uses the largest)

    Raises:
        FaceNotDetectedError: no face found in the image
        LowQualityFaceError:  detection confidence below QUALITY_THRESHOLD (0.6)
        MultipleFacesWarning: more than one face detected (largest used, execution continues)
        FileNotFoundError:    w600k_r50.onnx model file is missing
    """
    # ── Steps 1–2: Detection + Alignment ──────────────────────────────────────
    aligned_bgr, quality_score = detect_and_align(image_input)

    if quality_score < QUALITY_THRESHOLD:
        raise LowQualityFaceError(
            f'Detection confidence {quality_score:.3f} is below the minimum threshold '
            f'{QUALITY_THRESHOLD}. Provide a clearer, well-lit, front-facing image.'
        )

    # ── Step 3: Pixel Normalization ───────────────────────────────────────────
    blob = _preprocess_for_arcface(aligned_bgr)  # (1, 3, 112, 112) float32

    # ── Step 4: ONNX Inference ────────────────────────────────────────────────
    session = _get_recognizer()
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    # Run ResNet100 ArcFace inference; output shape: (1, 512)
    raw_output = session.run([output_name], {input_name: blob})[0]
    raw_embedding = raw_output[0]  # (512,) float32

    # ── Step 5: L2 Normalization ──────────────────────────────────────────────
    # Unit-normalize so that cosine similarity reduces to a simple dot product.
    # This matches the convention used in student_embeddings for vector search.
    norm = np.linalg.norm(raw_embedding)
    embedding = (raw_embedding / norm) if norm > 0.0 else raw_embedding

    return {
        'embedding': embedding.astype(np.float32),
        'quality_score': round(quality_score, 4),
        'face_count': 1,
    }


# ─── STANDALONE TEST ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO, format='%(levelname)s  %(message)s')

    if len(sys.argv) < 2:
        print('Usage: python face_pipeline.py <image_path>')
        sys.exit(1)

    path = sys.argv[1]
    print(f'\nProcessing: {path}')

    result = extract_embedding(path)
    emb = result['embedding']

    print(f'  Embedding shape  : {emb.shape}')
    print(f'  Embedding dtype  : {emb.dtype}')
    print(f'  L2 norm          : {np.linalg.norm(emb):.6f}  (expected ~1.0)')
    print(f'  Quality score    : {result["quality_score"]}')
    print(f'  First 8 dims     : {emb[:8]}')
