# -*- coding: utf-8 -*-
"""
Serviciu de inferenta pentru segmentarea gliomelor post-tratament
Pipeline complet: preprocess -> inference -> postprocess
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import time

from .preprocess import get_preprocessor
from .postprocess import get_postprocessor

try:
    from src.ml import get_model_wrapper, ensure_model_loaded

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class GliomaInferenceService:
    """Serviciu complet de inferenta pentru gliome"""

    def __init__(self):
        if not ML_AVAILABLE:
            raise ImportError("Sistemul ML nu este disponibil")

        self.preprocessor = get_preprocessor()
        self.postprocessor = get_postprocessor()
        self.model_wrapper = get_model_wrapper()

    def run_inference_pipeline(self, folder_path: Path,
                               save_result: bool = True,
                               output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Pipeline complet de inferenta

        Args:
            folder_path: Folder cu modalitatile (t1n, t1c, t2w, t2f)
            save_result: Daca sa salveze rezultatul ca NIfTI
            output_dir: Directorul pentru salvare (optional)

        Returns:
            Dict cu rezultatele complete
        """
        print(f"Start pipeline inferenta pentru: {folder_path.name}")
        start_time = time.time()

        try:
            # 1. PREPROCESS
            print("Etapa 1: Preprocesare...")
            preprocess_start = time.time()
            preprocessed_data = self.preprocessor.preprocess_folder(folder_path)
            preprocess_time = time.time() - preprocess_start

            image_tensor = preprocessed_data["image_tensor"]
            print(f"Preprocesare completa: {preprocess_time:.2f}s")
            print(f"   Shape: {list(image_tensor.shape)}")

            # 2. INFERENCE
            print("Etapa 2: Inferenta model...")

            # Asigura ca modelul e incarcat
            if not self.model_wrapper.is_loaded:
                print("   incarca model...")
                ensure_model_loaded()

            inference_start = time.time()

            # Adauga dimensiunea batch daca lipseste
            if image_tensor.dim() == 4:  # (C, H, W, D)
                image_tensor = image_tensor.unsqueeze(0)  # (1, C, H, W, D)

            # Ruleaza inferenta
            with torch.no_grad():
                predictions = self.model_wrapper.predict(image_tensor)

            inference_time = time.time() - inference_start
            print(f"Inferenta completa: {inference_time:.2f}s")
            print(f"   Output shape: {list(predictions.shape)}")

            # 3. POSTPROCESS
            print("Etapa 3: Postprocesare...")
            postprocess_start = time.time()

            # Elimina dimensiunea batch pentru postprocesare
            if predictions.dim() == 5:  # (1, C, H, W, D)
                predictions = predictions.squeeze(0)  # (C, H, W, D)

            segmentation, postprocess_stats = self.postprocessor.postprocess_segmentation(predictions)
            postprocess_time = time.time() - postprocess_start

            print(f"Postprocesare completa: {postprocess_time:.2f}s")

            # 4. SALVARE (optional)
            saved_path = None
            if save_result:
                print("Etapa 4: Salvare rezultat...")

                if output_dir is None:
                    output_dir = Path("results")

                # Foloseste primul fisier gasit ca referinta pentru header
                reference_nifti = None
                original_paths = preprocessed_data.get("original_paths", {})
                if original_paths:
                    reference_nifti = list(original_paths.values())[0]

                # MODIFIED: Salveaza folosind noua metoda cu folder
                saved_path = self.postprocessor.save_as_nifti(
                    segmentation, folder_path.name, output_dir, reference_nifti
                )
                print(f"Rezultat salvat: {saved_path}")

            # Timing total
            total_time = time.time() - start_time

            # Rezultat complet - FIXED: asigura tipuri Python native pentru JSON
            result = {
                "success": True,
                "folder_name": folder_path.name,
                "timing": {
                    "preprocess_time": float(preprocess_time),
                    "inference_time": float(inference_time),
                    "postprocess_time": float(postprocess_time),
                    "total_time": float(total_time)
                },
                "segmentation": {
                    "shape": [int(dim) for dim in segmentation.shape],
                    "classes_found": postprocess_stats["classes_found"],
                    "class_counts": postprocess_stats["class_counts"],
                    "total_segmented_voxels": postprocess_stats["total_segmented_voxels"]
                },
                "preprocessing_config": preprocessed_data["preprocessing_config"],
                "saved_path": str(saved_path) if saved_path else None,
                "segmentation_array": segmentation  # Pentru utilizare ulterioara
            }

            print(f"Pipeline complet in {total_time:.2f}s")
            print(
                f"   Preprocess: {preprocess_time:.1f}s | Inference: {inference_time:.1f}s | Postprocess: {postprocess_time:.1f}s")

            return result

        except Exception as e:
            error_time = time.time() - start_time
            print(f"Eroare in pipeline dupa {error_time:.2f}s: {str(e)}")

            return {
                "success": False,
                "folder_name": folder_path.name,
                "error": str(e),
                "error_time": error_time
            }

    def run_inference_from_preprocessed(self, preprocessed_tensor: torch.Tensor,
                                        folder_name: str = "unknown") -> Dict[str, Any]:
        """
        Ruleaza doar inferenta + postprocesare pe date deja preprocesate

        Args:
            preprocessed_tensor: Tensor deja preprocesат (C, H, W, D)
            folder_name: Numele pentru identificare

        Returns:
            Dict cu rezultatele
        """
        print(f"Inferenta directa pentru: {folder_name}")
        start_time = time.time()

        try:
            # Asigura ca modelul e incarcat
            if not self.model_wrapper.is_loaded:
                ensure_model_loaded()

            # Adauga batch dimension
            if preprocessed_tensor.dim() == 4:
                preprocessed_tensor = preprocessed_tensor.unsqueeze(0)

            # Inferenta
            with torch.no_grad():
                predictions = self.model_wrapper.predict(preprocessed_tensor)

            # Postprocesare
            if predictions.dim() == 5:
                predictions = predictions.squeeze(0)

            segmentation, stats = self.postprocessor.postprocess_segmentation(predictions)

            total_time = time.time() - start_time

            return {
                "success": True,
                "folder_name": folder_name,
                "timing": {"total_time": float(total_time)},
                "segmentation": {
                    "shape": [int(dim) for dim in segmentation.shape],
                    "classes_found": stats["classes_found"],
                    "class_counts": stats["class_counts"]
                },
                "segmentation_array": segmentation
            }

        except Exception as e:
            return {
                "success": False,
                "folder_name": folder_name,
                "error": str(e)
            }


