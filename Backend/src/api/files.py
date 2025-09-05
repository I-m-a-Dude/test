# -*- coding: utf-8 -*-
"""
API Endpoints pentru operatiile cu fisiere
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
    Rezolva calea catre un fisier, acceptand si fisiere din subfoldere

    Args:
        filename: Numele fisierului sau path relativ (ex: "folder/file.nii.gz")

    Returns:
        Path catre fisier

    Raises:
        HTTPException: Daca fisierul nu exista sau calea este nesigura
    """
    try:
        # Construieste calea si verifica ca nu iese din UPLOAD_DIR (securitate)
        file_path = UPLOAD_DIR / filename
        file_path = file_path.resolve()

        # Verifica ca fisierul este intr-adevar in UPLOAD_DIR sau subfolderele sale
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=400, detail="Calea catre fisier nu este permisa")

        # Verifica ca fisierul exista
        if not file_path.exists():
            # incearca sa il gaseasca in subfoldere daca nu e gasit direct
            possible_paths = list(UPLOAD_DIR.rglob(Path(filename).name))
            if possible_paths:
                print(f"[INFO] Fisier gasit in subfolder: {possible_paths[0]}")
                return possible_paths[0]
            else:
                raise HTTPException(status_code=404, detail="Fisierul nu exista")

        return file_path

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Eroare la rezolvarea caii pentru {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la procesarea caii: {str(e)}")


@router.post("/upload-mri")
async def upload_mri_file(file: UploadFile = File(...)):
    """
    Upload fisier MRI (inclusiv ZIP-uri cu fisiere NIfTI)
    """
    print(f"[INFO] incercare upload: {file.filename}")

    try:
        # Valideaza fisierul
        validate_file(file)

        # Salveaza fisierul (si il dezarhiveaza daca e ZIP)
        file_info = await save_file(file)

        if file_info.get("type") == "zip_extracted":
            print(f"[SUCCESS] ZIP dezarhivat: {file.filename}")
            print(f"[INFO] Extras in folderul: {file_info['extraction']['extracted_folder']}")
            print(f"[INFO] Fisiere NIfTI gasite: {file_info['extraction']['nifti_files_count']}")

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
                    "message": "ZIP salvat dar dezarhivarea a esuat",
                    "file_info": file_info
                }
            )

        else:
            print(f"[SUCCESS] Fisier salvat: {file.filename} ({file_info['size_mb']})")

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Fisier incarcat cu succes",
                    "file_info": file_info
                }
            )

    except HTTPException:
        # Re-ridica exceptiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neasteptata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare interna: {str(e)}")


@router.get("/")
async def get_uploaded_files():
    """
    Listeaza fisierele si folderele incarcate
    """
    try:
        items = list_files()

        files_count = len([item for item in items if item["type"] == "file"])
        folders_count = len([item for item in items if item["type"] == "folder"])

        print(f"[INFO] Listare: {files_count} fisiere, {folders_count} foldere")

        return {
            "items": items,
            "total_count": len(items),
            "files_count": files_count,
            "folders_count": folders_count,
            "upload_dir": str(UPLOAD_DIR.absolute())
        }

    except Exception as e:
        print(f"[ERROR] Eroare la listarea fisierelor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la listare: {str(e)}")


@router.delete("/{filename:path}")
async def delete_uploaded_file(filename: str):
    """
    sterge un fisier sau folder incarcat
    Accepta si paths catre fisiere din subfoldere
    """
    print(f"[INFO] incercare stergere: {filename}")

    try:
        result = delete_file(filename)

        if result["type"] == "file":
            print(f"[SUCCESS] Fisier sters: {filename} ({result['size_mb']})")
            message = f"Fisierul {filename} a fost sters cu succes"
        else:
            print(f"[SUCCESS] Folder sters: {filename} ({result['files_deleted']} fisiere, {result['size_mb']})")
            message = f"Folderul {filename} a fost sters cu succes"

        return {
            "message": message,
            "deleted_item": result
        }

    except HTTPException:
        # Re-ridica exceptiile HTTP
        raise
    except Exception as e:
        print(f"[ERROR] Eroare neasteptata la stergere: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare interna: {str(e)}")


