# -*- coding: utf-8 -*-
"""
API Endpoints pentru serviciul de inferenta
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from src.core.config import UPLOAD_DIR, TEMP_PREPROCESSING_DIR, get_file_size_mb

# Import servicii inferenta
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
    Verifica statusul sistemului de inferenta
    """
    if not INFERENCE_AVAILABLE:
        return {
            "inference_available": False,
            "error": "Dependentele pentru inferenta nu sunt instalate",
            "required_services": ["preprocess", "ml", "postprocess"]
        }

    try:
        service = get_inference_service()

        # Verifica toate componentele
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
    Ruleaza inferenta completa pe un folder cu modalitati
    Pipeline: preprocess -> inference -> postprocess -> save
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferenta nu este disponibil"
        )

    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul {folder_name} nu exista"
            )

        print(f"[INFERENCE API] Start pipeline pentru folder: {folder_name}")

        # Ruleaza pipeline-ul complet
        result = run_inference_on_folder(folder_path, save_result)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferenta a esuat: {result.get('error', 'Eroare necunoscuta')}"
            )

        # Pregateste raspunsul (fara array-ul mare)
        response_data = {
            "message": f"Inferenta completa pentru {folder_name}",
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

        # Redenumeste fisierul daca este specificat
        if save_result and result["saved_path"] and output_filename:
            try:
                old_path = Path(result["saved_path"])
                new_path = old_path.parent / output_filename
                old_path.rename(new_path)
                response_data["saved_file"] = str(new_path)
                print(f"[INFERENCE API] Fisier redenumit: {output_filename}")
            except Exception as e:
                print(f"[WARNING] Nu s-a putut redenumi fisierul: {e}")

        print(f"[INFERENCE API] Inferenta completa in {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare neasteptata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare interna la inferenta: {str(e)}"
        )


@router.post("/preprocessed/{filename}")
async def run_inference_on_preprocessed_endpoint(filename: str):
    """
    Ruleaza inferenta pe date preprocesate salvate
    Pipeline: load -> inference -> postprocess
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferenta nu este disponibil"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul preprocesат {filename} nu exista"
            )

        print(f"[INFERENCE API] incarca si proceseaza: {filename}")

        # incarca tensorul preprocesат
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            preprocessed_tensor = data['image_tensor']
            folder_name = data.get('metadata', {}).get('folder_name', filename.replace('.pt', ''))
        else:
            preprocessed_tensor = data
            folder_name = filename.replace('.pt', '')

        # Verifica shape-ul
        expected_shape = (4, 128, 128, 128)  # (C, H, W, D)
        if preprocessed_tensor.shape != expected_shape:
            raise HTTPException(
                status_code=400,
                detail=f"Shape tensor invalid: {preprocessed_tensor.shape}. Se asteapta: {expected_shape}"
            )

        # Ruleaza inferenta
        result = run_inference_on_preprocessed(preprocessed_tensor, folder_name)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferenta a esuat: {result.get('error', 'Eroare necunoscuta')}"
            )

        response_data = {
            "message": f"Inferenta completa pe date preprocesate",
            "source_file": filename,
            "folder_name": result["folder_name"],
            "timing": result["timing"],
            "segmentation_info": {
                "shape": list(result["segmentation"]["shape"]),
                "classes_found": result["segmentation"]["classes_found"],
                "class_counts": result["segmentation"]["class_counts"]
            }
        }

        print(f"[INFERENCE API] Inferenta pe {filename} completa in {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la inferenta pe preprocesate: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la inferenta: {str(e)}"
        )


@router.get("/results")
async def get_inference_results():
    """
    Listeaza rezultatele de inferenta salvate
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
        # Cauta fisiere cu pattern *-seg.nii.gz
        for result_path in results_dir.glob("*-seg.nii.gz"):
            stat = result_path.stat()

            # Extrage numele folderului din nume fisier (elimina -seg.nii.gz)
            folder_name = result_path.name.replace('-seg.nii.gz', '')

            results.append({
                "filename": result_path.name,
                "folder_name": folder_name,
                "full_path": str(result_path),
                "size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            })

        # Sorteaza dupa data crearii
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
    Descarca rezultatul de inferinta pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu exista"
            )

        print(f"[INFERENCE API] Descarcare rezultat: {folder_name}")

        return FileResponse(
            path=str(result_path),
            media_type="application/gzip",
            filename=f"{folder_name}-seg.nii.gz",
            headers={"Content-Disposition": f"attachment; filename={folder_name}-seg.nii.gz"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la descarcarea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descarcare: {str(e)}"
        )


@router.delete("/results/{folder_name}")
async def delete_inference_result(folder_name: str):
    """
    sterge rezultatul de inferinta pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu exista"
            )

        file_size = result_path.stat().st_size
        result_path.unlink()

        print(f"[INFERENCE API] Rezultat sters: {folder_name}")

        return {
            "message": f"Rezultatul pentru {folder_name} a fost sters",
            "deleted_file": result_path.name,
            "size_freed_mb": get_file_size_mb(file_size)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la stergerea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la stergere: {str(e)}"
        )


@router.get("/results/{folder_name}/info")
async def get_inference_result_info(folder_name: str):
    """
    Obtine informatii despre un rezultat de inferinta
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu exista"
            )

        # Informatii de baza despre fisier
        stat = result_path.stat()
        file_info = {
            "filename": result_path.name,
            "folder_name": folder_name,
            "full_path": str(result_path),
            "size_mb": get_file_size_mb(stat.st_size),
            "created": stat.st_ctime,
            "modified": stat.st_mtime
        }

        # incearca sa citeasca informatii din fisierul NIfTI
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
            print(f"[WARNING] Nu s-au putut citi informatii NIfTI: {e}")
            file_info["nifti_error"] = str(e)

        return file_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la obtinerea informatiilor: {str(e)}"
        )