# -*- coding: utf-8 -*-
"""
API Endpoints principal - importă și combină toate routerele
"""
from fastapi import APIRouter

from src.core.config import APP_NAME, VERSION, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS

# Importă toate routerele modulare
from .files import router as files_router
from .ml import router as ml_router
from .preprocess import router as preprocess_router
from .inference import router as inference_router

# Router principal
router = APIRouter()

# Endpoint-uri de bază (root și health)
@router.get("/")
async def root():
    """Endpoint de bază"""
    return {
        "message": f"{APP_NAME} API",
        "version": VERSION,
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "upload_dir": str(UPLOAD_DIR.absolute()),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "max_file_size": get_file_size_mb(MAX_FILE_SIZE),
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }


# Includ toate routerele modulare
router.include_router(files_router)
router.include_router(ml_router)
router.include_router(preprocess_router)
router.include_router(inference_router)

# Export pentru compatibilitate cu main.py
__all__ = ["router"]