# -*- coding: utf-8 -*-
"""
Utilități simple pentru manipularea fișierelor
"""
import shutil
import zipfile
import os
from pathlib import Path
from typing import Dict, List
from fastapi import UploadFile, HTTPException

from src.core.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, get_file_size_mb


def is_allowed_file(filename: str) -> bool:
    """Verifică dacă fișierul are o extensie permisă"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


def is_nifti_file(filename: str) -> bool:
    """Verifică dacă fișierul este NIfTI"""
    return filename.lower().endswith('.nii') or filename.lower().endswith('.nii.gz')


def extract_zip_file(zip_path: Path) -> Dict:
    """
    Extrage un fișier ZIP și returnează informații despre fișierele extrase

    Args:
        zip_path: Calea către fișierul ZIP

    Returns:
        Dict cu informații despre extragere

    Raises:
        Exception: Dacă extragerea eșuează
    """
    try:
        # Creează numele folderului bazat pe numele ZIP-ului
        folder_name = zip_path.stem  # numele fișierului fără extensie
        extract_dir = UPLOAD_DIR / folder_name

        # Dacă folderul există deja, adaugă un suffix numeric
        counter = 1
        original_extract_dir = extract_dir
        while extract_dir.exists():
            extract_dir = UPLOAD_DIR / f"{original_extract_dir.name}_{counter}"
            counter += 1

        # Creează folderul de destinație
        extract_dir.mkdir(exist_ok=True)

        extracted_files = []
        nifti_files = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Listează conținutul ZIP-ului
            file_list = zip_ref.namelist()

            print(f"[INFO] ZIP conține {len(file_list)} fișiere")

            for file_info in zip_ref.infolist():
                # Ignoră directoarele
                if file_info.is_dir():
                    continue

                filename = os.path.basename(file_info.filename)

                # Ignoră fișierele ascunse și fișierele sistem
                if filename.startswith('.') or filename.startswith('__'):
                    continue

                # Extrage doar fișierele care au nume valid
                if filename and len(filename) > 0:
                    # Citește conținutul fișierului
                    file_data = zip_ref.read(file_info.filename)

                    # Salvează fișierul în folderul de destinație
                    output_path = extract_dir / filename

                    # Dacă fișierul există deja, adaugă un suffix
                    counter = 1
                    original_output_path = output_path
                    while output_path.exists():
                        name_part = original_output_path.stem
                        ext_part = original_output_path.suffix
                        output_path = extract_dir / f"{name_part}_{counter}{ext_part}"
                        counter += 1

                    with open(output_path, 'wb') as output_file:
                        output_file.write(file_data)

                    file_size = len(file_data)
                    extracted_files.append({
                        "filename": output_path.name,
                        "original_path": file_info.filename,
                        "size": file_size,
                        "size_mb": get_file_size_mb(file_size)
                    })

                    # Verifică dacă este fișier NIfTI
                    if is_nifti_file(output_path.name):
                        nifti_files.append(output_path.name)

                    print(f"[INFO] Extras: {output_path.name} ({get_file_size_mb(file_size)})")

        # Șterge fișierul ZIP original după extragere
        zip_path.unlink()

        result = {
            "extracted_folder": extract_dir.name,
            "extracted_path": str(extract_dir.absolute()),
            "total_files": len(extracted_files),
            "nifti_files_count": len(nifti_files),
            "nifti_files": nifti_files,
            "all_files": extracted_files
        }

        print(f"[SUCCESS] ZIP extras cu succes: {len(extracted_files)} fișiere, {len(nifti_files)} NIfTI")
        return result

    except zipfile.BadZipFile:
        raise Exception("Fișierul ZIP este corupt sau invalid")
    except Exception as e:
        # Curăță folderul parțial creat în caz de eroare
        if 'extract_dir' in locals() and extract_dir.exists():
            try:
                shutil.rmtree(extract_dir)
            except:
                pass
        raise Exception(f"Eroare la extragerea ZIP: {str(e)}")


def validate_file(file: UploadFile) -> None:
    """
    Validează un fișier încărcat

    Args:
        file: Fișierul de validat

    Raises:
        HTTPException: Dacă validarea eșuează
    """
    # Verifică numele
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fișierul trebuie să aibă un nume")

    # Verifică extensia
    if not is_allowed_file(file.filename):
        allowed = ', '.join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"Doar fișiere {allowed} sunt acceptate"
        )

    # Verifică dimensiunea
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fișierul este prea mare (max {get_file_size_mb(MAX_FILE_SIZE)})"
        )


async def save_file(file: UploadFile) -> Dict:
    """
    Salvează un fișier încărcat (și îl dezarhivează dacă este ZIP)

    Args:
        file: Fișierul de salvat

    Returns:
        Dict cu informații despre fișier sau extragere

    Raises:
        HTTPException: Dacă salvarea eșuează
    """
    try:
        file_path = UPLOAD_DIR / file.filename

        # Salvează fișierul
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Verifică că s-a salvat corect
        if not file_path.exists():
            raise Exception("Fișierul nu a fost salvat corect")

        actual_size = file_path.stat().st_size

        # Dacă este ZIP, îl dezarhivează
        if file.filename.lower().endswith('.zip'):
            print(f"[INFO] Detectat fișier ZIP, se dezarhivează...")

            try:
                extraction_result = extract_zip_file(file_path)

                return {
                    "filename": file.filename,
                    "size": actual_size,
                    "size_mb": get_file_size_mb(actual_size),
                    "content_type": file.content_type,
                    "type": "zip_extracted",
                    "extraction": extraction_result
                }

            except Exception as e:
                # Dacă extragerea eșuează, păstrează ZIP-ul original
                print(f"[WARNING] Extragerea ZIP a eșuat: {str(e)}")
                return {
                    "filename": file.filename,
                    "size": actual_size,
                    "size_mb": get_file_size_mb(actual_size),
                    "content_type": file.content_type,
                    "type": "zip_failed",
                    "path": str(file_path.absolute()),
                    "error": str(e)
                }

        # Pentru fișiere obișnuite (NIfTI)
        return {
            "filename": file.filename,
            "size": actual_size,
            "size_mb": get_file_size_mb(actual_size),
            "content_type": file.content_type,
            "type": "single_file",
            "path": str(file_path.absolute())
        }

    except Exception as e:
        # Curăță fișierul parțial dacă există
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Eroare la salvare: {str(e)}")


def list_files() -> List[Dict]:
    """
    Listează fișierele și folderele din directorul de upload

    Returns:
        Lista cu informații despre fișiere și foldere
    """
    items = []
    try:
        # Listează fișierele individuale
        for file_path in UPLOAD_DIR.glob("*.nii*"):
            if file_path.is_file():
                stat = file_path.stat()
                items.append({
                    "name": file_path.name,
                    "type": "file",
                    "size": stat.st_size,
                    "size_mb": get_file_size_mb(stat.st_size),
                    "modified": stat.st_mtime,
                    "path": str(file_path.absolute()),
                    "extension": file_path.suffix
                })

        # Listează folderele (create din ZIP-uri)
        for folder_path in UPLOAD_DIR.iterdir():
            if folder_path.is_dir():
                # Numără fișierele NIfTI din folder
                nifti_files = list(folder_path.glob("*.nii*"))
                total_files = list(folder_path.glob("*"))

                # Calculează dimensiunea totală a folderului
                total_size = 0
                for file in total_files:
                    if file.is_file():
                        total_size += file.stat().st_size

                stat = folder_path.stat()
                items.append({
                    "name": folder_path.name,
                    "type": "folder",
                    "size": total_size,
                    "size_mb": get_file_size_mb(total_size),
                    "modified": stat.st_mtime,
                    "path": str(folder_path.absolute()),
                    "files_count": len(total_files),
                    "nifti_count": len(nifti_files),
                    "nifti_files": [f.name for f in nifti_files]
                })

        # Sortează după data modificării
        items.sort(key=lambda f: f["modified"], reverse=True)

    except Exception as e:
        print(f"Eroare la listarea fișierelor: {e}")

    return items


def delete_file(filename: str) -> Dict:
    """
    Șterge un fișier sau folder

    Args:
        filename: Numele fișierului/folderului de șters

    Returns:
        Dict cu informații despre elementul șters

    Raises:
        HTTPException: Dacă ștergerea eșuează
    """
    item_path = UPLOAD_DIR / filename

    if not item_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul sau folderul nu există")

    try:
        if item_path.is_file():
            # Șterge fișier
            file_size = item_path.stat().st_size
            item_path.unlink()

            return {
                "name": filename,
                "type": "file",
                "size": file_size,
                "size_mb": get_file_size_mb(file_size)
            }

        elif item_path.is_dir():
            # Șterge folder și tot conținutul
            total_size = 0
            file_count = 0

            # Calculează dimensiunea totală înainte de ștergere
            for file in item_path.rglob("*"):
                if file.is_file():
                    total_size += file.stat().st_size
                    file_count += 1

            shutil.rmtree(item_path)

            return {
                "name": filename,
                "type": "folder",
                "size": total_size,
                "size_mb": get_file_size_mb(total_size),
                "files_deleted": file_count
            }

        else:
            raise Exception("Elementul nu este nici fișier, nici folder")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare la ștergere: {str(e)}")