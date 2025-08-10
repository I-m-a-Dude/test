import logging
import sys
from pathlib import Path
from datetime import datetime
from .config import settings


def setup_logger(name: str = "pediatric_segmentation") -> logging.Logger:
    """
    Configurează logger pentru aplicația de segmentare medicală

    Args:
        name: Numele logger-ului

    Returns:
        Logger configurat
    """

    # Creează logger
    logger = logging.getLogger(name)

    # Evită duplicate handlers
    if logger.handlers:
        return logger

    # Setează nivelul de logging
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    # Format pentru mesaje
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (pentru development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (pentru producție)
    log_dir = settings.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log_inference(logger: logging.Logger, filename: str, duration: float, success: bool):
    """
    Log dedicat pentru procesul de inferență

    Args:
        logger: Logger instance
        filename: Numele fișierului procesat
        duration: Durata în secunde
        success: Dacă procesul a fost cu succes
    """
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"INFERENCE | {filename} | {status} | {duration:.2f}s")


def log_upload(logger: logging.Logger, filename: str, file_size: int):
    """
    Log pentru upload-uri

    Args:
        logger: Logger instance
        filename: Numele fișierului
        file_size: Dimensiunea în bytes
    """
    size_mb = file_size / (1024 * 1024)
    logger.info(f"UPLOAD | {filename} | {size_mb:.2f}MB")


# Logger principal
main_logger = setup_logger()