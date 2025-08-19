# -*- coding: utf-8 -*-
"""
Serviciu de preprocesare pentru fisiere NIfTI folosind MONAI
Adapteaza pipeline-ul pentru inferenta (validation/testing mode)
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import logging

try:
    from monai.transforms import (
        LoadImaged, EnsureChannelFirstd, Spacingd, Orientationd,
        ScaleIntensityRanged, CropForegroundd, ResizeWithPadOrCropd,
        ConcatItemsd, EnsureTyped, Compose
    )
    from monai.data import Dataset, DataLoader
    import nibabel as nib

    MONAI_AVAILABLE = True
except ImportError as e:
    print(f"AVERTISMENT: MONAI sau dependentele nu sunt disponibile: {e}")
    MONAI_AVAILABLE = False

from src.core.config import (
    IMG_SIZE, SPACING, ORIENTATION, INTENSITY_RANGES,
    TEMP_PROCESSING_DIR, NUM_CHANNELS
)
from src.utils.nifti_validation import get_modality_files_mapping

logger = logging.getLogger(__name__)


class NIfTIPreprocessor:
    """
    Preprocesorul pentru fisiere NIfTI folosind MONAI transforms
    Adapteaza pipeline-ul pentru inferenta (fara augmentari)
    """

    def __init__(self):
        self.transforms = None
        self.is_initialized = False

        if not MONAI_AVAILABLE:
            raise ImportError("MONAI nu este disponibil. Instaleaza cu: pip install monai")

        self._create_transforms()

    def _create_transforms(self) -> None:
        """
        Creeaza pipeline-ul de transforms pentru inferenta
        Bazat pe functia create_transforms cu is_train=False
        """
        try:
            print("[PREPROCESS] Creeaza pipeline transforms pentru inferenta...")

            # Define keys pentru transformari (4 modalitati)
            image_keys = ["image_t1n", "image_t1c", "image_t2w", "image_t2f"]
            all_keys = image_keys  # Pentru inferenta nu avem segmentare

            # ========== TRANSFORMS COMUNE (ca in functia ta) ==========

            common_transforms = [
                # incarca imaginile din fisiere NIfTI
                LoadImaged(keys=all_keys),

                # Asigura formatul channel-first (BCHWD pentru MONAI)
                EnsureChannelFirstd(keys=all_keys),

                # Standardizeaza voxel spacing la (1.0, 1.0, 1.0) mm
                Spacingd(
                    keys=all_keys,
                    pixdim=SPACING,
                    mode=["bilinear"] * len(image_keys),  # bilinear pentru toate imaginile
                ),

                # Asigura orientarea consistenta "RAI"
                Orientationd(
                    keys=all_keys,
                    axcodes=ORIENTATION,
                ),
            ]

            # ========== NORMALIZARE INTENSITATE ==========

            intensity_transforms = [
                # Normalizeaza intensitatea pentru fiecare modalitate
                ScaleIntensityRanged(
                    keys=["image_t1n"],
                    a_min=INTENSITY_RANGES["t1n"]["a_min"],
                    a_max=INTENSITY_RANGES["t1n"]["a_max"],
                    b_min=INTENSITY_RANGES["t1n"]["b_min"],
                    b_max=INTENSITY_RANGES["t1n"]["b_max"],
                    clip=True,
                ),
                ScaleIntensityRanged(
                    keys=["image_t1c"],
                    a_min=INTENSITY_RANGES["t1c"]["a_min"],
                    a_max=INTENSITY_RANGES["t1c"]["a_max"],
                    b_min=INTENSITY_RANGES["t1c"]["b_min"],
                    b_max=INTENSITY_RANGES["t1c"]["b_max"],
                    clip=True,
                ),
                ScaleIntensityRanged(
                    keys=["image_t2w"],
                    a_min=INTENSITY_RANGES["t2w"]["a_min"],
                    a_max=INTENSITY_RANGES["t2w"]["a_max"],
                    b_min=INTENSITY_RANGES["t2w"]["b_min"],
                    b_max=INTENSITY_RANGES["t2w"]["b_max"],
                    clip=True,
                ),
                ScaleIntensityRanged(
                    keys=["image_t2f"],
                    a_min=INTENSITY_RANGES["t2f"]["a_min"],
                    a_max=INTENSITY_RANGES["t2f"]["a_max"],
                    b_min=INTENSITY_RANGES["t2f"]["b_min"],
                    b_max=INTENSITY_RANGES["t2f"]["b_max"],
                    clip=True,
                ),
            ]

            # ========== TRANSFORMS SPAtIALE (pentru inferenta) ==========

            spatial_transforms = [
                # Crop background folosind imaginea T1n pentru identificarea creierului
                CropForegroundd(
                    keys=all_keys,
                    source_key="image_t1n",  # Foloseste T1n pentru identificarea creierului
                    margin=10,  # Margine mica pentru tot creierul
                ),

                # Resize la dimensiunea consistenta pentru inferenta
                ResizeWithPadOrCropd(
                    keys=all_keys,
                    spatial_size=IMG_SIZE,
                ),

                # Concateneaza cele 4 modalitati intr-un tensor multi-channel
                ConcatItemsd(
                    keys=image_keys,
                    name="image",
                    dim=0,  # Concateneaza pe dimensiunea channel-urilor
                ),
            ]

            # ========== CONVERSIE FINALa ==========

            type_transforms = [
                EnsureTyped(
                    keys=["image"],
                    dtype=torch.float32
                )
            ]

            # ========== COMBINa TOATE TRANSFORMS ==========

            self.transforms = Compose(
                common_transforms +
                intensity_transforms +
                spatial_transforms +
                type_transforms
            )

            self.is_initialized = True
            print("[PREPROCESS] Pipeline transforms creat cu succes!")
            print(f"    - Dimensiune finala: {IMG_SIZE}")
            print(f"    - Spacing: {SPACING}")
            print(f"    - Orientare: {ORIENTATION}")
            print(f"    - Canale output: {NUM_CHANNELS}")

        except Exception as e:
            logger.error(f"Eroare la crearea transforms: {str(e)}")
            raise RuntimeError(f"Nu s-a putut crea pipeline-ul de transforms: {str(e)}")

    def preprocess_folder(self, folder_path: Path) -> Dict[str, Any]:
        """
        Preproceseaza toate fisierele dintr-un folder validat

        Args:
            folder_path: Calea catre folderul cu modalitatile validate

        Returns:
            Dict cu datele preprocesate si metadata

        Raises:
            ValueError: Daca folderul nu contine modalitatile necesare
            RuntimeError: Daca preprocesarea esueaza
        """
        if not self.is_initialized:
            raise RuntimeError("Preprocesorul nu este initializat")

        try:
            print(f"[PREPROCESS] incepe preprocesarea folderului: {folder_path.name}")

            # Obtine mapping-ul modalitate -> fisier
            modality_mapping = get_modality_files_mapping(folder_path)

            if modality_mapping is None:
                raise ValueError(f"Folderul {folder_path.name} nu contine toate modalitatile necesare")

            print(f"[PREPROCESS] Modalitati gasite: {list(modality_mapping.keys())}")

            # Creeaza dictionarul pentru MONAI transforms
            data_dict = {
                "image_t1n": str(modality_mapping["t1n"]),
                "image_t1c": str(modality_mapping["t1c"]),
                "image_t2w": str(modality_mapping["t2w"]),
                "image_t2f": str(modality_mapping["t2f"])
            }

            print("[PREPROCESS] Aplica transforms...")

            # Aplica transforms
            processed_data = self.transforms(data_dict)

            # Extrage tensorul final
            image_tensor = processed_data["image"]

            print(f"[PREPROCESS] Preprocesare completa!")
            print(f"    - Shape final: {list(image_tensor.shape)}")
            print(f"    - Dtype: {image_tensor.dtype}")
            print(f"    - Device: {image_tensor.device}")
            print(f"    - Min/Max: {image_tensor.min():.3f}/{image_tensor.max():.3f}")

            # Verifica shape-ul final
            expected_shape = (NUM_CHANNELS,) + IMG_SIZE
            if image_tensor.shape != expected_shape:
                print(f"[WARNING] Shape neasteptat: {list(image_tensor.shape)} vs {expected_shape}")

            result = {
                "image_tensor": image_tensor,
                "original_paths": modality_mapping,
                "processed_shape": list(image_tensor.shape),
                "folder_name": folder_path.name,
                "preprocessing_config": {
                    "img_size": IMG_SIZE,
                    "spacing": SPACING,
                    "orientation": ORIENTATION,
                    "intensity_ranges": INTENSITY_RANGES
                }
            }

            return result

        except Exception as e:
            logger.error(f"Eroare la preprocesarea folderului {folder_path}: {str(e)}")
            raise RuntimeError(f"Preprocesarea a esuat: {str(e)}")

    def save_preprocessed_data(self,
                               preprocessed_data: Dict[str, Any],
                               output_path: Optional[Path] = None) -> Path:
        """
        Salveaza datele preprocesate pe disc

        Args:
            preprocessed_data: Datele returnate de preprocess_folder()
            output_path: Calea de salvare (optional)

        Returns:
            Calea catre fisierul salvat
        """
        try:
            if output_path is None:
                folder_name = preprocessed_data["folder_name"]
                output_path = TEMP_PROCESSING_DIR / f"{folder_name}_preprocessed.pt"

            # Asigura ca directorul exista
            output_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"[PREPROCESS] Salveaza datele preprocesate in: {output_path}")

            # Salveaza folosind torch.save
            save_data = {
                "image_tensor": preprocessed_data["image_tensor"],
                "metadata": {
                    "original_paths": {k: str(v) for k, v in preprocessed_data["original_paths"].items()},
                    "processed_shape": preprocessed_data["processed_shape"],
                    "folder_name": preprocessed_data["folder_name"],
                    "preprocessing_config": preprocessed_data["preprocessing_config"]
                }
            }

            torch.save(save_data, output_path)

            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            print(f"[PREPROCESS] Date salvate cu succes ({file_size:.1f} MB)")

            return output_path

        except Exception as e:
            logger.error(f"Eroare la salvarea datelor preprocesate: {str(e)}")
            raise RuntimeError(f"Salvarea a esuat: {str(e)}")

    def load_preprocessed_data(self, file_path: Path) -> Dict[str, Any]:
        """
        incarca datele preprocesate salvate anterior

        Args:
            file_path: Calea catre fisierul .pt

        Returns:
            Dict cu datele incarcate
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"Fisierul nu exista: {file_path}")

            print(f"[PREPROCESS] incarca datele preprocesate din: {file_path}")

            data = torch.load(file_path, map_location='cpu')

            print(f"[PREPROCESS] Date incarcate cu succes")
            print(f"    - Shape: {list(data['image_tensor'].shape)}")
            print(f"    - Folder original: {data['metadata']['folder_name']}")

            return data

        except Exception as e:
            logger.error(f"Eroare la incarcarea datelor preprocesate: {str(e)}")
            raise RuntimeError(f"incarcarea a esuat: {str(e)}")

    def get_preprocessing_info(self) -> Dict[str, Any]:
        """
        Returneaza informatii despre configuratia de preprocesare

        Returns:
            Dict cu informatii despre configuratie
        """
        return {
            "is_initialized": self.is_initialized,
            "img_size": IMG_SIZE,
            "spacing": SPACING,
            "orientation": ORIENTATION,
            "num_channels": NUM_CHANNELS,
            "intensity_ranges": INTENSITY_RANGES,
            "monai_available": MONAI_AVAILABLE
        }


# Instanta globala singleton
_preprocessor = None


def get_preprocessor() -> NIfTIPreprocessor:
    """
    Returneaza instanta globala a preprocesorului (singleton pattern)

    Returns:
        Instanta NIfTIPreprocessor
    """
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = NIfTIPreprocessor()
    return _preprocessor


def preprocess_folder_simple(folder_path: Path) -> Dict[str, Any]:
    """
    Functie simpla pentru preprocesarea unui folder

    Args:
        folder_path: Calea catre folderul cu modalitatile

    Returns:
        Dict cu datele preprocesate
    """
    preprocessor = get_preprocessor()
    return preprocessor.preprocess_folder(folder_path)