# -*- coding: utf-8 -*-
"""
Postprocesare MONAI pentru segmentare gliome - cu overlay support
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
    """Postprocesare pentru segmentarea gliomelor post-tratament cu suport overlay"""

    def __init__(self):
        if not MONAI_AVAILABLE:
            raise ImportError("MONAI necesar pentru postprocesare")

        self.min_component_sizes = {
            1: 50,  # NETC
            2: 100,  # SNFH
            3: 20,  # ET
            4: 30  # RC
        }

        # Color mapping pentru overlay
        self.overlay_colors = {
            0: [0, 0, 0],  # Background - negru
            1: [0, 100, 255],  # NETC - albastru
            2: [255, 255, 0],  # SNFH - galben
            3: [255, 0, 0],  # ET - roșu
            4: [128, 0, 128],  # RC - violet
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

    def normalize_t1n_for_display(self, t1n_data: np.ndarray) -> np.ndarray:
        """
        Normalizează datele T1N pentru display (0-255)
        Păstrează windowing-ul medical pentru diagnostic
        """
        # Remove outliers pentru normalizare mai bună
        p1, p99 = np.percentile(t1n_data, [1, 99])

        # Clip la percentile pentru a evita outliers
        clipped = np.clip(t1n_data, p1, p99)

        # Normalizează la 0-255
        normalized = ((clipped - p1) / (p99 - p1)) * 255

        return normalized.astype(np.uint8)

    def create_overlay(self, t1n_data: np.ndarray, segmentation: np.ndarray,
                       alpha: float = 0.4) -> np.ndarray:
        """
        Creează overlay-ul cu T1N ca bază și segmentarea colorată peste

        Args:
            t1n_data: Datele T1N originale (H, W, D)
            segmentation: Segmentarea procesată (H, W, D)
            alpha: Transparența overlay-ului (0.0-1.0)

        Returns:
            Array RGB cu overlay (H, W, D, 3)
        """
        print(f"[OVERLAY] Creez overlay cu alpha={alpha}")

        # Normalizează T1N pentru display
        t1n_normalized = self.normalize_t1n_for_display(t1n_data)

        # Creează imaginea RGB de bază (grayscale)
        h, w, d = t1n_data.shape
        overlay_image = np.zeros((h, w, d, 3), dtype=np.uint8)

        # Setează canalele RGB cu valorile grayscale
        overlay_image[:, :, :, 0] = t1n_normalized  # R
        overlay_image[:, :, :, 1] = t1n_normalized  # G
        overlay_image[:, :, :, 2] = t1n_normalized  # B

        # Aplică overlay-ul colorat pentru fiecare clasă
        for class_id in range(1, 5):  # Skip background (0)
            if class_id not in segmentation:
                continue

            # Găsește pixelii din această clasă
            class_mask = (segmentation == class_id)
            if not np.any(class_mask):
                continue

            color = self.overlay_colors[class_id]

            # Blending: overlay = (1-alpha) * base + alpha * color
            for channel in range(3):
                overlay_image[class_mask, channel] = (
                        (1 - alpha) * overlay_image[class_mask, channel] +
                        alpha * color[channel]
                ).astype(np.uint8)

        print(f"[OVERLAY] Overlay creat cu succes: {overlay_image.shape}")
        return overlay_image

    def postprocess_segmentation(self, predictions: torch.Tensor) -> Tuple[np.ndarray, Dict]:
        """Pipeline complet de postprocesare"""
        # Converteste in clase
        classes = self.convert_predictions_to_classes(predictions)
        segmentation = classes.cpu().numpy() if isinstance(classes, torch.Tensor) else classes

        # Aplica postprocesare
        segmentation = self.apply_morphological_cleaning(segmentation)
        segmentation = self.remove_small_components(segmentation)

        # Statistici - converteste toate valorile numpy in tipuri Python
        unique_classes, counts = np.unique(segmentation, return_counts=True)
        class_stats = {int(cls): int(count) for cls, count in zip(unique_classes, counts)}

        stats = {
            "classes_found": [int(cls) for cls in unique_classes],
            "class_counts": class_stats,
            "total_segmented_voxels": int(sum(count for cls, count in class_stats.items() if cls > 0)),
            "segmentation_shape": [int(dim) for dim in segmentation.shape]
        }

        return segmentation, stats

    def save_as_nifti(self, segmentation: np.ndarray, folder_name: str,
                      output_base_dir: Path = None, reference_nifti: Optional[Path] = None) -> Path:
        """
        Salveaza segmentarea ca NIfTI într-un folder cu numele specificat
        """
        if output_base_dir is None:
            output_base_dir = Path("results")

        # Creeaza folderul pentru acest rezultat
        result_folder = output_base_dir / folder_name
        result_folder.mkdir(parents=True, exist_ok=True)

        # Calea către fisierul final
        output_path = result_folder / f"{folder_name}-seg.nii.gz"

        if reference_nifti and reference_nifti.exists():
            ref_img = nib.load(reference_nifti)
            nifti_img = nib.Nifti1Image(segmentation.astype(np.uint8), ref_img.affine, ref_img.header)
        else:
            nifti_img = nib.Nifti1Image(segmentation.astype(np.uint8), np.eye(4))

        nib.save(nifti_img, str(output_path))
        print(f"[POSTPROCESS] Segmentare salvată în: {output_path}")
        return output_path

    def save_overlay_as_nifti(self, overlay_image: np.ndarray, folder_name: str,
                              output_base_dir: Path = None, reference_nifti: Optional[Path] = None) -> Path:
        """
        Salvează overlay-ul ca NIfTI RGB

        Args:
            overlay_image: Array RGB (H, W, D, 3)
            folder_name: Numele folderului
            output_base_dir: Directorul de salvare
            reference_nifti: Fișier de referință pentru header

        Returns:
            Path către fișierul salvat
        """
        if output_base_dir is None:
            output_base_dir = Path("results")

        # Creeaza folderul pentru acest rezultat
        result_folder = output_base_dir / folder_name
        result_folder.mkdir(parents=True, exist_ok=True)

        # Calea către fisierul overlay
        output_path = result_folder / f"{folder_name}-overlay.nii.gz"

        # Pentru NIfTI RGB, trebuie să reorganizez dimensiunile: (H, W, D, 3) -> (H, W, D, 1, 3)
        # Sau să salvez ca 4D cu ultimul canal ca RGB
        nifti_data = overlay_image.astype(np.uint8)

        if reference_nifti and reference_nifti.exists():
            ref_img = nib.load(reference_nifti)
            # Pentru RGB, folosim header-ul de referință dar modificăm datatype
            header = ref_img.header.copy()
            header.set_data_dtype(np.uint8)
            nifti_img = nib.Nifti1Image(nifti_data, ref_img.affine, header)
        else:
            nifti_img = nib.Nifti1Image(nifti_data, np.eye(4))

        nib.save(nifti_img, str(output_path))
        print(f"[POSTPROCESS] Overlay salvat în: {output_path}")
        return output_path


# Functii utilitare
def create_postprocessor() -> GliomaPostprocessor:
    """Creeaza instanta postprocessor"""
    return GliomaPostprocessor()


def quick_postprocess(predictions: torch.Tensor, folder_name: str, output_base_dir: Path = None) -> Tuple[
    np.ndarray, Dict]:
    """Postprocesare rapida"""
    processor = create_postprocessor()
    segmentation, stats = processor.postprocess_segmentation(predictions)

    if folder_name:
        processor.save_as_nifti(segmentation, folder_name, output_base_dir)

    return segmentation, stats


# Instanta globala
_postprocessor = None


def get_postprocessor() -> GliomaPostprocessor:
    """Returneaza instanta globala a postprocessor-ului"""
    global _postprocessor
    if _postprocessor is None:
        _postprocessor = create_postprocessor()
    return _postprocessor