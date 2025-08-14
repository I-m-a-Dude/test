import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurări pentru aplicația de segmentare pediatrică."""

    # Configurări server
    app_name: str = "Pediatric Segmentation API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Configurări fișiere
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    allowed_extensions: list = [".nii", ".nii.gz"]

    # Configurări model ML
    model_path: str = "models/segmentation_model.pth"
    model_device: str = "cpu"  # sau "cuda" dacă există GPU
    model_input_size: tuple = (128, 128, 128)  # dimensiuni standard pentru preprocesare

    # Configurări procesare
    normalization_method: str = "z_score"  # z_score, min_max, percentile
    resampling_spacing: tuple = (1.0, 1.0, 1.0)  # spacing în mm
    use_postprocessing: bool = True
    smoothing_factor: float = 1.0

    # Configurări logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # CORS și securitate
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_credentials: bool = True
    cors_methods: list = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: list = ["*"]

    @field_validator('model_device')
    @classmethod
    def validate_device(cls, v):
        """Validează device-ul pentru model."""
        import torch
        if v == "cuda" and not torch.cuda.is_available():
            return "cpu"
        return v

    @field_validator('upload_dir', 'output_dir')
    @classmethod
    def create_directories(cls, v):
        """Creează directoarele dacă nu există."""
        os.makedirs(v, exist_ok=True)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instanță globală a configurărilor
settings = Settings()