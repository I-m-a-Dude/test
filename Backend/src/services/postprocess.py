# -*- coding: utf-8 -*-
"""
Postprocesare MONAI pentru segmentare gliome - cu overlay support FIXED
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
    """Postprocesare pentru segmentarea gliomelor post-tratament cu suport overlay FIXED"""

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
            1: [100, 180, 255],  # NETC - lighter blue
            2: [255, 255, 150],  # SNFH - lighter yellow
            3: [255, 100, 100],  # ET - lighter red
            4: [200, 100, 200],  # RC - lighter violet
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

    def normalize_t1n_for_overlay(self, t1n_data: np.ndarray) -> np.ndarray:
        """
        Normalizează datele T1N pentru overlay păstrând aspectul original (nu grayscale)
        FIXED: Păstrează imaginea originală, nu o face grayscale
        """
        print(f"[OVERLAY] Normalizez T1N: shape={t1n_data.shape}, dtype={t1n_data.dtype}")

        # Remove outliers pentru normalizare mai bună dar păstrează aspectul original
        non_zero_mask = t1n_data > 0
        if not np.any(non_zero_mask):
            print("[OVERLAY] WARNING: Toate valorile T1N sunt 0")
            return np.zeros_like(t1n_data, dtype=np.uint8)

        non_zero_values = t1n_data[non_zero_mask]
        p1, p99 = np.percentile(non_zero_values, [1, 99])

        print(f"[OVERLAY] Range original: {t1n_data.min():.2f} - {t1n_data.max():.2f}")
        print(f"[OVERLAY] Range percentile: {p1:.2f} - {p99:.2f}")

        # Clip la percentile pentru a evita outliers
        clipped = np.clip(t1n_data, p1, p99)

        # Normalizează la 0-255 PĂSTRÂND aspectul original (nu grayscale)
        if p99 > p1:
            normalized = ((clipped - p1) / (p99 - p1)) * 255
        else:
            normalized = np.zeros_like(clipped)

        result = normalized.astype(np.uint8)
        print(f"[OVERLAY] Normalizare completă: {result.min()} - {result.max()}")

        return result

    def create_overlay_with_subtle_t1n(self, t1n_data: np.ndarray, segmentation: np.ndarray,
                                       segmentation_alpha: float = 0.4,
                                       t1n_background_opacity: float = 0.65) -> np.ndarray:
        """
        Creează overlay cu segmentare TRANSPARENTĂ peste T1N vizibil

        Args:
            t1n_data: Datele T1N preprocesate (H, W, D)
            segmentation: Segmentarea procesată (H, W, D)
            segmentation_alpha: Transparența segmentării (0.0-1.0, mai mic = mai transparent)
            t1n_background_opacity: Opacitatea T1N în background (0.0-1.0)

        Returns:
            Array RGB cu overlay transparent (H, W, D, 3)
        """
        print(f"[OVERLAY] Creez overlay cu segmentare transparentă (alpha={segmentation_alpha})")

        # Normalizează T1N pentru background vizibil
        t1n_normalized = ((t1n_data - t1n_data.min()) / (t1n_data.max() - t1n_data.min()) * 255).astype(np.uint8)

        h, w, d = t1n_data.shape
        overlay_image = np.zeros((h, w, d, 3), dtype=np.uint8)

        # Setează T1N ca bază pe toate canalele (grayscale vizibil)
        for channel in range(3):
            overlay_image[:, :, :, channel] = (t1n_normalized * t1n_background_opacity).astype(np.uint8)

        # Aplică culorile segmentării TRANSPARENT peste T1N
        for class_id in range(1, 5):
            class_mask = (segmentation == class_id)
            if not np.any(class_mask):
                continue

            color = self.overlay_colors[class_id]

            # Blending transparent: overlay = (1-alpha) * t1n + alpha * culoare_segmentare
            for channel in range(3):
                current_t1n = overlay_image[class_mask, channel].astype(float)
                segmentation_color = float(color[channel])

                blended = (1 - segmentation_alpha) * current_t1n + segmentation_alpha * segmentation_color
                overlay_image[class_mask, channel] = blended.astype(np.uint8)

        print(f"[OVERLAY] Overlay transparent creat: {overlay_image.shape}")
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
        FIXED: Salvează overlay-ul ca NIfTI RGB

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

        print(f"[OVERLAY] Salvând overlay: {overlay_image.shape} -> {output_path}")

        # Convertim RGBA la format compatibil NIfTI
        # NIfTI nu suportă nativ RGB, dar putem salva ca 4D cu ultimul canal ca RGB
        nifti_data = overlay_image.astype(np.uint8)

        if reference_nifti and reference_nifti.exists():
            ref_img = nib.load(reference_nifti)
            # Pentru RGB, creăm un header nou compatibil
            affine = ref_img.affine.copy()
            header = ref_img.header.copy()
            header.set_data_dtype(np.uint8)
            nifti_img = nib.Nifti1Image(nifti_data, affine, header)
        else:
            # Creăm un affine simplu 4x4 pentru RGB
            affine = np.eye(4)
            nifti_img = nib.Nifti1Image(nifti_data, affine)

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