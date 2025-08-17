# -*- coding: utf-8 -*-
"""
Postprocesare pentru rezultatele de segmentare MedNeXt folosind MONAI
Convertește predicțiile modelului înapoi în format NIfTI salvabil
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import logging

try:
    from monai.transforms import (
        AsDiscrete, KeepLargestConnectedComponent,
        FillHoles, SpatialPad, Resize, Spacing, Orientation,
        Compose, EnsureType, SaveImage
    )
    from monai.data import MetaTensor
    import nibabel as nib

    MONAI_AVAILABLE = True
except ImportError as e:
    print(f"[POSTPROCESS] MONAI nu este disponibil: {e}")
    MONAI_AVAILABLE = False

from src.core.config import TEMP_RESULTS_DIR, NUM_CLASSES
from scipy import ndimage
from scipy.ndimage import binary_fill_holes, binary_opening, label

logger = logging.getLogger(__name__)

# Configurări postprocesare
MIN_COMPONENT_SIZE = {
    1: 50,  # NETC - minim 50 voxeli
    2: 100,  # SNFH - minim 100 voxeli
    3: 20,  # ET - minim 20 voxeli
    4: 30  # RC - minim 30 voxeli
}

MORPHOLOGICAL_ITERATIONS = {
    1: 1,  # NETC - opening ușor
    2: 2,  # SNFH - opening mai agresiv
    3: 1,  # ET - opening ușor
    4: 1  # RC - opening ușor
}


class SegmentationPostprocessor:
    """
    Postprocesează rezultatele de segmentare pentru output final
    """

    def __init__(self,
                 confidence_threshold: float = 0.5,
                 apply_morphological: bool = True,
                 remove_small_components: bool = True,
                 fill_holes: bool = True):

        if not MONAI_AVAILABLE:
            raise ImportError("MONAI este necesar pentru postprocesare")

        self.confidence_threshold = confidence_threshold
        self.apply_morphological = apply_morphological
        self.remove_small_components = remove_small_components
        self.fill_holes = fill_holes

        print(f"[POSTPROCESS] Inițializat cu:")
        print(f"    - Confidence threshold: {confidence_threshold}")
        print(f"    - Morphological ops: {apply_morphological}")
        print(f"    - Remove small components: {remove_small_components}")
        print(f"    - Fill holes: {fill_holes}")

    def convert_predictions_to_classes(self, predictions: torch.Tensor) -> torch.Tensor:
        """
        Convertește predicțiile probabiliste în clase discrete

        Args:
            predictions: Tensor cu predicții (B, C, H, W, D) sau (C, H, W, D)

        Returns:
            Tensor cu clase discrete (B, H, W, D) sau (H, W, D)
        """
        print(f"[POSTPROCESS] Input predictions shape: {predictions.shape}")

        # Asigură că avem dimensiunea batch
        if predictions.dim() == 4:  # (C, H, W, D)
            predictions = predictions.unsqueeze(0)  # (1, C, H, W, D)

        # Aplicăm softmax pentru a obține probabilități
        if predictions.requires_grad:
            predictions = predictions.detach()

        probs = torch.softmax(predictions, dim=1)

        # Convertim în clase discrete folosind argmax
        class_predictions = torch.argmax(probs, dim=1)  # (B, H, W, D)

        print(f"[POSTPROCESS] Output classes shape: {class_predictions.shape}")
        print(f"[POSTPROCESS] Clase găsite: {torch.unique(class_predictions).tolist()}")

        return class_predictions

    def apply_morphological_operations(self, segmentation: np.ndarray) -> np.ndarray:
        """
        Aplică operații morfologice pentru curățarea segmentării

        Args:
            segmentation: Array 3D cu segmentarea (H, W, D)

        Returns:
            Array 3D procesat
        """
        if not self.apply_morphological:
            return segmentation

        print(f"[POSTPROCESS] Aplicare operații morfologice...")
        processed = segmentation.copy()

        # Procesează fiecare clasă separat
        for class_id in range(1, NUM_CLASSES):  # Skip background (0)
            if class_id not in processed:
                continue

            # Extrage masca pentru clasa curentă
            class_mask = (processed == class_id)

            if class_mask.sum() == 0:
                continue

            print(f"    - Clasa {class_id}: {class_mask.sum()} voxeli")

            # Aplicăm binary opening pentru a elimina noise-ul
            iterations = MORPHOLOGICAL_ITERATIONS.get(class_id, 1)
            cleaned_mask = binary_opening(class_mask, iterations=iterations)

            # Fill holes dacă este activat
            if self.fill_holes:
                cleaned_mask = binary_fill_holes(cleaned_mask)

            # Actualizează segmentarea
            processed[class_mask] = 0  # Șterge vechea clasă
            processed[cleaned_mask] = class_id  # Setează clasa curățată

            voxels_after = cleaned_mask.sum()
            print(f"    - După curățare: {voxels_after} voxeli (diferență: {class_mask.sum() - voxels_after})")

        return processed

    def remove_small_connected_components(self, segmentation: np.ndarray) -> np.ndarray:
        """
        Elimină componentele conexe mici

        Args:
            segmentation: Array 3D cu segmentarea (H, W, D)

        Returns:
            Array 3D cu componentele mici eliminate
        """
        if not self.remove_small_components:
            return segmentation

        print(f"[POSTPROCESS] Eliminare componente mici...")
        processed = segmentation.copy()

        # Procesează fiecare clasă separat
        for class_id in range(1, NUM_CLASSES):  # Skip background (0)
            if class_id not in processed:
                continue

            # Extrage masca pentru clasa curentă
            class_mask = (processed == class_id)

            if class_mask.sum() == 0:
                continue

            # Găsește componentele conexe
            labeled_array, num_features = label(class_mask)

            if num_features == 0:
                continue

            min_size = MIN_COMPONENT_SIZE.get(class_id, 50)
            components_removed = 0

            # Verifică fiecare componentă
            for component_id in range(1, num_features + 1):
                component_mask = (labeled_array == component_id)
                component_size = component_mask.sum()

                # Elimină componentele mici
                if component_size < min_size:
                    processed[component_mask] = 0  # Set to background
                    components_removed += 1

            remaining_voxels = (processed == class_id).sum()
            print(f"    - Clasa {class_id}: eliminat {components_removed}/{num_features} componente")
            print(f"    - Voxeli rămași: {remaining_voxels}")

        return processed

    def postprocess_segmentation(self,
                                 predictions: torch.Tensor,
                                 original_metadata: Dict[str, Any] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Pipeline complet de postprocesare

        Args:
            predictions: Predicțiile modelului (B, C, H, W, D)
            original_metadata: Metadata din preprocesare (opțional)

        Returns:
            Tuple cu (segmentare_finală, metadata_postprocesare)
        """
        try:
            print(f"[POSTPROCESS] Start pipeline postprocesare...")

            # 1. Convertește în clase discrete
            class_segmentation = self.convert_predictions_to_classes(predictions)

            # Convertește în numpy pentru procesări ulterioare
            if class_segmentation.dim() == 4:  # (B, H, W, D)
                segmentation_np = class_segmentation[0].cpu().numpy()  # Prima din batch
            else:  # (H, W, D)
                segmentation_np = class_segmentation.cpu().numpy()

            print(f"[POSTPROCESS] Segmentare numpy shape: {segmentation_np.shape}")

            # 2. Operații morfologice
            segmentation_np = self.apply_morphological_operations(segmentation_np)

            # 3. Eliminare componente mici
            segmentation_np = self.remove_small_connected_components(segmentation_np)

            # 4. Statistici finale
            unique_classes, counts = np.unique(segmentation_np, return_counts=True)
            class_stats = {int(cls): int(count) for cls, count in zip(unique_classes, counts)}

            print(f"[POSTPROCESS] Statistici finale:")
            for cls, count in class_stats.items():
                if cls > 0:  # Skip background
                    print(f"    - Clasa {cls}: {count} voxeli")

            # Metadata pentru rezultat
            postprocess_metadata = {
                "postprocess_config": {
                    "confidence_threshold": self.confidence_threshold,
                    "morphological_ops": self.apply_morphological,
                    "remove_small_components": self.remove_small_components,
                    "fill_holes": self.fill_holes
                },
                "final_shape": segmentation_np.shape,
                "classes_found": list(unique_classes),
                "class_statistics": class_stats,
                "total_segmented_voxels": int(np.sum([count for cls, count in class_stats.items() if cls > 0]))
            }

            if original_metadata:
                postprocess_metadata["original_metadata"] = original_metadata

            print(f"[POSTPROCESS] Pipeline complet cu succes!")
            return segmentation_np, postprocess_metadata

        except Exception as e:
            logger.error(f"Eroare în postprocesare: {str(e)}")
            raise RuntimeError(f"Postprocesarea a eșuat: {str(e)}")

    def save_segmentation_as_nifti(self,
                                   segmentation: np.ndarray,
                                   output_path: Path,
                                   reference_nifti: Optional[Path] = None,
                                   metadata: Dict[str, Any] = None) -> Path:
        """
        Salvează segmentarea ca fișier NIfTI

        Args:
            segmentation: Array 3D cu segmentarea
            output_path: Calea unde să salveze fișierul
            reference_nifti: Fișier NIfTI de referință pentru header (opțional)
            metadata: Metadata pentru salvare (opțional)

        Returns:
            Calea către fișierul salvat
        """
        try:
            print(f"[POSTPROCESS] Salvare NIfTI la: {output_path}")

            # Creează directorul dacă nu există
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Folosește fișierul de referință pentru header dacă este disponibil
            if reference_nifti and reference_nifti.exists():
                print(f"[POSTPROCESS] Folosește fișier referință: {reference_nifti}")
                ref_img = nib.load(reference_nifti)

                # Creează imaginea nouă cu header-ul de referință
                new_img = nib.Nifti1Image(
                    segmentation.astype(np.uint8),
                    ref_img.affine,
                    ref_img.header
                )
            else:
                print(f"[POSTPROCESS] Creează header implicit")
                # Creează header implicit
                new_img = nib.Nifti1Image(segmentation.astype(np.uint8), np.eye(4))

            # Salvează fișierul
            nib.save(new_img, str(output_path))

            # Verifică că s-a salvat
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                print(f"[POSTPROCESS] Fișier salvat cu succes: {file_size:.2f} MB")
                return output_path
            else:
                raise RuntimeError("Fișierul nu a fost salvat corect")

        except Exception as e:
            logger.error(f"Eroare la salvarea NIfTI: {str(e)}")
            raise RuntimeError(f"Salvarea NIfTI a eșuat: {str(e)}")


