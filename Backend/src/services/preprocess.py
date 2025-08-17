# -*- coding: utf-8 -*-
"""
Preprocesare pentru fișiere NIfTI folosind MONAI transforms
Adaptat pentru inference din fișiere ZIP
"""
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging

try:
    from monai.transforms import (
        LoadImaged, EnsureChannelFirstd, Spacingd, Orientationd,
        ScaleIntensityRanged, CropForegroundd, ResizeWithPadOrCropd,
        ConcatItemsd, EnsureTyped, Compose, SpatialPadd
    )
    from monai.data import Dataset
    import nibabel as nib

    MONAI_AVAILABLE = True
except ImportError as e:
    print(f"[PREPROCESS] MONAI nu este disponibil: {e}")
    MONAI_AVAILABLE = False

from src.core.config import NUM_CHANNELS, TEMP_PROCESSING_DIR

logger = logging.getLogger(__name__)

# Configurări pentru preprocesare
IMG_SIZE = (128, 128, 128)  # Dimensiune standard pentru model
TARGET_SPACING = (1.0, 1.0, 1.0)  # Spacing standard în mm
TARGET_ORIENTATION = "RAI"  # Right, Anterior, Inferior

# Maparea modalităților MRI pentru BraTS
MODALITY_MAPPING = {
    't1': 'image_t1n',
    't1n': 'image_t1n',
    't1c': 'image_t1c',
    't1ce': 'image_t1c',  # alias
    't2': 'image_t2w',
    't2w': 'image_t2w',
    'flair': 'image_t2f',
    't2f': 'image_t2f'
}

# Parametrii de normalizare pentru fiecare modalitate
INTENSITY_RANGES = {
    'image_t1n': {'a_min': 0, 'a_max': 3000, 'b_min': 0.0, 'b_max': 1.0},
    'image_t1c': {'a_min': 0, 'a_max': 3000, 'b_min': 0.0, 'b_max': 1.0},
    'image_t2w': {'a_min': 0, 'a_max': 3500, 'b_min': 0.0, 'b_max': 1.0},
    'image_t2f': {'a_min': 0, 'a_max': 3500, 'b_min': 0.0, 'b_max': 1.0}
}