@router.get("/{filename:path}/info")
async def get_file_info(filename: str):
    """
    Obtine informatii despre un fisier specific
    Accepta si paths catre fisiere din subfoldere
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
        print(f"[ERROR] Eroare la citirea informatiilor pentru {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la citirea informatiilor: {str(e)}")


@router.get("/{filename:path}/download")
async def download_file(filename: str):
    """
    Descarca un fisier (returneaza fisierul direct in browser)
    Accepta si paths catre fisiere din subfoldere
    """
    try:
        file_path = resolve_file_path(filename)
        actual_filename = file_path.name

        print(f"[INFO] Descarcare fisier: {filename} -> {file_path}")

        # Detecteaza tipul MIME
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
        print(f"[ERROR] Eroare la descarcarea fisierului {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descarcare: {str(e)}")


@router.get("/{filename:path}/download-attachment")
async def download_file_attachment(filename: str):
    """
    Descarca un fisier ca attachment (forteaza salvarea)
    Accepta si paths catre fisiere din subfoldere
    """
    try:
        file_path = resolve_file_path(filename)
        actual_filename = file_path.name

        print(f"[INFO] Descarcare attachment: {filename} -> {file_path}")

        # Pentru fisiere .nii.gz seteaza tipul corect
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
        print(f"[ERROR] Eroare la descarcarea attachment {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descarcare: {str(e)}")


@router.get("/folder/{folder_name}/files")
async def get_folder_files(folder_name: str):
    """
    Listeaza fisierele dintr-un folder specific
    """
    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Folderul {folder_name} nu exista")

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
        print(f"[ERROR] Eroare la listarea fisierelor din folder {folder_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la listarea folderului: {str(e)}")

    # Adaugă acest endpoint în Backend/src/api/files.py

@router.get("/{folder_name}/download-zip")
async def download_folder_as_zip(folder_name: str):
        """
        Descarcă un folder întreg ca fișier ZIP
        """
        try:
            folder_path = UPLOAD_DIR / folder_name

            if not folder_path.exists() or not folder_path.is_dir():
                raise HTTPException(status_code=404, detail=f"Folderul {folder_name} nu există")

            print(f"[INFO] Creează ZIP pentru folderul: {folder_name}")

            # Creează un fișier ZIP temporar
            import tempfile
            import zipfile
            import os
            from fastapi.responses import StreamingResponse

            # Creează un fișier temporar pentru ZIP
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                zip_path = temp_zip.name

            try:
                # Creează ZIP-ul cu toate fișierele din folder
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Parcurge recursiv toate fișierele din folder
                    for file_path in folder_path.rglob('*'):
                        if file_path.is_file():
                            # Calculează calea relativă în ZIP
                            arcname = file_path.relative_to(folder_path)
                            zip_file.write(file_path, arcname)
                            print(f"[INFO] Adăugat în ZIP: {arcname}")

                # Verifică că ZIP-ul a fost creat cu succes
                if not os.path.exists(zip_path):
                    raise Exception("Fișierul ZIP nu a fost creat")

                zip_size = os.path.getsize(zip_path)
                print(f"[SUCCESS] ZIP creat: {zip_path} ({get_file_size_mb(zip_size)})")

                # Creează un generator pentru streaming
                def generate_zip():
                    try:
                        with open(zip_path, 'rb') as zip_file:
                            while True:
                                chunk = zip_file.read(8192)  # 8KB chunks
                                if not chunk:
                                    break
                                yield chunk
                    finally:
                        # Șterge fișierul temporar după streaming
                        try:
                            os.unlink(zip_path)
                            print(f"[CLEANUP] Fișier temporar șters: {zip_path}")
                        except Exception as cleanup_error:
                            print(f"[WARNING] Nu s-a putut șterge fișierul temporar: {cleanup_error}")

                # Numele fișierului ZIP pentru download
                zip_filename = f"{folder_name}.zip"

                return StreamingResponse(
                    generate_zip(),
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={zip_filename}",
                        "Content-Length": str(zip_size)
                    }
                )

            except Exception as zip_error:
                # Cleanup în caz de eroare
                try:
                    if os.path.exists(zip_path):
                        os.unlink(zip_path)
                except:
                    pass
                raise zip_error

        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR] Eroare la crearea ZIP pentru {folder_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Eroare la crearea ZIP: {str(e)}")

@router.get("/{folder_name}/info-detailed")
async def get_folder_detailed_info(folder_name: str):
        """
        Obține informații detaliate despre un folder (pentru preview înainte de download)
        """
        try:
            folder_path = UPLOAD_DIR / folder_name

            if not folder_path.exists() or not folder_path.is_dir():
                raise HTTPException(status_code=404, detail=f"Folderul {folder_name} nu există")

            files_info = []
            total_size = 0
            nifti_count = 0

            # Parcurge recursiv toate fișierele
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    relative_path = file_path.relative_to(folder_path)

                    file_info = {
                        "name": file_path.name,
                        "relative_path": str(relative_path),
                        "size": stat.st_size,
                        "size_mb": get_file_size_mb(stat.st_size),
                        "modified": stat.st_mtime,
                        "extension": file_path.suffix,
                        "is_nifti": file_path.name.endswith('.nii') or file_path.name.endswith('.nii.gz')
                    }

                    files_info.append(file_info)
                    total_size += stat.st_size

                    if file_info["is_nifti"]:
                        nifti_count += 1

            return {
                "folder_name": folder_name,
                "folder_path": str(folder_path.absolute()),
                "total_files": len(files_info),
                "total_size": total_size,
                "total_size_mb": get_file_size_mb(total_size),
                "nifti_files_count": nifti_count,
                "files": files_info,
                "estimated_zip_size_mb": get_file_size_mb(int(total_size * 0.9))  # Estimare după compresie
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR] Eroare la obținerea informațiilor pentru {folder_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Eroare la obținerea informațiilor: {str(e)}")