"""
Utilități generale pentru manipularea fișierelor.
Include validare, cleanup, gestionare fișiere temporare și operațiuni I/O.
"""

import os
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import Union, List, Optional, Dict, Any, Generator
import logging
import time
from contextlib import contextmanager
import mimetypes
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manager pentru operațiuni cu fișiere în contextul aplicației.
    Gestionează uploads, cleanup, validări și fișiere temporare.
    """

    # Extensii permise pentru upload
    ALLOWED_EXTENSIONS = {'.nii', '.nii.gz'}

    # Dimensiuni maxime (în bytes)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB pentru fișiere NIfTI mari

    # Timp de viață pentru fișiere temporare (în secunde)
    TEMP_FILE_LIFETIME = 3600  # 1 oră

    def __init__(self, base_upload_dir: Union[str, Path], base_output_dir: Union[str, Path]):
        """
        Inițializează managerul cu directoarele de lucru.

        Args:
            base_upload_dir: Director pentru fișiere uploadate
            base_output_dir: Director pentru rezultate procesate
        """
        self.upload_dir = Path(base_upload_dir)
        self.output_dir = Path(base_output_dir)
        self.temp_dir = Path(tempfile.gettempdir()) / "nifti_segmentation"

        # Creează directoarele dacă nu există
        self._setup_directories()

        logger.info(f"FileManager inițializat:")
        logger.info(f"  - Upload dir: {self.upload_dir}")
        logger.info(f"  - Output dir: {self.output_dir}")
        logger.info(f"  - Temp dir: {self.temp_dir}")

    def _setup_directories(self) -> None:
        """Creează directoarele necesare."""
        for directory in [self.upload_dir, self.output_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Director creat/verificat: {directory}")

    def validate_upload_file(self, file_path: Union[str, Path], check_content: bool = True) -> Dict[str, Any]:
        """
        Validează un fișier uploadat.

        Args:
            file_path: Calea către fișier
            check_content: Dacă să valideze și conținutul fișierului

        Returns:
            Dict cu rezultatul validării și informații despre fișier
        """
        file_path = Path(file_path)

        result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {}
        }

        try:
            # Verifică existența
            if not file_path.exists():
                result["errors"].append("Fișierul nu există")
                return result

            # Informații de bază
            file_size = file_path.stat().st_size
            file_extension = ''.join(file_path.suffixes)  # Pentru .nii.gz

            result["file_info"] = {
                "name": file_path.name,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "extension": file_extension,
                "created": datetime.fromtimestamp(file_path.stat().st_ctime),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime)
            }

            # Verifică extensia
            if file_extension not in self.ALLOWED_EXTENSIONS:
                result["errors"].append(f"Extensie nesuportată: {file_extension}. Permise: {self.ALLOWED_EXTENSIONS}")

            # Verifică dimensiunea
            if file_size > self.MAX_FILE_SIZE:
                result["errors"].append(
                    f"Fișier prea mare: {result['file_info']['size_mb']}MB. Maxim: {self.MAX_FILE_SIZE / (1024 * 1024)}MB")

            if file_size == 0:
                result["errors"].append("Fișier gol")

            # Verificare conținut (opțională)
            if check_content and not result["errors"]:
                from .nifti_io import NIfTIProcessor
                if not NIfTIProcessor.validate_nifti_file(file_path):
                    result["errors"].append("Conținut NIfTI invalid")

            # Avertismente pentru fișiere foarte mari
            if file_size > 100 * 1024 * 1024:  # 100MB
                result["warnings"].append("Fișier foarte mare - procesarea poate dura")

            result["is_valid"] = len(result["errors"]) == 0

            logger.info(f"Validare fișier {file_path.name}: {'✓' if result['is_valid'] else '✗'}")
            if result["errors"]:
                logger.warning(f"Erori validare: {result['errors']}")

        except Exception as e:
            result["errors"].append(f"Eroare la validare: {str(e)}")
            logger.error(f"Excepție la validarea {file_path}: {e}")

        return result

    def generate_unique_filename(self, original_name: str, suffix: str = "") -> str:
        """
        Generează un nume unic de fișier bazat pe timestamp și hash.

        Args:
            original_name: Numele original
            suffix: Sufix opțional (ex: "_processed")

        Returns:
            str: Nume unic de fișier
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Hash din numele original pentru unicitate
        hash_object = hashlib.md5(original_name.encode())
        file_hash = hash_object.hexdigest()[:8]

        # Extrage extensia
        path = Path(original_name)
        extension = ''.join(path.suffixes)
        base_name = path.name.replace(extension, '')

        unique_name = f"{base_name}_{timestamp}_{file_hash}{suffix}{extension}"

        logger.debug(f"Nume unic generat: {original_name} → {unique_name}")
        return unique_name

    @contextmanager
    def temporary_file(self, suffix: str = ".nii.gz", prefix: str = "temp_") -> Generator[Path, None, None]:
        """
        Context manager pentru fișiere temporare cu cleanup automat.

        Args:
            suffix: Extensia fișierului temporar
            prefix: Prefixul numelui

        Yields:
            Path: Calea către fișierul temporar
        """
        temp_file = None
        try:
            # Creează fișier temporar în directorul nostru
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
            os.close(fd)  # Închidem file descriptor-ul

            temp_file = Path(temp_path)
            logger.debug(f"Fișier temporar creat: {temp_file}")

            yield temp_file

        finally:
            # Cleanup automat
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Fișier temporar șters: {temp_file}")
                except Exception as e:
                    logger.warning(f"Nu s-a putut șterge fișierul temporar {temp_file}: {e}")

    def cleanup_old_files(self, directory: Union[str, Path], max_age_hours: int = 24) -> int:
        """
        Șterge fișierele vechi dintr-un director.

        Args:
            directory: Directorul de curățat
            max_age_hours: Vârsta maximă a fișierelor (în ore)

        Returns:
            int: Numărul de fișiere șterse
        """
        directory = Path(directory)
        if not directory.exists():
            return 0

        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0

        try:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_age = file_path.stat().st_mtime
                    if file_age < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Șters fișier vechi: {file_path}")
                        except Exception as e:
                            logger.warning(f"Nu s-a putut șterge {file_path}: {e}")

            logger.info(f"Cleanup complet: {deleted_count} fișiere șterse din {directory}")

        except Exception as e:
            logger.error(f"Eroare la cleanup în {directory}: {e}")

        return deleted_count

    def safe_copy_file(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """
        Copiază un fișier cu verificări de siguranță.

        Args:
            source: Fișierul sursă
            destination: Destinația

        Returns:
            bool: True dacă copierea a reușit
        """
        source, destination = Path(source), Path(destination)

        try:
            # Verifică sursa
            if not source.exists():
                logger.error(f"Fișierul sursă nu există: {source}")
                return False

            # Creează directorul destinație
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copiază cu verificare
            shutil.copy2(source, destination)

            # Verifică copierea
            if destination.exists() and destination.stat().st_size == source.stat().st_size:
                logger.info(f"Fișier copiat cu succes: {source} → {destination}")
                return True
            else:
                logger.error(f"Copierea a eșuat sau fișierul e incomplet: {destination}")
                return False

        except Exception as e:
            logger.error(f"Eroare la copierea {source} → {destination}: {e}")
            return False

    def get_directory_size(self, directory: Union[str, Path]) -> Dict[str, Any]:
        """
        Calculează dimensiunea unui director.

        Args:
            directory: Directorul de analizat

        Returns:
            Dict cu informații despre dimensiune
        """
        directory = Path(directory)

        if not directory.exists():
            return {"exists": False}

        total_size = 0
        file_count = 0

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1

            return {
                "exists": True,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "directory": str(directory)
            }

        except Exception as e:
            logger.error(f"Eroare la calcularea dimensiunii {directory}: {e}")
            return {"exists": True, "error": str(e)}

    def schedule_cleanup(self) -> None:
        """
        Rulează cleanup pe toate directoarele gestionate.
        Metoda poate fi apelată periodic de un scheduler.
        """
        logger.info("Începe cleanup programat...")

        # Cleanup fișiere uploadate vechi (24h)
        upload_cleaned = self.cleanup_old_files(self.upload_dir, 24)

        # Cleanup rezultate vechi (48h)
        output_cleaned = self.cleanup_old_files(self.output_dir, 48)

        # Cleanup fișiere temporare (1h)
        temp_cleaned = self.cleanup_old_files(self.temp_dir, 1)

        total_cleaned = upload_cleaned + output_cleaned + temp_cleaned

        logger.info(f"Cleanup complet: {total_cleaned} fișiere șterse")
        logger.info(f"  - Upload: {upload_cleaned}, Output: {output_cleaned}, Temp: {temp_cleaned}")


# Funcții de conveniență
def ensure_directory(path: Union[str, Path]) -> Path:
    """Asigură că directorul există."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_remove_file(file_path: Union[str, Path]) -> bool:
    """Șterge un fișier în siguranță."""
    try:
        Path(file_path).unlink(missing_ok=True)
        return True
    except Exception as e:
        logger.warning(f"Nu s-a putut șterge {file_path}: {e}")
        return False


def get_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> Optional[str]:
    """Calculează hash-ul unui fișier."""
    try:
        hash_algo = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_algo.update(chunk)
        return hash_algo.hexdigest()
    except Exception as e:
        logger.error(f"Eroare calculare hash pentru {file_path}: {e}")
        return None