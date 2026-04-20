"""
ai_engine/exceptions.py

Custom exceptions for the face embedding pipeline.
"""


class FaceNotDetectedError(Exception):
    """Raised when no face is found in the input image."""


class MultipleFacesWarning(UserWarning):
    """
    Issued when more than one face is detected in the image.
    The pipeline continues using the largest bounding box.
    """


class LowQualityFaceError(Exception):
    """
    Raised when the detected face quality score falls below the minimum
    threshold (default: 0.6). Caller should prompt for a better image.
    """
