# -*- coding: utf-8 -*-
"""
API Endpoints pentru serviciul de inferenta - cu suport cache și overlay FIXED
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

from src.core.config import UPLOAD_DIR, TEMP_PREPROCESSING_DIR, get_file_size_mb

# Import servicii inferenta
try:
    from src.services import (
        get_inference_service,
        run_inference_on_folder,
        run_inference_on_preprocessed,
        get_postprocessor,
        check_existing_result
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


@router.get("/cache-check/{folder_name}")
async def check_cache_status(folder_name: str):
    """
    Verifica daca exista rezultate in cache pentru un folder (segmentation + overlay)
    """
    try:
        existing_results = check_existing_result(folder_name)

        has_segmentation = existing_results.get("segmentation") is not None
        has_overlay = existing_results.get("overlay") is not None

        result = {
            "has_cache": has_segmentation or has_overlay,
            "has_segmentation": has_segmentation,
            "has_overlay": has_overlay,
        }

        if has_segmentation:
            seg_path = existing_results["segmentation"]
            stat = seg_path.stat()
            result["segmentation_info"] = {
                "file_path": str(seg_path),
                "file_size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            }

        if has_overlay:
            overlay_path = existing_results["overlay"]
            stat = overlay_path.stat()
            result["overlay_info"] = {
                "file_path": str(overlay_path),
                "file_size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            }

        if not (has_segmentation or has_overlay):
            result["message"] = f"Nu exista rezultate in cache pentru {folder_name}"

        return result

    except Exception as e:
        return {
            "has_cache": False,
            "error": str(e)
        }


@router.post("/folder/{folder_name}")
async def run_inference_on_folder_endpoint(
        folder_name: str,
        save_result: bool = True,
        output_filename: str = None,
        create_overlay: bool = Query(True, description="Creează și overlay-ul T1N + segmentare"),
        force_reprocess: bool = Query(False, description="Forțează re-procesarea chiar dacă există cache"),
        overlay_alpha: float = Query(0.5, description="Transparența overlay-ului (0.0-1.0)", ge=0.0, le=1.0)
):
    """
    FIXED: Ruleaza inferenta completa pe un folder cu modalitati + creează overlay
    Pipeline: cache-check -> preprocess -> inference -> postprocess -> overlay -> save
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
        print(f"[INFERENCE API] Create overlay: {create_overlay}")
        print(f"[INFERENCE API] Overlay alpha: {overlay_alpha}")
        if force_reprocess:
            print(f"[INFERENCE API] Re-procesare forțată activată")

        # Ruleaza pipeline-ul complet cu verificare cache și overlay
        result = run_inference_on_folder(folder_path, save_result, force_reprocess, create_overlay)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferenta a esuat: {result.get('error', 'Eroare necunoscuta')}"
            )

        # Pregateste raspunsul
        response_data = {
            "message": result.get("message", f"Inferenta completa pentru {folder_name}"),
            "folder_name": result["folder_name"],
            "cached": result.get("cached", False),
            "timing": result["timing"],
            "saved_file": result["saved_path"],
            "overlay_file": result.get("overlay_path"),  # Noul câmp
            "has_overlay": result.get("overlay_path") is not None
        }

        # Adauga informatii despre segmentare
        if "segmentation" in result and result["segmentation"]:
            response_data["segmentation_info"] = {
                "shape": result["segmentation"].get("shape", []),
                "classes_found": result["segmentation"].get("classes_found", []),
                "class_counts": result["segmentation"].get("class_counts", {}),
                "total_segmented_voxels": result["segmentation"].get("total_segmented_voxels", 0)
            }

        # Adauga config doar daca nu e din cache
        if not result.get("cached", False) and "preprocessing_config" in result:
            response_data["preprocessing_config"] = result["preprocessing_config"]

        # Adauga informatii despre cache daca exista
        if result.get("cached", False) and "cache_info" in result:
            response_data["cache_info"] = result["cache_info"]

        # Redenumire fisier daca e specificat
        if save_result and result["saved_path"] and output_filename and not result.get("cached", False):
            try:
                old_path = Path(result["saved_path"])
                new_path = old_path.parent / output_filename
                old_path.rename(new_path)
                response_data["saved_file"] = str(new_path)
                print(f"[INFERENCE API] Fisier redenumit: {output_filename}")
            except Exception as e:
                print(f"[WARNING] Nu s-a putut redenumi fisierul: {e}")

        # Mesaj final
        if result.get("cached", False):
            print(f"[INFERENCE API] Folosit cache pentru {folder_name}")
        else:
            print(f"[INFERENCE API] Inferenta completa in {result['timing']['total_time']:.2f}s")
            if create_overlay and result.get("overlay_path"):
                print(f"[INFERENCE API] Overlay creat in {result['timing'].get('overlay_time', 0):.2f}s")

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
            "cached": result.get("cached", False),
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
    Listeaza rezultatele de inferenta salvate (segmentation + overlay)
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

        # Cauta foldere cu fisiere de rezultate
        for folder_path in results_dir.iterdir():
            if folder_path.is_dir():
                # Cauta fisierele seg și overlay în folder
                seg_files = list(folder_path.glob("*-seg.nii.gz"))
                overlay_files = list(folder_path.glob("*-overlay.nii.gz"))

                if seg_files or overlay_files:
                    folder_result = {
                        "folder_name": folder_path.name,
                        "result_folder": str(folder_path),
                        "has_segmentation": len(seg_files) > 0,
                        "has_overlay": len(overlay_files) > 0,
                        "files": {}
                    }

                    # Informatii despre segmentation
                    if seg_files:
                        seg_file = seg_files[0]
                        stat = seg_file.stat()
                        folder_result["files"]["segmentation"] = {
                            "filename": seg_file.name,
                            "full_path": str(seg_file),
                            "size_mb": get_file_size_mb(stat.st_size),
                            "created": stat.st_ctime,
                            "modified": stat.st_mtime
                        }

                    # Informatii despre overlay
                    if overlay_files:
                        overlay_file = overlay_files[0]
                        stat = overlay_file.stat()
                        folder_result["files"]["overlay"] = {
                            "filename": overlay_file.name,
                            "full_path": str(overlay_file),
                            "size_mb": get_file_size_mb(stat.st_size),
                            "created": stat.st_ctime,
                            "modified": stat.st_mtime
                        }

                    # Foloseste timestamp-ul celui mai recent fisier pentru sortare
                    latest_time = 0
                    if seg_files:
                        latest_time = max(latest_time, seg_files[0].stat().st_ctime)
                    if overlay_files:
                        latest_time = max(latest_time, overlay_files[0].stat().st_ctime)

                    folder_result["latest_modified"] = latest_time
                    results.append(folder_result)

        # Sorteaza dupa data modificarii (cel mai recent primul)
        results.sort(key=lambda x: x["latest_modified"], reverse=True)

        return {
            "inference_results": results,
            "count": len(results),
            "results_dir": str(results_dir),
            "cache_enabled": True
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la listarea rezultatelor: {str(e)}"
        )


