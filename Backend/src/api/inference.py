# -*- coding: utf-8 -*-
"""
API Endpoints pentru serviciul de inferență
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from src.core.config import UPLOAD_DIR, TEMP_PREPROCESSING_DIR, get_file_size_mb

# Import servicii inferență
try:
    from src.services import (
        get_inference_service,
        run_inference_on_folder,
        run_inference_on_preprocessed,
        get_postprocessor
    )

    INFERENCE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Inference dependencies nu sunt disponibile: {e}")
    INFERENCE_AVAILABLE = False

router = APIRouter(prefix="/inference", tags=["Inference"])


@router.get("/status")
async def get_inference_status():
    """
    Verifică statusul sistemului de inferență
    """
    if not INFERENCE_AVAILABLE:
        return {
            "inference_available": False,
            "error": "Dependențele pentru inferență nu sunt instalate",
            "required_services": ["preprocess", "ml", "postprocess"]
        }

    try:
        service = get_inference_service()

        # Verifică toate componentele
        preprocessor_info = service.preprocessor.get_preprocessing_info()
        model_info = service.model_wrapper.get_model_info()
        memory_info = service.model_wrapper.get_memory_usage()

        return {
            "inference_available": True,
            "components": {
                "preprocessor": {
                    "initialized": preprocessor_info["is_initialized"],
                    "monai_available": preprocessor_info["monai_available"]
                },
                "model": {
                    "loaded": model_info["is_loaded"],
                    "device": model_info["device"],
                    "parameters": model_info.get("total_parameters", 0)
                },
                "postprocessor": {
                    "initialized": True
                }
            },
            "memory_usage": memory_info,
            "status": "ready" if model_info["is_loaded"] else "model_not_loaded"
        }

    except Exception as e:
        return {
            "inference_available": True,
            "error": str(e),
            "status": "error"
        }


@router.post("/folder/{folder_name}")
async def run_inference_on_folder_endpoint(
        folder_name: str,
        save_result: bool = True,
        output_filename: str = None
):
    """
    Rulează inferența completă pe un folder cu modalități
    Pipeline: preprocess -> inference -> postprocess -> save
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferență nu este disponibil"
        )

    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul {folder_name} nu există"
            )

        print(f"[INFERENCE API] Start pipeline pentru folder: {folder_name}")

        # Rulează pipeline-ul complet
        result = run_inference_on_folder(folder_path, save_result)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferența a eșuat: {result.get('error', 'Eroare necunoscută')}"
            )

        # Pregătește răspunsul (fără array-ul mare)
        response_data = {
            "message": f"Inferență completă pentru {folder_name}",
            "folder_name": result["folder_name"],
            "timing": result["timing"],
            "segmentation_info": {
                "shape": list(result["segmentation"]["shape"]),
                "classes_found": result["segmentation"]["classes_found"],
                "class_counts": result["segmentation"]["class_counts"],
                "total_segmented_voxels": result["segmentation"]["total_segmented_voxels"]
            },
            "saved_file": result["saved_path"],
            "preprocessing_config": result["preprocessing_config"]
        }

        # Redenumește fișierul dacă este specificat
        if save_result and result["saved_path"] and output_filename:
            try:
                old_path = Path(result["saved_path"])
                new_path = old_path.parent / output_filename
                old_path.rename(new_path)
                response_data["saved_file"] = str(new_path)
                print(f"[INFERENCE API] Fișier redenumit: {output_filename}")
            except Exception as e:
                print(f"[WARNING] Nu s-a putut redenumi fișierul: {e}")

        print(f"[INFERENCE API] Inferență completă în {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare neașteptată: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare internă la inferență: {str(e)}"
        )


