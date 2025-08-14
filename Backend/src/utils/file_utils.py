"""
Utilități generale pentru manipularea fișierelor în aplicația de segmentare.
"""

import os
import shutil
import tempfile
import hashlib
import uuid
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, timedelta
import mimetypes

from src.core import settings, logger, log_processing_step


class FileManager:
    """Manager pentru operații cu fișiere."""

    def __init__(self):
        self.logger = logger
        self.upload_dir = Path(settings.upload_dir)
        self.output_dir = Path(settings.output_dir)
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = settings.allowed_extensions

        # Creează directoarele
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_upload(self,
                             filename: str,
                             file_size: int,
                             content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Validează un fișier pentru upload.

        Args:
            filename: Numele fișierului
            file_size: Dimensiunea în bytes
            content_type: MIME type (opțional)

        Returns:
            Dict cu rezultatul validării
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {
                "name": filename,
                "size": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "content_type": content_type
            }
        }

        try:
            # Validare extensie
            file_path = Path(filename)
            extension = self._get_full_extension(file_path)

            if extension not in self.allowed_extensions:
                result["errors"].append(
                    f"Extensie nepermisă: {extension}. "
                    f"Extensii permise: {', '.join(self.allowed_extensions)}"
                )

            # Validare dimensiune
            if file_size > self.max_file_size:
                max_mb = self.max_file_size // (1024 * 1024)
                result["errors"].append(
                    f"Fișier prea mare: {result['file_info']['size_mb']}MB. "
                    f"Maxim permis: {max_mb}MB"
                )

            if file_size == 0:
                result["errors"].append("Fișierul este gol")

            # Validare nume fișier
            if not self._is_safe_filename(filename):
                result["errors"].append("Numele fișierului conține caractere nepermise")

            # Avertismente
            if file_size > 100 * 1024 * 1024:  # > 100MB
                result["warnings"].append("Fișier mare - procesarea poate dura mai mult")

            # Validare MIME type (dacă e disponibil)
            if content_type and not self._is_valid_mime_type(content_type):
                result["warnings"].append(f"MIME type neașteptat: {content_type}")

            result["valid"] = len(result["errors"]) == 0
            result["file_info"]["extension"] = extension

            if result["valid"]:
                self.logger.info(f"✅ Validare fișier OK: {filename}")
            else:
                self.logger.warning(f"⚠️ Validare fișier eșuată: {filename} - {result['errors']}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Eroare la validarea fișierului {filename}: {e}")
            result["errors"].append(f"Eroare de validare: {e}")
            return result

    def generate_unique_filename(self, original_filename: str, prefix: str = "") -> str:
        """
        Generează un nume unic de fișier păstrând extensia originală.

        Args:
            original_filename: Numele original
            prefix: Prefix opțional

        Returns:
            Nume unic de fișier
        """
        file_path = Path(original_filename)
        extension = self._get_full_extension(file_path)
        stem = file_path.stem.replace('.nii', '')  # Pentru .nii.gz

        # Generează UUID scurt
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Construiește numele
        parts = [part for part in [prefix, stem, timestamp, unique_id] if part]
        unique_name = "_".join(parts) + extension

        return self._sanitize_filename(unique_name)

    def save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """
        Salvează un fișier uploadat în directorul de upload.

        Args:
            file_content: Conținutul fișierului
            filename: Numele fișierului

        Returns:
            Calea către fișierul salvat
        """
        try:
            # Generează nume unic
            unique_filename = self.generate_unique_filename(filename, "upload")
            file_path = self.upload_dir / unique_filename

            # Salvează fișierul
            with open(file_path, 'wb') as f:
                f.write(file_content)

            log_processing_step("file_upload", str(file_path),
                                size=len(file_content), original_name=filename)

            self.logger.info(f"✅ Fișier salvat: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"❌ Eroare la salvarea fișierului {filename}: {e}")
            raise

    def create_output_path(self, input_filename: str, suffix: str = "segmented") -> Path:
        """
        Creează calea pentru fișierul de output.

        Args:
            input_filename: Numele fișierului de input
            suffix: Suffix pentru output

        Returns:
            Calea pentru fișierul de output
        """
        input_path = Path(input_filename)
        stem = input_path.stem.replace('.nii', '')  # Pentru .nii.gz
        extension = self._get_full_extension(input_path)

        output_filename = f"{stem}_{suffix}{extension}"
        return self.output_dir / output_filename

    def cleanup_old_files(self, max_age_hours: int = 24) -> Dict[str, int]:
        """
        Șterge fișierele vechi din directoarele de upload și output.

        Args:
            max_age_hours: Vârsta maximă în ore

        Returns:
            Dict cu numărul de fișiere șterse
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted = {"upload": 0, "output": 0}

        try:
            # Cleanup upload directory
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted["upload"] += 1

            # Cleanup output directory
            for file_path in self.output_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted["output"] += 1

            self.logger.info(f"🧹 Cleanup: {deleted['upload']} upload, {deleted['output']} output files deleted")
            return deleted

        except Exception as e:
            self.logger.error(f"❌ Eroare la cleanup: {e}")
            return deleted

    def get_file_hash(self, file_path: Union[str, Path]) -> str:
        """
        Calculează hash-ul MD5 al unui fișier.

        Args:
            file_path: Calea către fișier

        Returns:
            Hash MD5 ca string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_directory_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Returnează statistici despre directoarele de fișiere.

        Returns:
            Dict cu statistici
        """
        stats = {}

        for name, directory in [("upload", self.upload_dir), ("output", self.output_dir)]:
            try:
                files = list(directory.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())

                stats[name] = {
                    "directory": str(directory),
                    "file_count": len([f for f in files if f.is_file()]),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "exists": directory.exists()
                }
            except Exception as e:
                stats[name] = {"error": str(e)}

        return stats

    def _get_full_extension(self, file_path: Path) -> str:
        """Returnează extensia completă (inclusiv .nii.gz)."""
        if file_path.suffix == '.gz' and file_path.stem.endswith('.nii'):
            return '.nii.gz'
        return file_path.suffix.lower()

    def _is_safe_filename(self, filename: str) -> bool:
        """Verifică dacă numele fișierului este sigur."""
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        return not any(char in filename for char in dangerous_chars)

    def _sanitize_filename(self, filename: str) -> str:
        """Curăță numele fișierului de caractere periculoase."""
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        return filename

    def _is_valid_mime_type(self, content_type: str) -> bool:
        """Verifică dacă MIME type-ul este valid pentru NIfTI."""
        valid_types = [
            'application/octet-stream',
            'application/x-gzip',
            'application/gzip',
            'application/x-nifti',
            'application/nifti'
        ]
        return content_type in valid_types


# Instanță globală
file_manager = FileManager()


# Funcții de conveniență
def validate_upload(filename: str, file_size: int, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Funcție de conveniență pentru validarea upload-ului."""
    return file_manager.validate_file_upload(filename, file_size, content_type)


def save_uploaded_file(file_content: bytes, filename: str) -> Path:
    """Funcție de conveniență pentru salvarea fișierului."""
    return file_manager.save_uploaded_file(file_content, filename)


def cleanup_old_files(max_age_hours: int = 24) -> Dict[str, int]:
    """Funcție de conveniență pentru cleanup."""
    return file_manager.cleanup_old_files(max_age_hours)


def get_directory_stats() -> Dict[str, Dict[str, Any]]:
    """Funcție de conveniență pentru statistici."""
    return file_manager.get_directory_stats()