@router.get("/results/{folder_name}/download-segmentation")
async def download_segmentation_result(folder_name: str):
    """
    Descarca rezultatul de segmentare pentru un folder
    """
    try:
        result_folder = Path("results") / folder_name

        if not result_folder.exists() or not result_folder.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul cu rezultatul pentru {folder_name} nu exista"
            )

        # Cauta fisierul seg în folder
        seg_files = list(result_folder.glob("*-seg.nii.gz"))

        if not seg_files:
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul de segmentare pentru {folder_name} nu exista"
            )

        result_path = seg_files[0]
        print(f"[INFERENCE API] Descarcare segmentare: {folder_name} -> {result_path}")

        return FileResponse(
            path=str(result_path),
            media_type="application/gzip",
            filename=result_path.name,
            headers={"Content-Disposition": f"attachment; filename={result_path.name}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la descarcarea segmentarii: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descarcare: {str(e)}"
        )


@router.get("/results/{folder_name}/download-overlay")
async def download_overlay_result(folder_name: str):
    """
    FIXED: Descarca rezultatul overlay pentru un folder
    """
    try:
        result_folder = Path("results") / folder_name

        if not result_folder.exists() or not result_folder.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul cu rezultatul pentru {folder_name} nu exista"
            )

        # Cauta fisierul overlay în folder
        overlay_files = list(result_folder.glob("*-overlay.nii.gz"))

        if not overlay_files:
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul overlay pentru {folder_name} nu exista"
            )

        result_path = overlay_files[0]
        print(f"[INFERENCE API] Descarcare overlay: {folder_name} -> {result_path}")

        return FileResponse(
            path=str(result_path),
            media_type="application/gzip",
            filename=result_path.name,
            headers={"Content-Disposition": f"attachment; filename={result_path.name}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la descarcarea overlay-ului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descarcare: {str(e)}"
        )


# Backward compatibility - păstrează endpoint-ul vechi
@router.get("/results/{folder_name}/download")
async def download_inference_result(folder_name: str):
    """
    Descarca rezultatul de inferinta pentru un folder (segmentation - backward compatibility)
    """
    return await download_segmentation_result(folder_name)


@router.delete("/results/{folder_name}")
async def delete_inference_result(folder_name: str):
    """
    sterge rezultatele de inferinta pentru un folder (curata cache-ul complet)
    """
    try:
        import shutil

        result_folder = Path("results") / folder_name

        if not result_folder.exists() or not result_folder.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul cu rezultatul pentru {folder_name} nu exista"
            )

        # Calculeaza dimensiunea totala inainte de stergere
        total_size = 0
        file_count = 0
        for file_path in result_folder.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1

        # sterge intregul folder
        shutil.rmtree(result_folder)

        print(f"[INFERENCE API] Cache curatat pentru: {folder_name}")

        return {
            "message": f"Cache pentru {folder_name} a fost curatat",
            "deleted_folder": folder_name,
            "files_deleted": file_count,
            "size_freed_mb": get_file_size_mb(total_size),
            "cache_cleared": True
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la curatarea cache-ului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la stergere: {str(e)}"
        )