# Functii utilitare
def create_inference_service() -> GliomaInferenceService:
    """Creeaza serviciu de inferenta"""
    return GliomaInferenceService()


def run_inference_on_folder(folder_path: Path, save_result: bool = True) -> Dict[str, Any]:
    """
    Functie rapida pentru inferenta completa pe un folder

    Args:
        folder_path: Folder cu modalitatile
        save_result: Daca sa salveze rezultatul

    Returns:
        Dict cu rezultatele
    """
    service = create_inference_service()
    return service.run_inference_pipeline(folder_path, save_result)


def run_inference_on_preprocessed(preprocessed_tensor: torch.Tensor,
                                  folder_name: str = "unknown") -> Dict[str, Any]:
    """
    Functie rapida pentru inferenta pe date preprocesate

    Args:
        preprocessed_tensor: Tensor preprocesат
        folder_name: Nume pentru identificare

    Returns:
        Dict cu rezultatele
    """
    service = create_inference_service()
    return service.run_inference_from_preprocessed(preprocessed_tensor, folder_name)


# Instanta globala
_inference_service = None


def get_inference_service() -> GliomaInferenceService:
    """Returneaza instanta globala a serviciului de inferenta"""
    global _inference_service
    if _inference_service is None:
        _inference_service = create_inference_service()
    return _inference_service