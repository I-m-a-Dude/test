# -*- coding: utf-8 -*-
"""
Service package pentru MediView Backend
Conține serviciile de preprocesare, postprocesare și inferență (cu cache)
"""

from .preprocess import NIfTIPreprocessor, get_preprocessor, preprocess_folder_simple
from .postprocess import GliomaPostprocessor, create_postprocessor, quick_postprocess, get_postprocessor
from .inference import (
    GliomaInferenceService, create_inference_service, run_inference_on_folder,
    run_inference_on_preprocessed, get_inference_service,
    check_existing_result, get_existing_result_info
)

__all__ = [
    # Preprocess
    'NIfTIPreprocessor',
    'get_preprocessor',
    'preprocess_folder_simple',

    # Postprocess
    'GliomaPostprocessor',
    'create_postprocessor',
    'quick_postprocess',
    'get_postprocessor',

    # Inference (with cache)
    'GliomaInferenceService',
    'create_inference_service',
    'run_inference_on_folder',
    'run_inference_on_preprocessed',
    'get_inference_service',
    'check_existing_result',
    'get_existing_result_info'
]