
"""
Excepții custom pentru aplicația de segmentare medicală pediatrică
"""


class PediatricSegmentationError(Exception):
    """Excepție de bază pentru aplicația de segmentare"""
    pass


class FileProcessingError(PediatricSegmentationError):
    """Erori legate de procesarea fișierelor NIfTI"""

    def __init__(self, filename: str, message: str):
        self.filename = filename
        self.message = message
        super().__init__(f"Eroare procesare fișier '{filename}': {message}")


class InvalidNIfTIError(FileProcessingError):
    """Fișierul NIfTI nu este valid sau este corupt"""

    def __init__(self, filename: str, details: str = ""):
        message = f"Fișier NIfTI invalid{': ' + details if details else ''}"
        super().__init__(filename, message)


class ModelError(PediatricSegmentationError):
    """Erori legate de modelul de segmentare"""
    pass


class ModelNotFoundError(ModelError):
    """Modelul de segmentare nu poate fi găsit"""

    def __init__(self, model_path: str):
        super().__init__(f"Modelul nu a fost găsit la calea: {model_path}")


class ModelLoadError(ModelError):
    """Modelul nu poate fi încărcat"""

    def __init__(self, model_path: str, details: str = ""):
        message = f"Nu s-a putut încărca modelul de la {model_path}"
        if details:
            message += f": {details}"
        super().__init__(message)


class InferenceError(ModelError):
    """Eroare în timpul inferenței"""

    def __init__(self, message: str, filename: str = ""):
        full_message = f"Eroare inferență"
        if filename:
            full_message += f" pentru {filename}"
        full_message += f": {message}"
        super().__init__(full_message)


class PreprocessingError(FileProcessingError):
    """Erori în timpul preprocesării"""

    def __init__(self, filename: str, step: str, details: str):
        message = f"Eroare la {step}: {details}"
        super().__init__(filename, message)


class PostprocessingError(FileProcessingError):
    """Erori în timpul postprocesării"""

    def __init__(self, filename: str, step: str, details: str):
        message = f"Eroare la postprocesare ({step}): {details}"
        super().__init__(filename, message)


class FileSizeError(FileProcessingError):
    """Fișierul depășește dimensiunea maximă permisă"""

    def __init__(self, filename: str, size: int, max_size: int):
        size_mb = size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        message = f"Fișier prea mare ({size_mb:.1f}MB). Maxim permis: {max_mb:.1f}MB"
        super().__init__(filename, message)


class UnsupportedFormatError(FileProcessingError):
    """Format de fișier nesuportat"""

    def __init__(self, filename: str, extension: str, supported: set):
        supported_str = ", ".join(supported)
        message = f"Extensie '{extension}' nesuportată. Formate acceptate: {supported_str}"
        super().__init__(filename, message)