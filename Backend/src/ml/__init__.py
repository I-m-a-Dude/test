# -*- coding: utf-8 -*-
"""
ML package pentru MediView Backend
Conține model wrapper pentru MedNeXt și utilități pentru inferență
"""

from .model_wrapper import (
    MedNeXtWrapper,
    get_model_wrapper,
    ensure_model_loaded,
    unload_global_model,
    force_global_cleanup,
    get_global_memory_usage
)

__all__ = [
    'MedNeXtWrapper',
    'get_model_wrapper',
    'ensure_model_loaded',
    'unload_global_model',
    'force_global_cleanup',
    'get_global_memory_usage'
]