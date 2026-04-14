"""
Face recognition utility for Project Sandy.

Uses DeepFace with the Facenet512 model (512-dim embeddings).
Model weights (~90MB) are downloaded automatically on first use
and cached at ~/.deepface/weights/.

Swap extract_embedding() with a different model by changing MODEL_NAME.
The rest of the system (enrollment, identification, cosine similarity)
requires exactly 512 dimensions — update the DB schema if you change this.
"""
import tempfile
import os
import numpy as np

MODEL_NAME = 'Facenet512'      # 512-dim output, matches student_embeddings schema

# Detectors tried in order — retinaface is most accurate, opencv is fastest fallback
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

    last_error = None
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
                break  # success — stop trying other detectors
            except Exception as e:
                last_error = e
                continue
    finally:
        os.unlink(tmp_path)

    if results is None:
        raise ValueError(
            'No face detected in the image. '
            'Please ensure good lighting, face the camera directly, and avoid obstructions.'
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
    }


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
