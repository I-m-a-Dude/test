"""
Modulul core pentru aplicația de segmentare medicală pediatrică
"""

from .config import settings
from .logger import main_logger, setup_logger, log_inference, log_upload
from .exceptions import (
    PediatricSegmentationError,
    FileProcessingError,
    InvalidNIfTIError,
    ModelError,
    ModelNotFoundError,
    ModelLoadError,
    InferenceError,
    PreprocessingError,
    PostprocessingError,
    FileSizeError,
    UnsupportedFormatError
)

__all__ = [
    # Config
    'settings',

    # Logging
    'main_logger',
    'setup_logger',
    'log_inference',
    'log_upload',

    # Exceptions
    'PediatricSegmentationError',
    'FileProcessingError',
    'InvalidNIfTIError',
    'ModelError',
    'ModelNotFoundError',
    'ModelLoadError',
    'InferenceError',
    'PreprocessingError',
    'PostprocessingError',
    'FileSizeError',
    'UnsupportedFormatError'
]