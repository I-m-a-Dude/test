# -*- coding: utf-8 -*-
"""
Serviciu de inferenta pentru segmentarea gliomelor post-tratament
Pipeline complet: preprocess -> inference -> postprocess -> overlay (cu cache)
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import time
import nibabel as nib

from .preprocess import get_preprocessor
from .postprocess import get_postprocessor

try:
    from src.ml import get_model_wrapper, ensure_model_loaded

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


def check_existing_result(folder_name: str, output_dir: Path = None) -> Dict[str, Optional[Path]]:
    """
    Verifica daca exista deja rezultate de inferenta pentru folderul specificat

    Returns:
        Dict cu paths pentru 'segmentation' și 'overlay' sau None daca nu exista
    """
    if output_dir is None:
        output_dir = Path("results")

    result_folder = output_dir / folder_name
    results = {"segmentation": None, "overlay": None}

    if not result_folder.exists():
        return results

    # Cauta fisierul seg
    seg_files = list(result_folder.glob("*-seg.nii.gz"))
    if seg_files:
        results["segmentation"] = seg_files[0]
        print(f"[CACHE] Gasit segmentation existent: {seg_files[0]}")

    # Cauta fisierul overlay
    overlay_files = list(result_folder.glob("*-overlay.nii.gz"))
    if overlay_files:
        results["overlay"] = overlay_files[0]
        print(f"[CACHE] Gasit overlay existent: {overlay_files[0]}")

    return results


def get_existing_result_info(existing_path: Path) -> Dict[str, Any]:
    """
    Extrage informatii din rezultatul existent
    """
    try:
        # Informatii de baza despre fisier
        stat = existing_path.stat()
        folder_name = existing_path.parent.name

        result_info = {
            "folder_name": folder_name,
            "saved_path": str(existing_path),
            "file_size_mb": stat.st_size / (1024 * 1024),
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime
        }

        # incearca sa citeasca informatii din fisierul NIfTI
        try:
            nii_img = nib.load(str(existing_path))
            data = nii_img.get_fdata()

            # Pentru overlay (4D RGB) vs segmentation (3D)
            if data.ndim == 4:  # Overlay RGB
                nifti_info = {
                    "type": "overlay",
                    "shape": [int(dim) for dim in data.shape],
                    "channels": data.shape[-1] if data.ndim == 4 else 1
                }
            else:  # Segmentation standard
                unique_classes, counts = np.unique(data, return_counts=True)
                class_stats = {int(cls): int(count) for cls, count in zip(unique_classes, counts)}

                nifti_info = {
                    "type": "segmentation",
                    "shape": [int(dim) for dim in data.shape],
                    "classes_found": [int(cls) for cls in unique_classes],
                    "class_counts": class_stats,
                    "total_segmented_voxels": int(sum(count for cls, count in class_stats.items() if cls > 0))
                }

            result_info["nifti_info"] = nifti_info

        except Exception as e:
            print(f"[WARNING] Nu s-au putut citi informatii NIfTI din cache: {e}")
            result_info["nifti_error"] = str(e)

        return result_info

    except Exception as e:
        print(f"[ERROR] Eroare la citirea informatiilor din cache: {e}")
        return {"error": str(e)}


class GliomaInferenceService:
    """Serviciu complet de inferenta pentru gliome cu suport cache și overlay"""

    def __init__(self):
        if not ML_AVAILABLE:
            raise ImportError("Sistemul ML nu este disponibil")

        self.preprocessor = get_preprocessor()
        self.postprocessor = get_postprocessor()
        self.model_wrapper = get_model_wrapper()

    def run_inference_pipeline(self, folder_path: Path,
                               save_result: bool = True,
                               output_dir: Optional[Path] = None,
                               force_reprocess: bool = False,
                               create_overlay: bool = True) -> Dict[str, Any]:
        """
        Pipeline complet de inferenta cu suport cache și overlay

        Args:
            folder_path: Folder cu modalitatile
            save_result: Daca sa salveze rezultatul
            output_dir: Directorul pentru salvare
            force_reprocess: Daca sa forțeze re-procesarea
            create_overlay: Daca sa creeze și overlay-ul
        """
        folder_name = folder_path.name
        print(f"Start pipeline inferenta pentru: {folder_name}")

        # CACHE CHECK: Verifica daca exista deja rezultatele
        if not force_reprocess:
            existing_results = check_existing_result(folder_name, output_dir)

            if existing_results["segmentation"] and (not create_overlay or existing_results["overlay"]):
                print(f"[CACHE HIT] Folosesc rezultatele existente")

                # Extrage informatii din rezultatul principal (segmentation)
                cached_info = get_existing_result_info(existing_results["segmentation"])

                return {
                    "success": True,
                    "cached": True,
                    "folder_name": folder_name,
                    "message": "Folosit rezultat din cache",
                    "timing": {
                        "preprocess_time": 0.1,
                        "inference_time": 0.1,
                        "postprocess_time": 0.1,
                        "overlay_time": 0.1,
                        "total_time": 0.1
                    },
                    "segmentation": cached_info.get("nifti_info", {}),
                    "preprocessing_config": {},
                    "saved_path": str(existing_results["segmentation"]),
                    "overlay_path": str(existing_results["overlay"]) if existing_results["overlay"] else None,
                    "cache_info": {
                        "file_size_mb": cached_info.get("file_size_mb", 0),
                        "created_time": cached_info.get("created_time", 0),
                        "modified_time": cached_info.get("modified_time", 0)
                    }
                }

        # PROCESARE NORMALA daca nu e in cache
        print(f"[PROCESSING] Nu exista cache sau re-procesare forțată")
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

            # 4. OVERLAY CREATION
            overlay_time = 0
            overlay_path = None

            if create_overlay:
                print("Etapa 4: Creez overlay...")
                overlay_start = time.time()

                # Extrage T1N din datele preprocesate (primul canal)
                original_tensor = preprocessed_data["image_tensor"]
                if original_tensor.dim() == 4:  # (C, H, W, D)
                    t1n_data = original_tensor[0].cpu().numpy()  # Primul canal = T1N
                else:
                    print("[WARNING] Shape tensor nepotrivit pentru overlay")
                    t1n_data = None

                if t1n_data is not None:
                    # Creează overlay-ul
                    overlay_image = self.postprocessor.create_overlay(t1n_data, segmentation)
                    overlay_time = time.time() - overlay_start
                    print(f"Overlay creat: {overlay_time:.2f}s")
                else:
                    print("[WARNING] Nu s-a putut crea overlay-ul")

            # 5. SALVARE (optional)
            saved_path = None
            if save_result:
                print("Etapa 5: Salvare rezultate...")

                if output_dir is None:
                    output_dir = Path("results")

                # Foloseste primul fisier gasit ca referinta pentru header
                reference_nifti = None
                original_paths = preprocessed_data.get("original_paths", {})
                if original_paths:
                    reference_nifti = list(original_paths.values())[0]

                # Salveaza segmentarea
                saved_path = self.postprocessor.save_as_nifti(
                    segmentation, folder_path.name, output_dir, reference_nifti
                )
                print(f"Segmentare salvată: {saved_path}")

                # Salveaza overlay-ul (daca e creat)
                if create_overlay and 'overlay_image' in locals():
                    overlay_path = self.postprocessor.save_overlay_as_nifti(
                        overlay_image, folder_path.name, output_dir, reference_nifti
                    )
                    print(f"Overlay salvat: {overlay_path}")

            # Timing total
            total_time = time.time() - start_time

            # Rezultat complet
            result = {
                "success": True,
                "cached": False,
                "folder_name": folder_path.name,
                "timing": {
                    "preprocess_time": float(preprocess_time),
                    "inference_time": float(inference_time),
                    "postprocess_time": float(postprocess_time),
                    "overlay_time": float(overlay_time),
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
                "overlay_path": str(overlay_path) if overlay_path else None,
                "segmentation_array": segmentation,  # Pentru utilizare ulterioara
                "overlay_array": overlay_image if 'overlay_image' in locals() else None
            }

            print(f"Pipeline complet in {total_time:.2f}s")
            print(
                f"   Preprocess: {preprocess_time:.1f}s | Inference: {inference_time:.1f}s | Postprocess: {postprocess_time:.1f}s | Overlay: {overlay_time:.1f}s")

            return result

        except Exception as e:
            error_time = time.time() - start_time
            print(f"Eroare in pipeline dupa {error_time:.2f}s: {str(e)}")

            return {
                "success": False,
                "cached": False,
                "folder_name": folder_path.name,
                "error": str(e),
                "error_time": error_time
            }

    def run_inference_from_preprocessed(self, preprocessed_tensor: torch.Tensor,
                                        folder_name: str = "unknown") -> Dict[str, Any]:
        """
        Ruleaza doar inferenta + postprocesare pe date deja preprocesate
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
                "cached": False,
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
                "cached": False,
                "folder_name": folder_name,
                "error": str(e)
            }


# Functii utilitare
def create_inference_service() -> GliomaInferenceService:
    """Creeaza serviciu de inferenta"""
    return GliomaInferenceService()


def run_inference_on_folder(folder_path: Path, save_result: bool = True,
                            force_reprocess: bool = False, create_overlay: bool = True) -> Dict[str, Any]:
    """
    Functie rapida pentru inferenta completa pe un folder cu overlay
    """
    service = create_inference_service()
    return service.run_inference_pipeline(folder_path, save_result,
                                          force_reprocess=force_reprocess,
                                          create_overlay=create_overlay)


def run_inference_on_preprocessed(preprocessed_tensor: torch.Tensor,
                                  folder_name: str = "unknown") -> Dict[str, Any]:
    """
    Functie rapida pentru inferenta pe date preprocesate
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