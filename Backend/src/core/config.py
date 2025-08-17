# -*- coding: utf-8 -*-
"""
Configurări simple pentru aplicația MediView Backend
"""
import os
from pathlib import Path

# Configurări aplicație
APP_NAME = "MediView Backend"
VERSION = "1.0.0"
DESCRIPTION = "Backend pentru platforma de analiza MRI"

# Configurări server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "true").lower() == "true"

# Configurări CORS
CORS_ORIGINS = [
    "http://localhost:5173",    # Vite
    "http://localhost:3000",    # React
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

# Configurări upload
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(500 * 1024 * 1024)))  # 500MB
ALLOWED_EXTENSIONS = {'.nii', '.nii.gz', '.zip'}

# Creează directorul dacă nu există
UPLOAD_DIR.mkdir(exist_ok=True)

def get_file_size_mb(size_bytes: int) -> str:
    """Convertește bytes în MB"""
    return f"{size_bytes / (1024 * 1024):.2f} MB"