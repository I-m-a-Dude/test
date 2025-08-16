"""
Utilități pentru citirea și scrierea fișierelor NIfTI folosind nibabel.
Bazat pe logica din notebook pentru manipularea imaginilor medicale.
"""

import nibabel as nib
import numpy as np
import torch
from pathlib import Path
from typing import Union, Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class NIfTIProcessor:
    """
    Procesor pentru fișiere NIfTI cu metode pentru citire, scriere și validare.
    Thread-safe pentru utilizare în FastAPI.
    """

    SUPPORTED_EXTENSIONS = ['.nii', '.nii.gz']

    @staticmethod
    def validate_nifti_file(file_path: Union[str, Path]) -> bool:
        """
        Validează dacă fișierul este un NIfTI valid.

        Args:
            file_path: Calea către fișier

        Returns:
            bool: True dacă fișierul este valid
        """
        file_path = Path(file_path)

        # Verifică extensia
        if not any(str(file_path).endswith(ext) for ext in NIfTIProcessor.SUPPORTED_EXTENSIONS):
            logger.warning(f"Extensie nesuportată: {file_path.suffix}")
            return False

        # Verifică existența
        if not file_path.exists():
            logger.warning(f"Fișierul nu există: {file_path}")
            return False

        # Încearcă să încarce cu nibabel
        try:
            img = nib.load(str(file_path))
            data = img.get_fdata()

            # Verificări de bază
            if data.size == 0:
                logger.warning(f"Fișier gol: {file_path}")
                return False

            logger.info(f"Fișier NIfTI valid: {file_path} - Shape: {data.shape}")
            return True

        except Exception as e:
            logger.error(f"Eroare la validarea NIfTI {file_path}: {e}")
            return False

    @staticmethod
    def load_nifti(file_path: Union[str, Path]) -> Tuple[np.ndarray, nib.Nifti1Image]:
        """
        Încarcă un fișier NIfTI și returnează datele + header-ul.

        Args:
            file_path: Calea către fișierul NIfTI

        Returns:
            Tuple[np.ndarray, nib.Nifti1Image]: (data_array, nifti_image)
        """
        file_path = Path(file_path)

        if not NIfTIProcessor.validate_nifti_file(file_path):
            raise ValueError(f"Fișier NIfTI invalid: {file_path}")

        try:
            logger.info(f"Încărcare NIfTI: {file_path}")

            # Încarcă cu nibabel
            nifti_img = nib.load(str(file_path))

            # Extrage datele
            data = nifti_img.get_fdata(dtype=np.float32)

            logger.info(f"NIfTI încărcat cu succes:")
            logger.info(f"  - Shape: {data.shape}")
            logger.info(f"  - Data type: {data.dtype}")
            logger.info(f"  - Value range: [{data.min():.2f}, {data.max():.2f}]")
            logger.info(f"  - Affine shape: {nifti_img.affine.shape}")
            logger.info(f"  - Voxel sizes: {nifti_img.header.get_zooms()}")

            return data, nifti_img

        except Exception as e:
            logger.error(f"Eroare la încărcarea NIfTI {file_path}: {e}")
            raise

    @staticmethod
    def save_nifti(data: np.ndarray,
                   output_path: Union[str, Path],
                   reference_nifti: Optional[nib.Nifti1Image] = None,
                   affine: Optional[np.ndarray] = None) -> None:
        """
        Salvează un array numpy ca fișier NIfTI.

        Args:
            data: Array-ul numpy de salvat
            output_path: Calea de output
            reference_nifti: NIfTI de referință pentru header și affine
            affine: Matrice affine custom (dacă nu e dat reference_nifti)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Salvare NIfTI la: {output_path}")
            logger.info(f"  - Data shape: {data.shape}")
            logger.info(f"  - Data type: {data.dtype}")
            logger.info(f"  - Value range: [{data.min():.2f}, {data.max():.2f}]")

            # Determine affine matrix
            if reference_nifti is not None:
                affine_matrix = reference_nifti.affine
                header = reference_nifti.header.copy()
                logger.info("Folosesc affine și header din referință")
            elif affine is not None:
                affine_matrix = affine
                header = None
                logger.info("Folosesc affine custom")
            else:
                # Default identity affine
                affine_matrix = np.eye(4)
                header = None
                logger.warning("Folosesc affine identity (fără referință)")

            # Convertește la tipul corect pentru salvare
            if data.dtype == np.float64:
                data = data.astype(np.float32)
            elif data.dtype not in [np.uint8, np.uint16, np.int16, np.int32, np.float32]:
                logger.info(f"Convertesc din {data.dtype} la float32")
                data = data.astype(np.float32)

            # Creează imaginea NIfTI
            nifti_img = nib.Nifti1Image(data, affine_matrix, header=header)

            # Salvează
            nib.save(nifti_img, str(output_path))

            logger.info(f"NIfTI salvat cu succes la: {output_path}")

        except Exception as e:
            logger.error(f"Eroare la salvarea NIfTI {output_path}: {e}")
            raise

    @staticmethod
    def numpy_to_tensor(data: np.ndarray,
                       add_batch_dim: bool = True,
                       add_channel_dim: bool = False,
                       dtype: torch.dtype = torch.float32) -> torch.Tensor:
        """
        Convertește numpy array la PyTorch tensor cu dimensiunile corecte.

        Args:
            data: Array numpy de convertit
            add_batch_dim: Adaugă dimensiunea batch (prima)
            add_channel_dim: Adaugă dimensiunea channel
            dtype: Tipul tensorului

        Returns:
            torch.Tensor: Tensorul convertit
        """
        try:
            # Convertește la tensor
            tensor = torch.from_numpy(data.copy()).to(dtype)

            # Adaugă dimensiuni după necesitate
            if add_channel_dim:
                tensor = tensor.unsqueeze(0)  # Adaugă channel dim
            if add_batch_dim:
                tensor = tensor.unsqueeze(0)  # Adaugă batch dim

            logger.debug(f"Numpy to tensor: {data.shape} → {tensor.shape}")
            return tensor

        except Exception as e:
            logger.error(f"Eroare conversie numpy→tensor: {e}")
            raise

    @staticmethod
    def tensor_to_numpy(tensor: torch.Tensor,
                       remove_batch_dim: bool = True,
                       remove_channel_dim: bool = False) -> np.ndarray:
        """
        Convertește PyTorch tensor la numpy array.

        Args:
            tensor: Tensorul de convertit
            remove_batch_dim: Elimină dimensiunea batch (prima)
            remove_channel_dim: Elimină dimensiunea channel

        Returns:
            np.ndarray: Array-ul numpy
        """
        try:
            # Mută pe CPU și convertește
            array = tensor.detach().cpu().numpy()

            # Elimină dimensiuni după necesitate
            if remove_batch_dim and array.shape[0] == 1:
                array = array.squeeze(0)
            if remove_channel_dim and array.ndim > 3 and array.shape[0] == 1:
                array = array.squeeze(0)

            logger.debug(f"Tensor to numpy: {tensor.shape} → {array.shape}")
            return array

        except Exception as e:
            logger.error(f"Eroare conversie tensor→numpy: {e}")
            raise

    @staticmethod
    def get_nifti_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extrage informații detaliate despre un fișier NIfTI.

        Args:
            file_path: Calea către fișier

        Returns:
            Dict cu informații despre fișier
        """
        if not NIfTIProcessor.validate_nifti_file(file_path):
            raise ValueError(f"Fișier NIfTI invalid: {file_path}")

        try:
            nifti_img = nib.load(str(file_path))
            data = nifti_img.get_fdata()
            header = nifti_img.header

            info = {
                "file_path": str(file_path),
                "shape": data.shape,
                "data_type": str(data.dtype),
                "value_range": [float(data.min()), float(data.max())],
                "voxel_sizes": list(header.get_zooms()),
                "affine_shape": nifti_img.affine.shape,
                "orientation": nib.aff2axcodes(nifti_img.affine),
                "file_size_mb": round(Path(file_path).stat().st_size / (1024*1024), 2),
                "header_info": {
                    "dim": list(header["dim"]),
                    "pixdim": list(header["pixdim"]),
                    "datatype": int(header["datatype"])
                }
            }

            logger.info(f"Info extrasa pentru {file_path}")
            return info

        except Exception as e:
            logger.error(f"Eroare extragere info NIfTI {file_path}: {e}")
            raise


# Funcții de conveniență
def load_nifti_data(file_path: Union[str, Path]) -> np.ndarray:
    """Funcție simplă pentru încărcarea doar a datelor."""
    data, _ = NIfTIProcessor.load_nifti(file_path)
    return data


def save_nifti_data(data: np.ndarray,
                   output_path: Union[str, Path],
                   reference_path: Optional[Union[str, Path]] = None) -> None:
    """Funcție simplă pentru salvarea datelor cu referință opțională."""
    reference_nifti = None
    if reference_path:
        _, reference_nifti = NIfTIProcessor.load_nifti(reference_path)

    NIfTIProcessor.save_nifti(data, output_path, reference_nifti)