class NIfTIPreprocessor:
    """
    Preprocesează fișiere NIfTI pentru inferența cu MedNeXt
    """

    def __init__(self,
                 target_size: Tuple[int, int, int] = IMG_SIZE,
                 target_spacing: Tuple[float, float, float] = TARGET_SPACING,
                 target_orientation: str = TARGET_ORIENTATION):

        if not MONAI_AVAILABLE:
            raise ImportError("MONAI este necesar pentru preprocesare")

        self.target_size = target_size
        self.target_spacing = target_spacing
        self.target_orientation = target_orientation

        print(f"[PREPROCESS] Inițializat cu:")
        print(f"    - Target size: {target_size}")
        print(f"    - Target spacing: {target_spacing}")
        print(f"    - Target orientation: {target_orientation}")

    def identify_modalities(self, nifti_files: List[Path]) -> Dict[str, Path]:
        """
        Identifică modalitățile MRI din numele fișierelor

        Args:
            nifti_files: Lista cu căile către fișiere NIfTI

        Returns:
            Dict cu maparea modalitate -> cale fișier
        """
        modalities = {}

        for file_path in nifti_files:
            filename = file_path.name.lower()

            # Încearcă să identifice modalitatea din numele fișierului
            for identifier, modality in MODALITY_MAPPING.items():
                if identifier in filename:
                    modalities[modality] = file_path
                    break

        print(f"[PREPROCESS] Modalități identificate: {list(modalities.keys())}")

        return modalities

    def validate_modalities(self, modalities: Dict[str, Path]) -> bool:
        """
        Validează că avem modalitățile necesare pentru model

        Args:
            modalities: Dict cu modalitățile identificate

        Returns:
            True dacă avem suficiente modalități
        """
        required_modalities = ['image_t1n', 'image_t1c', 'image_t2w', 'image_t2f']
        available = list(modalities.keys())

        missing = [mod for mod in required_modalities if mod not in available]

        if missing:
            print(f"[PREPROCESS] ATENȚIE: Lipsesc modalități: {missing}")
            print(f"[PREPROCESS] Disponibile: {available}")

            # Pentru demo, acceptăm și cu modalități lipsă
            # Modelul va trebui adaptat sau vor fi folosite duplicate
            return len(available) > 0

        print(f"[PREPROCESS] Toate modalitățile sunt disponibile")
        return True

    def create_inference_transforms(self, modalities: List[str]) -> Compose:
        """
        Creează pipeline-ul de transformări pentru inferență

        Args:
            modalities: Lista cu modalitățile disponibile

        Returns:
            Pipeline MONAI Compose
        """

        # Transformări de bază pentru toate modalitățile
        basic_transforms = [
            # Încarcă imaginile
            LoadImaged(keys=modalities),

            # Asigură formatul channel-first
            EnsureChannelFirstd(keys=modalities),

            # Standardizează spacing-ul
            Spacingd(
                keys=modalities,
                pixdim=self.target_spacing,
                mode="bilinear",  # bilinear pentru imagini
            ),

            # Standardizează orientarea
            Orientationd(
                keys=modalities,
                axcodes=self.target_orientation,
            ),
        ]

        # Normalizare intensitate pentru fiecare modalitate
        intensity_transforms = []
        for modality in modalities:
            if modality in INTENSITY_RANGES:
                params = INTENSITY_RANGES[modality]
                intensity_transforms.append(
                    ScaleIntensityRanged(
                        keys=[modality],
                        **params,
                        clip=True,
                    )
                )

        # Transformări spațiale
        spatial_transforms = [
            # Croppează background-ul
            CropForegroundd(
                keys=modalities,
                source_key=modalities[0],  # Folosește prima modalitate
                margin=10,
            ),

            # Redimensionează la dimensiunea dorită
            ResizeWithPadOrCropd(
                keys=modalities,
                spatial_size=self.target_size,
            ),
        ]

        # Combinare modalități (dacă avem 4)
        if len(modalities) == 4:
            combination_transforms = [
                ConcatItemsd(
                    keys=modalities,
                    name="image",
                    dim=0,  # Concatenează pe dimensiunea channel
                ),
            ]
        else:
            # Dacă nu avem 4 modalități, duplicăm sau adaptăm
            combination_transforms = [
                # Va fi implementat în funcție de cazul specific
            ]

        # Conversie finală
        final_transforms = [
            EnsureTyped(
                keys=["image"],
                dtype=torch.float32
            )
        ]

        # Combinăm toate transformările
        all_transforms = (
                basic_transforms +
                intensity_transforms +
                spatial_transforms +
                combination_transforms +
                final_transforms
        )

        return Compose(all_transforms)

    def handle_missing_modalities(self, modalities: Dict[str, Path]) -> Dict[str, Path]:
        """
        Gestionează cazurile cu modalități lipsă

        Args:
            modalities: Dict cu modalitățile disponibile

        Returns:
            Dict completat cu 4 modalități (duplicate dacă e necesar)
        """
        required = ['image_t1n', 'image_t1c', 'image_t2w', 'image_t2f']
        completed = modalities.copy()

        # Dacă avem cel puțin o modalitate, duplicăm pentru celelalte
        if modalities:
            available_modality = list(modalities.values())[0]

            for req_mod in required:
                if req_mod not in completed:
                    completed[req_mod] = available_modality
                    print(f"[PREPROCESS] Duplicat {available_modality.name} pentru {req_mod}")

        return completed

    def preprocess_batch(self, nifti_files: List[Path]) -> Tuple[torch.Tensor, Dict]:
        """
        Preprocesează un batch de fișiere NIfTI

        Args:
            nifti_files: Lista cu fișiere NIfTI

        Returns:
            Tuple cu (tensor_preprocessat, metadata)
        """
        try:
            print(f"[PREPROCESS] Procesează {len(nifti_files)} fișiere")

            # Identifică modalitățile
            modalities = self.identify_modalities(nifti_files)

            if not modalities:
                raise ValueError("Nu s-au putut identifica modalități din fișiere")

            # Completează modalitățile lipsă dacă e necesar
            if len(modalities) < 4:
                modalities = self.handle_missing_modalities(modalities)

            # Validează
            if not self.validate_modalities(modalities):
                raise ValueError("Modalitățile nu sunt suficiente pentru procesare")

            # Creează transformările
            modality_keys = list(modalities.keys())
            transforms = self.create_inference_transforms(modality_keys)

            # Pregătește datele pentru MONAI
            data_dict = {key: str(path) for key, path in modalities.items()}

            print(f"[PREPROCESS] Aplicare transformări...")

            # Aplică transformările
            transformed_data = transforms(data_dict)

            # Extrage tensor-ul final
            if "image" in transformed_data:
                image_tensor = transformed_data["image"]
            else:
                # Fallback dacă nu avem concatenare
                tensors = [transformed_data[key] for key in modality_keys]
                image_tensor = torch.cat(tensors, dim=0)

            # Adaugă dimensiunea batch dacă lipsește
            if image_tensor.dim() == 4:  # CHWD
                image_tensor = image_tensor.unsqueeze(0)  # BCHWD

            print(f"[PREPROCESS] Tensor final shape: {image_tensor.shape}")

            # Metadata
            metadata = {
                "original_files": [str(path) for path in nifti_files],
                "modalities_used": list(modalities.keys()),
                "target_size": self.target_size,
                "target_spacing": self.target_spacing,
                "tensor_shape": list(image_tensor.shape),
                "dtype": str(image_tensor.dtype)
            }

            return image_tensor, metadata

        except Exception as e:
            logger.error(f"Eroare la preprocesare: {str(e)}")
            raise RuntimeError(f"Preprocesarea a eșuat: {str(e)}")

    def preprocess_single_file(self, nifti_file: Path) -> Tuple[torch.Tensor, Dict]:
        """
        Preprocesează un singur fișier NIfTI

        Args:
            nifti_file: Calea către fișierul NIfTI

        Returns:
            Tuple cu (tensor_preprocessat, metadata)
        """
        return self.preprocess_batch([nifti_file])


# Funcții utilitare

def get_nifti_files(folder_path: Path) -> List[Path]:
    """
    Găsește toate fișierele NIfTI dintr-un folder

    Args:
        folder_path: Calea către folder

    Returns:
        Lista cu fișiere NIfTI
    """
    nifti_files = []

    # Căută fișiere .nii și .nii.gz
    for pattern in ["*.nii", "*.nii.gz"]:
        nifti_files.extend(folder_path.glob(pattern))

    return sorted(nifti_files)


def create_preprocessor() -> NIfTIPreprocessor:
    """
    Creează o instanță de preprocessor cu configurările standard

    Returns:
        Instanță NIfTIPreprocessor
    """
    return NIfTIPreprocessor(
        target_size=IMG_SIZE,
        target_spacing=TARGET_SPACING,
        target_orientation=TARGET_ORIENTATION
    )


# Instanță globală
_preprocessor = None


def get_preprocessor() -> NIfTIPreprocessor:
    """
    Returnează instanța globală a preprocessor-ului (singleton)

    Returns:
        Instanță NIfTIPreprocessor
    """
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = create_preprocessor()
    return _preprocessor