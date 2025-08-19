# -*- coding: utf-8 -*-
"""
Postprocesare MONAI pentru segmentare gliome - versiune simplificata
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import nibabel as nib

try:
    from monai.transforms import AsDiscrete, KeepLargestConnectedComponent

    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False

from scipy.ndimage import binary_fill_holes, binary_opening, label


class GliomaPostprocessor:
    """Postprocesare pentru segmentarea gliomelor post-tratament"""

    def __init__(self):
        if not MONAI_AVAILABLE:
            raise ImportError("MONAI necesar pentru postprocesare")

        self.min_component_sizes = {
            1: 50,  # NETC
            2: 100,  # SNFH
            3: 20,  # ET
            4: 30  # RC
        }

    def convert_predictions_to_classes(self, predictions: torch.Tensor) -> torch.Tensor:
        """Converteste predictii in clase discrete"""
        if predictions.dim() == 4:  # (C, H, W, D)
            predictions = predictions.unsqueeze(0)

        with torch.no_grad():
            probs = torch.softmax(predictions, dim=1)
            classes = torch.argmax(probs, dim=1)

        if classes.shape[0] == 1:
            classes = classes.squeeze(0)

        return classes

    def apply_morphological_cleaning(self, segmentation: np.ndarray) -> np.ndarray:
        """Aplica operatii morfologice pentru curatare"""
        cleaned = segmentation.copy()

        for class_id in range(1, 5):
            if class_id not in segmentation:
                continue

            class_mask = (cleaned == class_id)
            if class_mask.sum() == 0:
                continue

            # Binary opening + fill holes
            iterations = 1 if class_id in [1, 3, 4] else 2
            opened_mask = binary_opening(class_mask, iterations=iterations)
            filled_mask = binary_fill_holes(opened_mask)

            cleaned[class_mask] = 0
            cleaned[filled_mask] = class_id

        return cleaned

    def remove_small_components(self, segmentation: np.ndarray) -> np.ndarray:
        """Elimina componentele conexe mici"""
        filtered = segmentation.copy()

        for class_id in range(1, 5):
            if class_id not in segmentation:
                continue

            class_mask = (filtered == class_id)
            if class_mask.sum() == 0:
                continue

            labeled_array, num_components = label(class_mask)
            min_size = self.min_component_sizes.get(class_id, 50)

            for comp_id in range(1, num_components + 1):
                component_mask = (labeled_array == comp_id)
                if component_mask.sum() < min_size:
                    filtered[component_mask] = 0

        return filtered

    def postprocess_segmentation(self, predictions: torch.Tensor) -> Tuple[np.ndarray, Dict]:
        """Pipeline complet de postprocesare"""
        # Converteste in clase
        classes = self.convert_predictions_to_classes(predictions)
        segmentation = classes.cpu().numpy() if isinstance(classes, torch.Tensor) else classes

        # Aplica postprocesare
        segmentation = self.apply_morphological_cleaning(segmentation)
        segmentation = self.remove_small_components(segmentation)

        # Statistici - FIXED: converteste toate valorile numpy in tipuri Python
        unique_classes, counts = np.unique(segmentation, return_counts=True)
        class_stats = {int(cls): int(count) for cls, count in zip(unique_classes, counts)}

        stats = {
            "classes_found": [int(cls) for cls in unique_classes],  # Convert numpy.int64 to int
            "class_counts": class_stats,
            "total_segmented_voxels": int(sum(count for cls, count in class_stats.items() if cls > 0)),
            # Convert to int
            "segmentation_shape": [int(dim) for dim in segmentation.shape]  # Convert shape tuple to list of ints
        }

        return segmentation, stats

    def save_as_nifti(self, segmentation: np.ndarray, output_path: Path,
                      reference_nifti: Optional[Path] = None) -> Path:
        """Salveaza segmentarea ca NIfTI"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if reference_nifti and reference_nifti.exists():
            ref_img = nib.load(reference_nifti)
            nifti_img = nib.Nifti1Image(segmentation.astype(np.uint8), ref_img.affine, ref_img.header)
        else:
            nifti_img = nib.Nifti1Image(segmentation.astype(np.uint8), np.eye(4))

        nib.save(nifti_img, str(output_path))
        return output_path


# Functii utilitare
def create_postprocessor() -> GliomaPostprocessor:
    """Creeaza instanta postprocessor"""
    return GliomaPostprocessor()


def quick_postprocess(predictions: torch.Tensor, output_path: Path = None) -> Tuple[np.ndarray, Dict]:
    """Postprocesare rapida"""
    processor = create_postprocessor()
    segmentation, stats = processor.postprocess_segmentation(predictions)

    if output_path:
        processor.save_as_nifti(segmentation, output_path)

    return segmentation, stats


# Instanta globala
_postprocessor = None


def get_postprocessor() -> GliomaPostprocessor:
    """Returneaza instanta globala a postprocessor-ului"""
    global _postprocessor
    if _postprocessor is None:
        _postprocessor = create_postprocessor()
    return _postprocessor