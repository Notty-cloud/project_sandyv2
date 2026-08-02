"""
Face embedding backends.

Two implementations exist and both emit 512-dim L2-normalised vectors:

  deepface (production baseline)
      students/face.py — DeepFace + Facenet512. Weights download automatically
      and are baked into the image at build time.

  onnx (experimental)
      ai_engine/face_pipeline.py — SCRFD-10GF detection + ArcFace ResNet50 via
      ONNX Runtime. Needs det_10g.onnx and w600k_r50.onnx in ai_engine/models/
      (see that directory's .gitkeep) and `pip install -r requirements-onnx.txt`.
      Interesting because ONNX Runtime is ~75 MB against TensorFlow's ~2.4 GB
      and runs on ARM, which is what an on-site edge device would need.

**The two are not interchangeable at runtime.** Facenet512 and ArcFace embed
into different vector spaces, so a cosine similarity between one backend's
vector and the other's is meaningless — it will return plausible-looking
numbers that are pure noise. Every StudentEmbedding therefore records the
backend that produced it, and matching only ever compares within one backend.
Switching backends means re-enrolling every student.

Select with the FACE_BACKEND environment variable (default: deepface).
"""
from django.conf import settings

DEEPFACE = 'deepface'
ONNX = 'onnx'
VALID_BACKENDS = (DEEPFACE, ONNX)


def active_backend():
    """Name of the configured backend, validated."""
    name = getattr(settings, 'FACE_BACKEND', DEEPFACE)
    if name not in VALID_BACKENDS:
        raise ValueError(
            f'FACE_BACKEND={name!r} is not recognised. Expected one of {VALID_BACKENDS}.'
        )
    return name


def extract_embedding(image_file, backend=None):
    """
    Extract one 512-dim embedding using the selected backend.

    Returns a dict with the same shape from either backend:
        embedding     list[float] — 512 floats, L2-normalised
        quality_score float       — detection confidence, 0.0–1.0
        face_count    int
        backend       str         — which implementation produced it

    Raises ValueError when no usable face is found, whichever backend is
    active, so callers need not know which is in use.
    """
    backend = backend or active_backend()
    if backend == DEEPFACE:
        return _extract_deepface(image_file)
    return _extract_onnx(image_file)


def _extract_deepface(image_file):
    from .face import extract_embedding as deepface_extract

    result = deepface_extract(image_file)  # already raises ValueError
    result['backend'] = DEEPFACE
    result.setdefault('detector', '')
    return result


def _extract_onnx(image_file):
    try:
        from ai_engine.face_pipeline import extract_embedding as onnx_extract
        from ai_engine.exceptions import FaceNotDetectedError, LowQualityFaceError
    except ImportError as exc:
        raise RuntimeError(
            'The onnx backend needs onnxruntime: pip install -r requirements-onnx.txt'
        ) from exc

    if hasattr(image_file, 'seek'):
        image_file.seek(0)

    try:
        result = onnx_extract(image_file)
    except (FaceNotDetectedError, LowQualityFaceError) as exc:
        # Normalise to ValueError so view error handling is backend-agnostic.
        raise ValueError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f'ONNX model files are missing from ai_engine/models/ — see that '
            f'directory\'s .gitkeep for download instructions. ({exc})'
        ) from exc

    embedding = result['embedding']
    return {
        # face_pipeline returns a numpy array; the DB layer and pgvector both
        # want a plain list.
        'embedding': embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding),
        'quality_score': result['quality_score'],
        'face_count': result.get('face_count', 1),
        'backend': ONNX,
        'detector': 'scrfd',  # the ONNX pipeline always uses SCRFD-10GF
    }
