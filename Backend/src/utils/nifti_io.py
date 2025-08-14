"""
Module pentru Input/Output operații pe fișiere NIfTI.
Folosește nibabel pentru manipularea imaginilor medicale 3D.
"""

import nibabel as nib
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union
import tempfile
import os

from src.core import logger, log_processing_step


class NIfTIHandler:
    """Handler pentru operații I/O pe fișiere NIfTI."""

    def __init__(self):
        self.logger = logger

    def load_nifti(self, file_path: Union[str, Path]) -> Tuple[np.ndarray, nib.Nifti1Image]:
        """
        Încarcă un fișier NIfTI și returnează datele și metadata.

        Args:
            file_path: Calea către fișierul NIfTI

        Returns:
            Tuple cu (array numpy 3D, obiect NIfTI cu metadata)

        Raises:
            FileNotFoundError: Dacă fișierul nu există
            ValueError: Dacă fișierul nu e valid NIfTI
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Fișierul {file_path} nu există")

        try:
            log_processing_step("load_nifti", str(file_path))

            # Încarcă fișierul NIfTI
            nifti_img = nib.load(str(file_path))

            # Extrage datele ca numpy array
            data = nifti_img.get_fdata()

            # Validări de bază
            if data.ndim < 3:
                raise ValueError(f"Imaginea trebuie să aibă cel puțin 3 dimensiuni, are {data.ndim}")

            # Convertește la float32 pentru eficiență
            if data.dtype != np.float32:
                data = data.astype(np.float32)

            self.logger.info(f"✅ NIfTI încărcat: {data.shape}, dtype: {data.dtype}")
            log_processing_step("load_nifti_success", str(file_path),
                                shape=data.shape, dtype=str(data.dtype))

            return data, nifti_img

        except Exception as e:
            self.logger.error(f"❌ Eroare la încărcarea NIfTI {file_path}: {e}")
            raise ValueError(f"Fișier NIfTI invalid: {e}")

    def save_nifti(self,
                   data: np.ndarray,
                   output_path: Union[str, Path],
                   reference_img: Optional[nib.Nifti1Image] = None,
                   affine: Optional[np.ndarray] = None) -> Path:
        """
        Salvează un array numpy ca fișier NIfTI.

        Args:
            data: Array numpy 3D cu datele de salvat
            output_path: Calea pentru fișierul de ieșire
            reference_img: Imagine NIfTI de referință pentru metadata
            affine: Matrice de transformare (dacă nu e dată reference_img)

        Returns:
            Calea către fișierul salvat

        Raises:
            ValueError: Dacă datele nu sunt valide
        """
        output_path = Path(output_path)

        try:
            log_processing_step("save_nifti", str(output_path))

            # Validări
            if data.ndim < 3:
                raise ValueError(f"Datele trebuie să aibă cel puțin 3 dimensiuni, au {data.ndim}")

            # Creează directorul dacă nu există
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Determină affine matrix
            if reference_img is not None:
                affine = reference_img.affine
                header = reference_img.header.copy()
            elif affine is not None:
                header = None
            else:
                # Affine implicit (identitate)
                affine = np.eye(4)
                header = None

            # Convertește datele la tipul potrivit
            if data.dtype not in [np.uint8, np.uint16, np.int16, np.int32, np.float32, np.float64]:
                data = data.astype(np.float32)

            # Creează imaginea NIfTI
            nifti_img = nib.Nifti1Image(data, affine, header)

            # Salvează fișierul
            nib.save(nifti_img, str(output_path))

            self.logger.info(f"✅ NIfTI salvat: {output_path}")
            log_processing_step("save_nifti_success", str(output_path),
                                shape=data.shape, dtype=str(data.dtype))

            return output_path

        except Exception as e:
            self.logger.error(f"❌ Eroare la salvarea NIfTI {output_path}: {e}")
            raise ValueError(f"Nu s-a putut salva fișierul NIfTI: {e}")

    def get_nifti_info(self, file_path: Union[str, Path]) -> dict:
        """
        Extrage informații despre un fișier NIfTI fără a încărca toate datele.

        Args:
            file_path: Calea către fișierul NIfTI

        Returns:
            Dict cu informații despre fișier
        """
        try:
            nifti_img = nib.load(str(file_path))
            header = nifti_img.header

            info = {
                "file_path": str(file_path),
                "shape": tuple(header.get_data_shape()),
                "dtype": str(header.get_data_dtype()),
                "voxel_sizes": tuple(header.get_zooms()),
                "orientation": nib.orientations.aff2axcodes(nifti_img.affine),
                "file_size_mb": Path(file_path).stat().st_size / (1024 * 1024),
                "header_description": header.get_descrip().decode('utf-8', errors='ignore'),
            }

            return info

        except Exception as e:
            self.logger.error(f"❌ Nu s-au putut extrage info din {file_path}: {e}")
            return {"error": str(e)}

    def validate_nifti_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validează dacă un fișier este un NIfTI valid.

        Args:
            file_path: Calea către fișierul de validat

        Returns:
            True dacă fișierul e valid NIfTI
        """
        try:
            file_path = Path(file_path)

            # Verifică extensia
            if not file_path.suffix.lower() in ['.nii', '.gz']:
                if not (file_path.suffix.lower() == '.gz' and
                        file_path.stem.endswith('.nii')):
                    return False

            # Încearcă să încărce header-ul
            nifti_img = nib.load(str(file_path))

            # Validări de bază
            shape = nifti_img.header.get_data_shape()
            if len(shape) < 3:
                return False

            # Verifică că dimensiunile sunt rezonabile
            if any(dim <= 0 for dim in shape[:3]):
                return False

            return True

        except Exception:
            return False


# Instanță globală pentru utilizare facilă
nifti_handler = NIfTIHandler()


# Funcții de conveniență
def load_nifti(file_path: Union[str, Path]) -> Tuple[np.ndarray, nib.Nifti1Image]:
    """Funcție de conveniență pentru încărcarea NIfTI."""
    return nifti_handler.load_nifti(file_path)


def save_nifti(data: np.ndarray,
               output_path: Union[str, Path],
               reference_img: Optional[nib.Nifti1Image] = None) -> Path:
    """Funcție de conveniență pentru salvarea NIfTI."""
    return nifti_handler.save_nifti(data, output_path, reference_img)


def validate_nifti(file_path: Union[str, Path]) -> bool:
    """Funcție de conveniență pentru validarea NIfTI."""
    return nifti_handler.validate_nifti_file(file_path)


def get_nifti_info(file_path: Union[str, Path]) -> dict:
    """Funcție de conveniență pentru informații NIfTI."""
    return nifti_handler.get_nifti_info(file_path)