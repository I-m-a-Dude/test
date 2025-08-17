# -*- coding: utf-8 -*-
"""
Toate endpoint-urile API pentru MediView Backend
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import mimetypes

from src.core.config import APP_NAME, VERSION, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from src.utils.file_utils import validate_file, save_file, list_files, delete_file

# Import ML pentru test endpoint
try:
    from src.ml import get_model_wrapper, ensure_model_loaded

    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] ML dependencies nu sunt disponibile: {e}")
    ML_AVAILABLE = False

# Router principal
router = APIRouter()


@router.get("/")
async def root():
    """Endpoint de bază"""
    return {
        "message": f"{APP_NAME} API",
        "version": VERSION,
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "upload_dir": str(UPLOAD_DIR.absolute()),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "max_file_size": get_file_size_mb(MAX_FILE_SIZE),
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }


@router.post("/upload-mri")
async def upload_mri_file(file: UploadFile = File(...)):
    """
    Upload fișier MRI (inclusiv ZIP-uri cu fișiere NIfTI)
    """
    print(f"[INFO] Încercare upload: {file.filename}")

    try:
        # Validează fișierul
        validate_file(file)

        # Salvează fișierul (și îl dezarhivează dacă e ZIP)
        file_info = await save_file(file)

        if file_info.get("type") == "zip_extracted":
            print(f"[SUCCESS] ZIP dezarhivat: {file.filename}")
            print(f"[INFO] Extras în folderul: {file_info['extraction']['extracted_folder']}")
            print(f"[INFO] Fișiere NIfTI găsite: {file_info['extraction']['nifti_files_count']}")

            return JSONResponse(
                status_code=200,
                content={
                    "message": "ZIP dezarhivat cu succes",
                    "file_info": file_info
                }
            )

        elif file_info.get("type") == "zip_failed":
            print(f"[WARNING] ZIP salvat dar nu a putut fi dezarhivat: {file.filename}")

            return JSONResponse(
                status_code=200,
                content={
                    "message": "ZIP salvat dar dezarhivarea a eșuat",
                    "file_info": file_info
                }
            )

        else:
            print(f"[SUCCESS] Fișier salvat: {file.filename} ({file_info['size_mb']})")

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Fișier încărcat cu succes",
                    "file_info": file_info
                }
            )

    except HTTPException:
        # Re-ridică excepțiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neașteptată: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare internă: {str(e)}")


@router.get("/files")
async def get_uploaded_files():
    """
    Listează fișierele și folderele încărcate
    """
    try:
        items = list_files()

        files_count = len([item for item in items if item["type"] == "file"])
        folders_count = len([item for item in items if item["type"] == "folder"])

        print(f"[INFO] Listare: {files_count} fișiere, {folders_count} foldere")

        return {
            "items": items,
            "total_count": len(items),
            "files_count": files_count,
            "folders_count": folders_count,
            "upload_dir": str(UPLOAD_DIR.absolute())
        }

    except Exception as e:
        print(f"[ERROR] Eroare la listarea fișierelor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la listare: {str(e)}")


@router.delete("/files/{filename}")
async def delete_uploaded_file(filename: str):
    """
    Șterge un fișier sau folder încărcat
    """
    print(f"[INFO] Încercare ștergere: {filename}")

    try:
        result = delete_file(filename)

        if result["type"] == "file":
            print(f"[SUCCESS] Fișier șters: {filename} ({result['size_mb']})")
            message = f"Fișierul {filename} a fost șters cu succes"
        else:
            print(f"[SUCCESS] Folder șters: {filename} ({result['files_deleted']} fișiere, {result['size_mb']})")
            message = f"Folderul {filename} a fost șters cu succes"

        return {
            "message": message,
            "deleted_item": result
        }

    except HTTPException:
        # Re-ridică excepțiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neașteptată la ștergere: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare internă: {str(e)}")


@router.get("/files/{filename}/info")
async def get_file_info(filename: str):
    """
    Obține informații despre un fișier specific
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

    try:
        stat = file_path.stat()

        return {
            "filename": filename,
            "size": stat.st_size,
            "size_mb": get_file_size_mb(stat.st_size),
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "path": str(file_path.absolute()),
            "extension": file_path.suffix
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare la citirea informațiilor: {str(e)}")


@router.get("/ml/status")
async def get_ml_status():
    """
    Verifică statusul sistemului ML
    """
    if not ML_AVAILABLE:
        return {
            "ml_available": False,
            "error": "Dependențele ML nu sunt instalate",
            "required_packages": ["torch", "monai", "nibabel"]
        }

    try:
        wrapper = get_model_wrapper()
        model_info = wrapper.get_model_info()

        return {
            "ml_available": True,
            "model_info": model_info,
            "status": "ready" if wrapper.is_loaded else "not_loaded"
        }

    except Exception as e:
        return {
            "ml_available": True,
            "error": str(e),
            "status": "error"
        }


@router.post("/ml/load-model")
async def load_model_endpoint():
    """
    Încarcă modelul ML în memorie
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        print("[API] Incercare incarcare model...")
        success = ensure_model_loaded()

        if success:
            wrapper = get_model_wrapper()
            model_info = wrapper.get_model_info()

            print("[API] Model incarcat cu succes!")
            return {
                "message": "Model incarcat cu succes",
                "model_info": model_info
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Incarcarea modelului a esuat"
            )

    except Exception as e:
        print(f"[API] Eroare la incarcarea modelului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la incarcarea modelului: {str(e)}"
        )


@router.get("/ml/inspect-model")
async def inspect_model_file():
    """
    Inspectează fișierul modelului fără să îl încarce
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        from src.core.config import MODEL_PATH
        import torch

        if not MODEL_PATH.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fișierul model nu există: {MODEL_PATH}"
            )

        print(f"[API] Inspectare model: {MODEL_PATH}")

        # Încarcă checkpoint pentru inspecție
        checkpoint = torch.load(MODEL_PATH, map_location='cpu')

        inspection = {
            "file_path": str(MODEL_PATH),
            "file_size_mb": MODEL_PATH.stat().st_size / (1024 * 1024),
            "checkpoint_type": str(type(checkpoint)),
        }

        if isinstance(checkpoint, dict):
            inspection.update({
                "is_dict": True,
                "keys": list(checkpoint.keys()),
                "keys_count": len(checkpoint.keys())
            })

            # Inspectează fiecare key
            for key, value in checkpoint.items():
                if isinstance(value, dict):
                    inspection[f"{key}_info"] = {
                        "type": "dict",
                        "keys_count": len(value.keys()),
                        "sample_keys": list(value.keys())[:5]
                    }
                elif hasattr(value, 'shape'):
                    inspection[f"{key}_info"] = {
                        "type": "tensor",
                        "shape": list(value.shape)
                    }
                else:
                    inspection[f"{key}_info"] = {
                        "type": str(type(value)),
                        "value": str(value)
                    }
        else:
            inspection.update({
                "is_dict": False,
                "direct_type": str(type(checkpoint))
            })

        return inspection

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[API] Eroare la inspectarea modelului:\n{error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la inspectarea modelului: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Descarcă un fișier (returnează fișierul direct în browser)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

    try:
        print(f"[INFO] Descărcare fișier: {filename}")

        # Detectează tipul MIME
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=filename
        )

    except Exception as e:
        print(f"[ERROR] Eroare la descărcarea fișierului {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")


@router.get("/files/{filename}/download")
async def download_file_attachment(filename: str):
    """
    Descarcă un fișier ca attachment (forțează salvarea)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

    try:
        print(f"[INFO] Descărcare attachment: {filename}")

        # Pentru fișiere .nii.gz setează tipul corect
        if filename.lower().endswith('.nii.gz'):
            media_type = "application/gzip"
        elif filename.lower().endswith('.nii'):
            media_type = "application/octet-stream"
        else:
            media_type, _ = mimetypes.guess_type(str(file_path))
            if not media_type:
                media_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"[ERROR] Eroare la descărcarea attachment {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")