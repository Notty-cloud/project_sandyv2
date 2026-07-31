#!/usr/bin/env python
"""
Pre-download DeepFace model weights at image build time.

DeepFace fetches weights on first use and caches them under ~/.deepface/weights.
In a container that directory is ephemeral, so without this step the first
enrolment after every deploy downloads ~95 MB over the network *inside a
request* — slow, dependent on an external host being reachable, repeated per
gunicorn worker, and liable to exceed the request timeout.

Baking the weights into an image layer makes that cost a build-time concern.

The recognition model is required: if it cannot be fetched the build should
fail loudly rather than ship an image that breaks on first use. Detector
weights are best-effort — 'opencv' ships with DeepFace and needs no download,
so the others are only fallbacks (see students/face.py::DETECTORS).
"""
import sys

from deepface import DeepFace

# Keep in step with students/face.py
MODEL_NAME = 'Facenet512'
OPTIONAL_DETECTORS = ['retinaface', 'mtcnn']


def main():
    print(f'Pre-fetching recognition model: {MODEL_NAME}')
    try:
        DeepFace.build_model(MODEL_NAME, task='facial_recognition')
        print(f'  ok: {MODEL_NAME}')
    except Exception as exc:
        print(f'  FAILED to fetch {MODEL_NAME}: {exc}', file=sys.stderr)
        return 1

    for detector in OPTIONAL_DETECTORS:
        try:
            DeepFace.build_model(detector, task='face_detector')
            print(f'  ok: {detector}')
        except Exception as exc:
            # Non-fatal: opencv is the primary detector and needs no weights.
            print(f'  skipped {detector}: {exc}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
