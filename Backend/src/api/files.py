# -*- coding: utf-8 -*-
"""
API Endpoints pentru operațiile cu fișiere
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import mimetypes
from pathlib import Path

from src.core.config import UPLOAD_DIR, get_file_size_mb
from src.utils.file_utils import validate_file, save_file, list_files, delete_file

router = APIRouter(prefix="/files", tags=["Files"])


def resolve_file_path(filename: str) -> Path:
    """
    Rezolvă calea către un fișier, acceptând și fișiere din subfoldere

    Args:
        filename: Numele fișierului sau path relativ (ex: "folder/file.nii.gz")

    Returns:
        Path către fișier

    Raises:
        HTTPException: Dacă fișierul nu există sau calea este nesigură
    """
    try:
        # Construiește calea și verifică că nu iese din UPLOAD_DIR (securitate)
        file_path = UPLOAD_DIR / filename
        file_path = file_path.resolve()

        # Verifică că fișierul este într-adevăr în UPLOAD_DIR sau subfolderele sale
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=400, detail="Calea către fișier nu este permisă")

        # Verifică că fișierul există
        if not file_path.exists():
            # Încearcă să îl găsească în subfoldere dacă nu e găsit direct
            possible_paths = list(UPLOAD_DIR.rglob(Path(filename).name))
            if possible_paths:
                print(f"[INFO] Fișier găsit în subfolder: {possible_paths[0]}")
                return possible_paths[0]
            else:
                raise HTTPException(status_code=404, detail="Fișierul nu există")

        return file_path

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la rezolvarea căii pentru {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la procesarea căii: {str(e)}")


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


@router.delete("/{filename:path}")
async def delete_uploaded_file(filename: str):
    """
    Șterge un fișier sau folder încărcat
    Acceptă și paths către fișiere din subfoldere
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


@router.get("/{filename:path}/info")
async def get_file_info(filename: str):
    """
    Obține informații despre un fișier specific
    Acceptă și paths către fișiere din subfoldere
    """
    try:
        file_path = resolve_file_path(filename)

        stat = file_path.stat()

        return {
            "filename": filename,
            "actual_path": str(file_path.relative_to(UPLOAD_DIR)),
            "size": stat.st_size,
            "size_mb": get_file_size_mb(stat.st_size),
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "path": str(file_path.absolute()),
            "extension": file_path.suffix
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la citirea informațiilor pentru {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la citirea informațiilor: {str(e)}")


@router.get("/{filename:path}/download")
async def download_file(filename: str):
    """
    Descarcă un fișier (returnează fișierul direct în browser)
    Acceptă și paths către fișiere din subfoldere
    """
    try:
        file_path = resolve_file_path(filename)
        actual_filename = file_path.name

        print(f"[INFO] Descărcare fișier: {filename} -> {file_path}")

        # Detectează tipul MIME
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=actual_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la descărcarea fișierului {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")


@router.get("/{filename:path}/download-attachment")
async def download_file_attachment(filename: str):
    """
    Descarcă un fișier ca attachment (forțează salvarea)
    Acceptă și paths către fișiere din subfoldere
    """
    try:
        file_path = resolve_file_path(filename)
        actual_filename = file_path.name

        print(f"[INFO] Descărcare attachment: {filename} -> {file_path}")

        # Pentru fișiere .nii.gz setează tipul corect
        if actual_filename.lower().endswith('.nii.gz'):
            media_type = "application/gzip"
        elif actual_filename.lower().endswith('.nii'):
            media_type = "application/octet-stream"
        else:
            media_type, _ = mimetypes.guess_type(str(file_path))
            if not media_type:
                media_type = "application/octet-stream"

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=actual_filename,
            headers={"Content-Disposition": f"attachment; filename={actual_filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la descărcarea attachment {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")


@router.get("/folder/{folder_name}/files")
async def get_folder_files(folder_name: str):
    """
    Listează fișierele dintr-un folder specific
    """
    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Folderul {folder_name} nu există")

        files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "relative_path": f"{folder_name}/{file_path.name}",
                    "size": stat.st_size,
                    "size_mb": get_file_size_mb(stat.st_size),
                    "modified": stat.st_mtime,
                    "extension": file_path.suffix,
                    "is_nifti": file_path.name.endswith('.nii') or file_path.name.endswith('.nii.gz')
                })

        return {
            "folder_name": folder_name,
            "files": files,
            "files_count": len(files),
            "nifti_count": len([f for f in files if f["is_nifti"]])
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la listarea fișierelor din folder {folder_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la listarea folderului: {str(e)}")