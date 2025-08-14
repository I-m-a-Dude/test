import logging
import sys
from typing import Optional
from pathlib import Path
import json
from datetime import datetime

from .config import settings


class JSONFormatter(logging.Formatter):
    """Formatter pentru logging în format JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Adaugă informații extra dacă există
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'file_path'):
            log_data['file_path'] = record.file_path

        if hasattr(record, 'processing_time'):
            log_data['processing_time'] = record.processing_time

        # Adaugă stack trace pentru erori
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class StandardFormatter(logging.Formatter):
    """Formatter standard pentru logging în format text."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(
        level: str = None,
        log_file: Optional[str] = None,
        json_format: bool = False
) -> logging.Logger:
    """
    Configurează logging-ul pentru aplicație.

    Args:
        level: Nivelul de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Calea către fișierul de log (opțional)
        json_format: Dacă să folosească format JSON pentru loguri

    Returns:
        Logger-ul principal al aplicației
    """
    # Folosește setările din config dacă nu sunt specificate
    level = level or settings.log_level
    log_file = log_file or settings.log_file

    # Configurează nivelul de logging
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Nivel de logging invalid: {level}')

    # Creează logger-ul principal
    logger = logging.getLogger("pediatric_segmentation")
    logger.setLevel(numeric_level)

    # Elimină handler-ele existente pentru a evita duplicarea
    logger.handlers.clear()

    # Formatter pentru console
    console_formatter = JSONFormatter() if json_format else StandardFormatter()

    # Handler pentru console (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Handler pentru fișier (dacă este specificat)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_formatter = JSONFormatter() if json_format else StandardFormatter()
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Configurează logger-ul pentru uvicorn dacă în debug
    if settings.debug:
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.setLevel(logging.DEBUG)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Obține un logger pentru un modul specific.

    Args:
        name: Numele modulului (opțional)

    Returns:
        Logger pentru modulul specificat
    """
    if name:
        return logging.getLogger(f"pediatric_segmentation.{name}")
    return logging.getLogger("pediatric_segmentation")


# Logger-ul principal al aplicației
logger = setup_logging()


def log_processing_step(step: str, file_path: str = None, **kwargs):
    """
    Logger specializat pentru pașii de procesare.

    Args:
        step: Numele pasului (preprocessing, inference, postprocessing)
        file_path: Calea către fișierul procesat
        **kwargs: Informații suplimentare pentru log
    """
    extra = {"processing_step": step}
    if file_path:
        extra["file_path"] = file_path
    extra.update(kwargs)

    logger.info(f"Procesare {step}", extra=extra)


def log_inference_metrics(accuracy: float = None, processing_time: float = None, **metrics):
    """
    Logger pentru metrici de inferență.

    Args:
        accuracy: Acuratețea modelului
        processing_time: Timpul de procesare în secunde
        **metrics: Alte metrici
    """
    extra = {"metrics": {}}
    if accuracy is not None:
        extra["metrics"]["accuracy"] = accuracy
    if processing_time is not None:
        extra["metrics"]["processing_time"] = processing_time
    extra["metrics"].update(metrics)

    logger.info("Metrici inferență", extra=extra)