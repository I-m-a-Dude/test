# -*- coding: utf-8 -*-
"""
Utilități simple pentru manipularea fișierelor
"""
from typing import Dict, List
from fastapi import UploadFile, HTTPException

from src.core.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, get_file_size_mb


def is_allowed_file(filename: str) -> bool:
    """Verifică dacă fișierul are o extensie permisă"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


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
        raise HTTPException(status_code=400, detail="Fisierul trebuie sa aiba un nume")

    # Verifică extensia
    if not is_allowed_file(file.filename):
        allowed = ', '.join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"Doar fisiere {allowed} sunt acceptate"
        )

    # Verifică dimensiunea
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Fisierul este prea mare (max {get_file_size_mb(MAX_FILE_SIZE)})"
        )


async def save_file(file: UploadFile) -> Dict:
    """
    Salvează un fișier încărcat

    Args:
        file: Fișierul de salvat

    Returns:
        Dict cu informații despre fișier

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
            raise Exception("Fisierul nu a fost salvat corect")

        actual_size = file_path.stat().st_size

        return {
            "filename": file.filename,
            "size": actual_size,
            "size_mb": get_file_size_mb(actual_size),
            "content_type": file.content_type,
            "path": str(file_path.absolute())
        }

    except Exception as e:
        # Curăță fișierul parțial dacă există
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Eroare la salvare: {str(e)}")


def list_files() -> List[Dict]:
    """
    Listează fișierele din directorul de upload

    Returns:
        Lista cu informații despre fișiere
    """
    files = []
    try:
        for file_path in UPLOAD_DIR.glob("*.nii*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "size_mb": get_file_size_mb(stat.st_size),
                    "modified": stat.st_mtime,
                    "path": str(file_path.absolute())
                })

        # Sortează după data modificării
        files.sort(key=lambda f: f["modified"], reverse=True)

    except Exception as e:
        print(f"Eroare la listarea fisierelor: {e}")

    return files


def delete_file(filename: str) -> Dict:
    """
    Șterge un fișier

    Args:
        filename: Numele fișierului de șters

    Returns:
        Dict cu informații despre fișierul șters

    Raises:
        HTTPException: Dacă ștergerea eșuează
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fisierul nu exista")

    try:
        file_size = file_path.stat().st_size
        file_path.unlink()

        return {
            "filename": filename,
            "size": file_size,
            "size_mb": get_file_size_mb(file_size)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare la stergere: {str(e)}")