@router.delete("/cache/clear-all")
async def clear_all_cache():
    """
    Curata tot cache-ul de inferenta
    """
    try:
        import shutil

        results_dir = Path("results")

        if not results_dir.exists():
            return {
                "message": "Nu exista cache de curatat",
                "cache_cleared": True,
                "folders_deleted": 0,
                "size_freed_mb": 0
            }

        # Calculeaza dimensiunea totala
        total_size = 0
        folder_count = 0

        for folder_path in results_dir.iterdir():
            if folder_path.is_dir():
                folder_count += 1
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size

        # sterge tot directorul results
        shutil.rmtree(results_dir)

        print(f"[INFERENCE API] Tot cache-ul curatat: {folder_count} foldere")

        return {
            "message": f"Tot cache-ul a fost curatat",
            "folders_deleted": folder_count,
            "size_freed_mb": get_file_size_mb(total_size),
            "cache_cleared": True
        }

    except Exception as e:
        print(f"[INFERENCE API] Eroare la curatarea totala: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la curatarea cache-ului: {str(e)}"
        )


@router.get("/results/{folder_name}/info")
async def get_inference_result_info(folder_name: str):
    """
    Obtine informatii despre rezultatele de inferinta (segmentation + overlay)
    """
    try:
        from src.services.inference import get_existing_result_info

        result_folder = Path("results") / folder_name

        if not result_folder.exists() or not result_folder.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul cu rezultatul pentru {folder_name} nu exista"
            )

        # Cauta fisierele
        seg_files = list(result_folder.glob("*-seg.nii.gz"))
        overlay_files = list(result_folder.glob("*-overlay.nii.gz"))

        if not seg_files and not overlay_files:
            raise HTTPException(
                status_code=404,
                detail=f"Nu exista fisiere de rezultate pentru {folder_name}"
            )

        folder_info = {
            "folder_name": folder_name,
            "result_folder": str(result_folder),
            "has_segmentation": len(seg_files) > 0,
            "has_overlay": len(overlay_files) > 0,
            "files": {}
        }

        # Informatii despre segmentation
        if seg_files:
            seg_info = get_existing_result_info(seg_files[0])
            folder_info["files"]["segmentation"] = seg_info

        # Informatii despre overlay
        if overlay_files:
            overlay_info = get_existing_result_info(overlay_files[0])
            folder_info["files"]["overlay"] = overlay_info

        return folder_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la obtinerea informatiilor: {str(e)}"
        )