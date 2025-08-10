import os
from pathlib import Path
from typing import Optional


class Settings:
    """Configurări aplicație pentru segmentarea medicală pediatrică"""

    # Configurări server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Căi fișiere
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "segresnet_model.pth"))

    # Configurări model
    MODEL_DEVICE: str = os.getenv("MODEL_DEVICE", "cpu")  # sau "cuda" dacă ai GPU
    MODEL_INPUT_SIZE: tuple = (128, 128, 128)  # dimensiuni standard pentru preprocesare
    MODEL_CHANNELS: int = 1  # imagini medicale grayscale
    NUM_CLASSES: int = 2  # background + organ de interes

    # Limitări upload
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB max
    ALLOWED_EXTENSIONS: set = {".nii", ".nii.gz"}

    # Parametri preprocesare
    TARGET_SPACING: tuple = (1.0, 1.0, 1.0)  # mm
    INTENSITY_RANGE: tuple = (0, 1)  # normalizare

    # Timeouts
    INFERENCE_TIMEOUT: int = 300  # 5 minute max pentru inferență

    def __init__(self):
        """Creează directoarele necesare"""
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.OUTPUT_DIR.mkdir(exist_ok=True)

    @property
    def model_available(self) -> bool:
        """Verifică dacă modelul există"""
        return Path(self.MODEL_PATH).exists()


# Instanță globală
settings = Settings()