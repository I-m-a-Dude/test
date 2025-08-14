"""
Core module pentru aplicația de segmentare pediatrică.

Acest modul conține configurările și utilitățile fundamentale
pentru funcționarea aplicației.
"""

from .config import settings, Settings
from .logger import (
    logger,
    get_logger,
    setup_logging,
    log_processing_step,
    log_inference_metrics,
    JSONFormatter,
    StandardFormatter
)

__all__ = [
    # Configurații
    "settings",
    "Settings",

    # Logging
    "logger",
    "get_logger",
    "setup_logging",
    "log_processing_step",
    "log_inference_metrics",
    "JSONFormatter",
    "StandardFormatter",
]

# Versiunea modulului core
__version__ = "1.0.0"