# -*- coding: utf-8 -*-
"""
Utilitati simple pentru manipularea fisierelor
"""
import shutil
import zipfile
import os
from pathlib import Path
from typing import Dict, List
from fastapi import UploadFile, HTTPException

from src.core.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, get_file_size_mb
from src.utils.nifti_validation import validate_segmentation_files, get_validation_summary


def is_allowed_file(filename: str) -> bool:
    """Verifica daca fisierul are o extensie permisa"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


def is_nifti_file(filename: str) -> bool:
    """Verifica daca fisierul este NIfTI"""
    return filename.lower().endswith('.nii') or filename.lower().endswith('.nii.gz')


def extract_zip_file(zip_path: Path) -> Dict:
    """
    Extrage un fisier ZIP si returneaza informatii despre fisierele extrase

    Args:
        zip_path: Calea catre fisierul ZIP

    Returns:
        Dict cu informatii despre extragere

    Raises:
        Exception: Daca extragerea esueaza
    """
    try:
        # Creeaza numele folderului bazat pe numele ZIP-ului
        folder_name = zip_path.stem  # numele fisierului fara extensie
        extract_dir = UPLOAD_DIR / folder_name

        # Daca folderul exista deja, adauga un suffix numeric
        counter = 1
        original_extract_dir = extract_dir
        while extract_dir.exists():
            extract_dir = UPLOAD_DIR / f"{original_extract_dir.name}_{counter}"
            counter += 1

        # Creeaza folderul de destinatie
        extract_dir.mkdir(exist_ok=True)

        extracted_files = []
        nifti_files = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Listeaza continutul ZIP-ului
            file_list = zip_ref.namelist()

            print(f"[INFO] ZIP contine {len(file_list)} fisiere")

            for file_info in zip_ref.infolist():
                # Ignora directoarele
                if file_info.is_dir():
                    continue

                filename = os.path.basename(file_info.filename)

                # Ignora fisierele ascunse si fisierele sistem
                if filename.startswith('.') or filename.startswith('__'):
                    continue

                # Extrage doar fisierele care au nume valid
                if filename and len(filename) > 0:
                    # Citeste continutul fisierului
                    file_data = zip_ref.read(file_info.filename)

                    # Salveaza fisierul in folderul de destinatie
                    output_path = extract_dir / filename

                    # Daca fisierul exista deja, adauga un suffix
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

                    # Verifica daca este fisier NIfTI
                    if is_nifti_file(output_path.name):
                        nifti_files.append(output_path.name)

                    print(f"[INFO] Extras: {output_path.name} ({get_file_size_mb(file_size)})")

        # sterge fisierul ZIP original dupa extragere
        zip_path.unlink()

        # Valideaza daca folderul contine fisierele necesare pentru segmentare
        validation_result = validate_segmentation_files(extract_dir)
        validation_summary = get_validation_summary(extract_dir)

        result = {
            "extracted_folder": extract_dir.name,
            "extracted_path": str(extract_dir.absolute()),
            "total_files": len(extracted_files),
            "nifti_files_count": len(nifti_files),
            "nifti_files": nifti_files,
            "all_files": extracted_files,
            "segmentation_validation": {
                "is_valid_for_segmentation": validation_result["is_valid"],
                "found_modalities": validation_result["found_modalities"],
                "missing_modalities": validation_result["missing_modalities"],
                "validation_summary": validation_summary,
                "validation_errors": validation_result["validation_errors"]
            }
        }

        print(f"[SUCCESS] ZIP extras cu succes: {len(extracted_files)} fisiere, {len(nifti_files)} NIfTI")
        print(f"[VALIDATION] {validation_summary}")

        return result

    except zipfile.BadZipFile:
        raise Exception("Fisierul ZIP este corupt sau invalid")
    except Exception as e:
        # Curata folderul partial creat in caz de eroare
        if 'extract_dir' in locals() and extract_dir.exists():
            try:
                shutil.rmtree(extract_dir)
            except:
                pass
        raise Exception(f"Eroare la extragerea ZIP: {str(e)}")


def validate_file(file: UploadFile) -> None:
    """
    Valideaza un fisier incarcat

    Args:
        file: Fisierul de validat

    Raises:
        HTTPException: Daca validarea esueaza
    """
    # Verifica numele
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fisierul trebuie sa aiba un nume")

    # Verifica extensia
    if not is_allowed_file(file.filename):
        allowed = ', '.join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"Doar fisiere {allowed} sunt acceptate"
        )

    # Verifica dimensiunea
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fisierul este prea mare (max {get_file_size_mb(MAX_FILE_SIZE)})"
        )


async def save_file(file: UploadFile) -> Dict:
    """
    Salveaza un fisier incarcat (si il dezarhiveaza daca este ZIP)

    Args:
        file: Fisierul de salvat

    Returns:
        Dict cu informatii despre fisier sau extragere

    Raises:
        HTTPException: Daca salvarea esueaza
    """
    try:
        file_path = UPLOAD_DIR / file.filename

        # Salveaza fisierul
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Verifica ca s-a salvat corect
        if not file_path.exists():
            raise Exception("Fisierul nu a fost salvat corect")

        actual_size = file_path.stat().st_size

        # Daca este ZIP, il dezarhiveaza
        if file.filename.lower().endswith('.zip'):
            print(f"[INFO] Detectat fisier ZIP, se dezarhiveaza...")

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
                # Daca extragerea esueaza, pastreaza ZIP-ul original
                print(f"[WARNING] Extragerea ZIP a esuat: {str(e)}")
                return {
                    "filename": file.filename,
                    "size": actual_size,
                    "size_mb": get_file_size_mb(actual_size),
                    "content_type": file.content_type,
                    "type": "zip_failed",
                    "path": str(file_path.absolute()),
                    "error": str(e)
                }

        # Pentru fisiere obisnuite (NIfTI)
        return {
            "filename": file.filename,
            "size": actual_size,
            "size_mb": get_file_size_mb(actual_size),
            "content_type": file.content_type,
            "type": "single_file",
            "path": str(file_path.absolute())
        }

    except Exception as e:
        # Curata fisierul partial daca exista
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Eroare la salvare: {str(e)}")


def list_files() -> List[Dict]:
    """
    Listeaza fisierele si folderele din directorul de upload

    Returns:
        Lista cu informatii despre fisiere si foldere
    """
    items = []
    try:
        # Listeaza fisierele individuale
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

        # Listeaza folderele (create din ZIP-uri)
        for folder_path in UPLOAD_DIR.iterdir():
            if folder_path.is_dir():
                # Numara fisierele NIfTI din folder
                nifti_files = list(folder_path.glob("*.nii*"))
                total_files = list(folder_path.glob("*"))

                # Calculeaza dimensiunea totala a folderului
                total_size = 0
                for file in total_files:
                    if file.is_file():
                        total_size += file.stat().st_size

                # Valideaza pentru segmentare
                validation_result = validate_segmentation_files(folder_path)

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
                    "nifti_files": [f.name for f in nifti_files],
                    "segmentation_ready": validation_result["is_valid"],
                    "found_modalities": list(validation_result["found_modalities"].keys()),
                    "missing_modalities": validation_result["missing_modalities"]
                })

        # Sorteaza dupa data modificarii
        items.sort(key=lambda f: f["modified"], reverse=True)

    except Exception as e:
        print(f"Eroare la listarea fisierelor: {e}")

    return items


def delete_file(filename: str) -> Dict:
    """
    sterge un fisier sau folder

    Args:
        filename: Numele fisierului/folderului de sters

    Returns:
        Dict cu informatii despre elementul sters

    Raises:
        HTTPException: Daca stergerea esueaza
    """
    item_path = UPLOAD_DIR / filename

    if not item_path.exists():
        raise HTTPException(status_code=404, detail="Fisierul sau folderul nu exista")

    try:
        if item_path.is_file():
            # sterge fisier
            file_size = item_path.stat().st_size
            item_path.unlink()

            return {
                "name": filename,
                "type": "file",
                "size": file_size,
                "size_mb": get_file_size_mb(file_size)
            }

        elif item_path.is_dir():
            # sterge folder si tot continutul
            total_size = 0
            file_count = 0

            # Calculeaza dimensiunea totala inainte de stergere
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
            raise Exception("Elementul nu este nici fisier, nici folder")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare la stergere: {str(e)}")