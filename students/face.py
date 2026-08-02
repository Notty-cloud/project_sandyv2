"""
Face recognition utility for Project Sandy.

Uses DeepFace with the Facenet512 model (512-dim embeddings).
Model weights (~90MB) are downloaded automatically on first use
and cached at ~/.deepface/weights/.

Swap extract_embedding() with a different model by changing MODEL_NAME.
The rest of the system (enrollment, identification, cosine similarity)
requires exactly 512 dimensions — update the DB schema if you change this.
"""
import io
import logging
import os
import sys
import tempfile

import numpy as np

# Quieten TensorFlow's startup logging. It emits several INFO/WARNING lines per
# process — no GPU present, oneDNN enabled, CPU instruction sets — which are
# purely informational but bury real errors in deploy logs.
#
# These must be set before TensorFlow is imported; DeepFace is imported lazily
# inside the functions below, so setting them here is early enough. setdefault
# leaves any operator override in place for debugging.
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')   # hide INFO and WARNING
os.environ.setdefault('GLOG_minloglevel', '2')
os.environ.setdefault('AUTOGRAPH_VERBOSITY', '0')
os.environ.setdefault('KMP_WARNINGS', '0')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# TF_ENABLE_ONEDNN_OPTS=0 would silence two further lines, but it disables the
# oneDNN kernels themselves — a real CPU inference slowdown on a box with no
# GPU. Not worth trading throughput for two log lines.

# Force UTF-8 stdout/stderr so DeepFace's emoji logger doesn't crash on
# Windows consoles that use cp1252 (causes UnicodeEncodeError during model
# weight downloads, silently killing every detector backend).
for _stream in ('stdout', 'stderr'):
    _s = getattr(sys, _stream)
    if hasattr(_s, 'buffer') and getattr(_s, 'encoding', 'utf-8').lower() != 'utf-8':
        setattr(sys, _stream, io.TextIOWrapper(_s.buffer, encoding='utf-8', errors='replace'))

MODEL_NAME = 'Facenet512'      # 512-dim output, matches student_embeddings schema

# Order matters, and not for the reason it looks like.
#
# Each detector crops and aligns the face differently, and Facenet512 is
# sensitive to alignment — so two embeddings are only comparable when the same
# detector produced them. Because the loop below takes whichever detector
# succeeds first, putting the least reliable one first made the choice depend on
# whether it happened to fail: the same person could be enrolled via retinaface
# and later recognised via opencv, yielding a poor similarity score for no
# reason other than the crop.
#
# retinaface leads because it is the most accurate and succeeds on almost
# everything, so in practice one detector is used throughout and embeddings stay
# comparable. opencv is kept last as a genuine fallback rather than the default.
# All three are pre-fetched at image build time (scripts/warm_face_models.py).
DETECTORS = ['retinaface', 'mtcnn', 'opencv']


def extract_embedding(image_file):
    """
    Extract a 512-dim face embedding from an uploaded image file.

    Args:
        image_file: Django InMemoryUploadedFile or file-like object

    Returns:
        dict with keys:
          embedding     (list[float])  — 512 floats, unit-normalized
          quality_score (float)        — face detection confidence 0.0–1.0
          face_count    (int)          — number of faces detected

    Raises:
        ValueError: if no face is detected in the image
        Exception:  for other DeepFace / IO errors
    """
    from deepface import DeepFace

    # Seek to start in case the file was already partially read
    if hasattr(image_file, 'seek'):
        image_file.seek(0)

    # Write to a temp file — DeepFace works best with file paths
    suffix = _get_suffix(image_file)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        if hasattr(image_file, 'chunks'):
            for chunk in image_file.chunks():
                tmp.write(chunk)
        else:
            tmp.write(image_file.read())
        tmp_path = tmp.name

    results = None
    used_detector = None

    try:
        for detector in DETECTORS:
            try:
                results = DeepFace.represent(
                    img_path=tmp_path,
                    model_name=MODEL_NAME,
                    detector_backend=detector,
                    enforce_detection=True,
                    align=True,
                )
                used_detector = detector
                break
            except Exception:
                continue
    finally:
        os.unlink(tmp_path)

    if not results:
        raise ValueError(
            'No face detected. Please ensure good lighting, face the camera directly, '
            'and avoid obstructions. The photo must contain a clear, visible face.'
        )

    # Use the highest-confidence face if multiple are detected
    best = max(results, key=lambda r: r.get('face_confidence', 0))
    raw_embedding = np.array(best['embedding'], dtype=np.float32)

    # Normalize to unit vector for cosine similarity
    norm = np.linalg.norm(raw_embedding)
    if norm > 0:
        raw_embedding = raw_embedding / norm

    return {
        'embedding': raw_embedding.tolist(),
        'quality_score': round(float(best.get('face_confidence', 0.0)), 4),
        'face_count': len(results),
        # Recorded so a poor similarity between two photos of one person can be
        # attributed to a detector change rather than guessed at.
        'detector': used_detector,
    }


def extract_all_embeddings(image_file):
    """
    Extract 512-dim embeddings for every face detected in an image.

    Returns:
        list of dicts, one per face:
          face_index   (int)         — 0-based order
          embedding    (list[float]) — 512 floats, unit-normalized
          quality_score(float)       — detection confidence
          facial_area  (dict)        — {x, y, w, h} bounding box if available

    Raises:
        ValueError: no faces detected
    """
    from deepface import DeepFace

    if hasattr(image_file, 'seek'):
        image_file.seek(0)

    suffix = _get_suffix(image_file)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        if hasattr(image_file, 'chunks'):
            for chunk in image_file.chunks():
                tmp.write(chunk)
        else:
            tmp.write(image_file.read())
        tmp_path = tmp.name

    results = None
    try:
        for detector in DETECTORS:
            try:
                results = DeepFace.represent(
                    img_path=tmp_path,
                    model_name=MODEL_NAME,
                    detector_backend=detector,
                    enforce_detection=True,
                    align=True,
                )
                break
            except Exception:
                continue

        if not results:
            raise ValueError(
                'No faces detected. Use a clear photo with visible faces and good lighting.'
            )
    finally:
        os.unlink(tmp_path)

    faces = []
    for i, r in enumerate(results):
        raw = np.array(r['embedding'], dtype=np.float32)
        norm = np.linalg.norm(raw)
        if norm > 0:
            raw = raw / norm
        faces.append({
            'face_index': i,
            'embedding': raw.tolist(),
            'quality_score': round(float(r.get('face_confidence', 0.0)), 4),
            'facial_area': r.get('facial_area', {}),
        })
    return faces


def cosine_similarity(vec_a, vec_b):
    """Cosine similarity between two lists/arrays. Returns float in [-1, 1]."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _get_suffix(image_file):
    name = getattr(image_file, 'name', '') or ''
    ext = os.path.splitext(name)[-1].lower()
    return ext if ext in ('.jpg', '.jpeg', '.png', '.bmp', '.webp') else '.jpg'
