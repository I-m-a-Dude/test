# -*- coding: utf-8 -*-
"""
API Endpoints pentru operațiile cu fișiere
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import mimetypes

from src.core.config import UPLOAD_DIR, get_file_size_mb
from src.utils.file_utils import validate_file, save_file, list_files, delete_file

router = APIRouter(prefix="/files", tags=["Files"])


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


@router.get("/")
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


@router.delete("/{filename}")
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


@router.get("/{filename}/info")
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


@router.get("/{filename}/download")
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


@router.get("/{filename}/download-attachment")
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