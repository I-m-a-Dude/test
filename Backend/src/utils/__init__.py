"""
Utils module pentru aplicația de segmentare pediatrică.

Acest modul conține utilități pentru manipularea fișierelor NIfTI
și operații generale cu fișiere.
"""

# NIfTI I/O operations
from .nifti_io import (
    NIfTIHandler,
    nifti_handler,
    load_nifti,
    save_nifti,
    validate_nifti,
    get_nifti_info
)

# File management utilities
from .file_utils import (
    FileManager,
    file_manager,
    validate_upload,
    save_uploaded_file,
    cleanup_old_files,
    get_directory_stats
)

__all__ = [
    # NIfTI operations
    "NIfTIHandler",
    "nifti_handler",
    "load_nifti",
    "save_nifti",
    "validate_nifti",
    "get_nifti_info",

    # File management
    "FileManager",
    "file_manager",
    "validate_upload",
    "save_uploaded_file",
    "cleanup_old_files",
    "get_directory_stats",
]

# Versiunea modulului utils
__version__ = "1.0.0"