@router.post("/preprocessed/{filename}")
async def run_inference_on_preprocessed_endpoint(filename: str):
    """
    Rulează inferența pe date preprocesate salvate
    Pipeline: load -> inference -> postprocess
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferență nu este disponibil"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fișierul preprocesат {filename} nu există"
            )

        print(f"[INFERENCE API] Încarcă și procesează: {filename}")

        # Încarcă tensorul preprocesат
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            preprocessed_tensor = data['image_tensor']
            folder_name = data.get('metadata', {}).get('folder_name', filename.replace('.pt', ''))
        else:
            preprocessed_tensor = data
            folder_name = filename.replace('.pt', '')

        # Verifică shape-ul
        expected_shape = (4, 128, 128, 128)  # (C, H, W, D)
        if preprocessed_tensor.shape != expected_shape:
            raise HTTPException(
                status_code=400,
                detail=f"Shape tensor invalid: {preprocessed_tensor.shape}. Se așteaptă: {expected_shape}"
            )

        # Rulează inferența
        result = run_inference_on_preprocessed(preprocessed_tensor, folder_name)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferența a eșuat: {result.get('error', 'Eroare necunoscută')}"
            )

        response_data = {
            "message": f"Inferență completă pe date preprocesate",
            "source_file": filename,
            "folder_name": result["folder_name"],
            "timing": result["timing"],
            "segmentation_info": {
                "shape": list(result["segmentation"]["shape"]),
                "classes_found": result["segmentation"]["classes_found"],
                "class_counts": result["segmentation"]["class_counts"]
            }
        }

        print(f"[INFERENCE API] Inferență pe {filename} completă în {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la inferența pe preprocesate: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la inferență: {str(e)}"
        )


@router.get("/results")
async def get_inference_results():
    """
    Listează rezultatele de inferență salvate
    """
    try:
        results_dir = Path("results")

        if not results_dir.exists():
            return {
                "inference_results": [],
                "count": 0,
                "results_dir": str(results_dir)
            }

        results = []
        # Caută fișiere cu pattern *-seg.nii.gz
        for result_path in results_dir.glob("*-seg.nii.gz"):
            stat = result_path.stat()

            # Extrage numele folderului din nume fișier (elimină -seg.nii.gz)
            folder_name = result_path.name.replace('-seg.nii.gz', '')

            results.append({
                "filename": result_path.name,
                "folder_name": folder_name,
                "full_path": str(result_path),
                "size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            })

        # Sortează după data creării
        results.sort(key=lambda x: x["created"], reverse=True)

        return {
            "inference_results": results,
            "count": len(results),
            "results_dir": str(results_dir)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la listarea rezultatelor: {str(e)}"
        )


@router.get("/results/{folder_name}/download")
async def download_inference_result(folder_name: str):
    """
    Descarcă rezultatul de inferință pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu există"
            )

        print(f"[INFERENCE API] Descărcare rezultat: {folder_name}")

        return FileResponse(
            path=str(result_path),
            media_type="application/gzip",
            filename=f"{folder_name}-seg.nii.gz",
            headers={"Content-Disposition": f"attachment; filename={folder_name}-seg.nii.gz"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la descărcarea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descărcare: {str(e)}"
        )


@router.delete("/results/{folder_name}")
async def delete_inference_result(folder_name: str):
    """
    Șterge rezultatul de inferință pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu există"
            )

        file_size = result_path.stat().st_size
        result_path.unlink()

        print(f"[INFERENCE API] Rezultat șters: {folder_name}")

        return {
            "message": f"Rezultatul pentru {folder_name} a fost șters",
            "deleted_file": result_path.name,
            "size_freed_mb": get_file_size_mb(file_size)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la ștergerea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la ștergere: {str(e)}"
        )


@router.get("/results/{folder_name}/info")
async def get_inference_result_info(folder_name: str):
    """
    Obține informații despre un rezultat de inferință
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu există"
            )

        # Informații de bază despre fișier
        stat = result_path.stat()
        file_info = {
            "filename": result_path.name,
            "folder_name": folder_name,
            "full_path": str(result_path),
            "size_mb": get_file_size_mb(stat.st_size),
            "created": stat.st_ctime,
            "modified": stat.st_mtime
        }

        # Încearcă să citească informații din fișierul NIfTI
        try:
            import nibabel as nib
            import numpy as np

            nii_img = nib.load(str(result_path))
            data = nii_img.get_fdata()

            # Statistici segmentare
            unique_classes, counts = np.unique(data, return_counts=True)
            class_stats = {int(cls): int(count) for cls, count in zip(unique_classes, counts)}

            nifti_info = {
                "shape": list(data.shape),
                "classes_found": [int(cls) for cls in unique_classes],
                "class_counts": class_stats,
                "total_segmented_voxels": int(sum(count for cls, count in class_stats.items() if cls > 0)),
                "voxel_size": list(nii_img.header.get_zooms()[:3])
            }

            file_info["nifti_info"] = nifti_info

        except Exception as e:
            print(f"[WARNING] Nu s-au putut citi informații NIfTI: {e}")
            file_info["nifti_error"] = str(e)

        return file_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la obținerea informațiilor: {str(e)}"
        )