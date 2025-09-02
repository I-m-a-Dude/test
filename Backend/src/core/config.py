# -*- coding: utf-8 -*-
"""
Configurări simple pentru aplicația MediView Backend
"""
import os
from pathlib import Path

# Configurări aplicație
APP_NAME = "MediView Backend"
VERSION = "1.0.0"
DESCRIPTION = "Backend pentru platforma de analiză MRI"

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
ALLOWED_EXTENSIONS = {'.nii', '.nii.gz', '.zip'}  # Adăugăm .zip

# Configurări ML
MODELS_DIR = Path(os.getenv("MODELS_DIR", "model"))
MODEL_PATH = MODELS_DIR / "ag_model.pth"
TEMP_PROCESSING_DIR = Path("temp/processing")
TEMP_PREPROCESSING_DIR = Path("temp/preprocess")
TEMP_RESULTS_DIR = Path("temp/results")

# Parametrii model MedNeXt
NUM_CHANNELS = 4        # 4 modalități (T1, T1c, T2, FLAIR)
NUM_CLASSES = 5         # 5 clase (background + 4 tipuri de segmentare)
INIT_FILTERS = 32
SPATIAL_DIMS = 3        # 3D segmentation
KERNEL_SIZE = 5
DEEP_SUPERVISION = False

# Parametrii preprocesare
IMG_SIZE = (128, 128, 128)  # Dimensiunea finală pentru model
SPACING = (1.0, 1.0, 1.0)   # Voxel spacing standard
ORIENTATION = "RAI"          # Right, Anterior, Inferior

# Parametrii normalizare intensitate (pentru fiecare modalitate)
INTENSITY_RANGES = {
    "t1n": {"a_min": 0, "a_max": 3000, "b_min": 0.0, "b_max": 1.0},
    "t1c": {"a_min": 0, "a_max": 3000, "b_min": 0.0, "b_max": 1.0},
    "t2w": {"a_min": 0, "a_max": 3500, "b_min": 0.0, "b_max": 1.0},
    "t2f": {"a_min": 0, "a_max": 3500, "b_min": 0.0, "b_max": 1.0}
}

# Creează directoarele dacă nu există
UPLOAD_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
TEMP_PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
TEMP_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def get_file_size_mb(size_bytes: int) -> str:
    """Convertește bytes în MB"""
    return f"{size_bytes / (1024 * 1024):.2f} MB"