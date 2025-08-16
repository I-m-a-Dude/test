# -*- coding: utf-8 -*-
"""
Toate endpoint-urile API pentru MediView Backend
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import mimetypes

from src.core.config import APP_NAME, VERSION, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from src.utils.file_utils import validate_file, save_file, list_files, delete_file

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
    Upload fișier MRI
    """
    print(f"[INFO] Încercare upload: {file.filename}")

    try:
        # Validează fișierul
        validate_file(file)

        # Salvează fișierul
        file_info = await save_file(file)

        print(f"[SUCCESS] Fisier salvat: {file.filename} ({file_info['size_mb']})")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Fisier incarcat cu succes",
                "file_info": file_info
            }
        )

    except HTTPException:
        # Re-ridică excepțiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neasteptata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare interna: {str(e)}")


@router.get("/files")
async def get_uploaded_files():
    """
    Listează fișierele încărcate
    """
    try:
        files = list_files()

        print(f"[INFO] Listare fisiere: {len(files)} fisiere gasite")

        return {
            "files": files,
            "count": len(files),
            "upload_dir": str(UPLOAD_DIR.absolute())
        }

    except Exception as e:
        print(f"[ERROR] Eroare la listarea fisierelor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la listare: {str(e)}")


@router.delete("/files/{filename}")
async def delete_uploaded_file(filename: str):
    """
    Șterge un fișier încărcat
    """
    print(f"[INFO] Incercare stergere: {filename}")

    try:
        result = delete_file(filename)

        print(f"[SUCCESS] Fisier sters: {filename} ({result['size_mb']})")

        return {
            "message": f"Fisierul {filename} a fost sters cu succes",
            "file_info": result
        }

    except HTTPException:
        # Re-ridică excepțiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neasteptata la stergere: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare interna: {str(e)}")


@router.get("/files/{filename}/info")
async def get_file_info(filename: str):
    """
    Obține informații despre un fișier specific
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fisierul nu exista")

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
        raise HTTPException(status_code=500, detail=f"Eroare la citirea informatiilor: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Descarcă un fișier (returnează fișierul direct în browser)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fisierul nu exista")

    try:
        print(f"[INFO] Descarcare fisier: {filename}")

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
        print(f"[ERROR] Eroare la descarcarea fisierului {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descarcare: {str(e)}")


@router.get("/files/{filename}/download")
async def download_file_attachment(filename: str):
    """
    Descarcă un fișier ca attachment (forțează salvarea)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fisierul nu exista")

    try:
        print(f"[INFO] Descarcare attachment: {filename}")

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
        print(f"[ERROR] Eroare la descarcarea attachment {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descarcare: {str(e)}")