# Funcții utilitare

def create_postprocessor(confidence_threshold: float = 0.5) -> SegmentationPostprocessor:
    """
    Creează o instanță de postprocessor cu configurările standard

    Args:
        confidence_threshold: Threshold pentru confidence (0.0-1.0)

    Returns:
        Instanță SegmentationPostprocessor
    """
    return SegmentationPostprocessor(
        confidence_threshold=confidence_threshold,
        apply_morphological=True,
        remove_small_components=True,
        fill_holes=True
    )


# Instanță globală
_postprocessor = None


def get_postprocessor() -> SegmentationPostprocessor:
    """
    Returnează instanța globală a postprocessor-ului (singleton)

    Returns:
        Instanță SegmentationPostprocessor
    """
    global _postprocessor
    if _postprocessor is None:
        _postprocessor = create_postprocessor()
    return _postprocessor


def quick_postprocess(predictions: torch.Tensor,
                      output_filename: str = "segmentation_result.nii.gz",
                      reference_nifti: Optional[Path] = None) -> Path:
    """
    Funcție rapidă pentru postprocesare completă

    Args:
        predictions: Predicțiile modelului
        output_filename: Numele fișierului de output
        reference_nifti: Fișier NIfTI de referință (opțional)

    Returns:
        Calea către fișierul rezultat
    """
    postprocessor = get_postprocessor()

    # Postprocesare
    segmentation, metadata = postprocessor.postprocess_segmentation(predictions)

    # Salvare
    output_path = TEMP_RESULTS_DIR / output_filename
    result_path = postprocessor.save_segmentation_as_nifti(
        segmentation,
        output_path,
        reference_nifti,
        metadata
    )

    return result_path