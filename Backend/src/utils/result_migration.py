# Creează fișierul src/utils/result_migration.py

"""
Utilitar pentru migrarea rezultatelor existente la noua structură de organizare
"""
from pathlib import Path
import shutil
import json
from typing import List, Dict
import time


def migrate_old_results_to_folders(results_dir: Path = Path("results")) -> Dict:
    """
    Migra rezultatele existente (format vechi) la noua structură de foldere

    Transformă:
    results/
    ├── folder1-seg.nii.gz
    ├── folder2-seg.nii.gz

    În:
    results/
    ├── folder1/
    │   └── folder1-seg.nii.gz
    ├── folder2/
    │   └── folder2-seg.nii.gz
    """
    if not results_dir.exists():
        return {"migrated": 0, "errors": [], "message": "Nu există rezultate de migrat"}

    migrated_files = []
    errors = []

    # Găsește fișierele de segmentare în format vechi
    old_seg_files = list(results_dir.glob("*-seg.nii.gz"))

    # Filtrează doar fișierele care sunt direct în results/ (nu în subfoldere)
    old_seg_files = [f for f in old_seg_files if f.parent == results_dir]

    print(f"[MIGRATION] Găsite {len(old_seg_files)} fișiere în format vechi")

    for seg_file in old_seg_files:
        try:
            # Extrage numele folderului din numele fișierului
            # folder_name-seg.nii.gz -> folder_name
            folder_name = seg_file.name.replace('-seg.nii.gz', '')

            # Creează folderul nou
            new_folder = results_dir / folder_name
            new_folder.mkdir(exist_ok=True)

            # Mută fișierul de segmentare
            new_seg_path = new_folder / seg_file.name
            shutil.move(str(seg_file), str(new_seg_path))

            migrated_files.append({
                "folder_name": folder_name,
                "old_path": str(seg_file),
                "new_folder": str(new_folder),
                "files_created": [new_seg_path.name]
            })

            print(f"[MIGRATION] Migrat: {seg_file.name} -> {new_folder.name}/")

        except Exception as e:
            error_msg = f"Eroare la migrarea {seg_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"[MIGRATION ERROR] {error_msg}")

    return {
        "migrated": len(migrated_files),
        "errors": len(errors),
        "migrated_files": migrated_files,
        "error_details": errors,
        "message": f"Migrare completă: {len(migrated_files)} fișiere, {len(errors)} erori"
    }


def validate_new_structure(results_dir: Path = Path("results")) -> Dict:
    """
    Validează că structura nouă este corectă
    """
    if not results_dir.exists():
        return {"valid": False, "message": "Directorul results nu există"}

    folders = []
    issues = []

    for item in results_dir.iterdir():
        if item.is_dir():
            folder_info = {
                "folder_name": item.name,
                "has_segmentation": False,
                "has_preprocessed": False,
                "files": []
            }

            # Verifică fișierele din folder
            seg_files = list(item.glob("*-seg.nii.gz"))
            prep_files = list(item.glob("preprocessed.pt"))

            folder_info["has_segmentation"] = len(seg_files) > 0
            folder_info["has_preprocessed"] = len(prep_files) > 0
            folder_info["files"] = [f.name for f in item.iterdir() if f.is_file()]

            if not folder_info["has_segmentation"]:
                issues.append(f"Folder {item.name}: lipsește fișierul de segmentare")

            folders.append(folder_info)

        elif item.is_file() and item.name.endswith('-seg.nii.gz'):
            issues.append(f"Fișier în format vechi găsit: {item.name}")

    return {
        "valid": len(issues) == 0,
        "folders_count": len(folders),
        "folders": folders,
        "issues": issues,
        "message": f"Structură validă: {len(folders)} foldere, {len(issues)} probleme"
    }


def create_results_index(results_dir: Path = Path("results")) -> Dict:
    """
    Creează un index cu toate rezultatele pentru navigare rapidă
    """
    index = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results_directory": str(results_dir.absolute()),
        "total_folders": 0,
        "folders": []
    }

    if not results_dir.exists():
        return index

    for folder in results_dir.iterdir():
        if folder.is_dir():
            folder_info = {
                "folder_name": folder.name,
                "path": str(folder),
                "files": {},
                "metadata": {}
            }

            # Inventariază fișierele
            for file in folder.iterdir():
                if file.is_file():
                    file_size = file.stat().st_size
                    folder_info["files"][file.name] = {
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "modified": file.stat().st_mtime
                    }

            # Extrage metadata din preprocessed.pt dacă există
            preprocessed_file = folder / "preprocessed.pt"
            if preprocessed_file.exists():
                try:
                    import torch
                    data = torch.load(preprocessed_file, map_location='cpu')
                    if isinstance(data, dict) and 'metadata' in data:
                        folder_info["metadata"] = data['metadata']
                except:
                    folder_info["metadata"] = {"error": "Nu s-a putut citi metadata din preprocessed.pt"}

            index["folders"].append(folder_info)

    index["total_folders"] = len(index["folders"])

    # Salvează index-ul
    index_file = results_dir / "results_index.json"
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)

    return index


# Endpoint pentru API
def add_migration_endpoints_to_api():
    """
    Adaugă endpoint-uri pentru migrare în API
    Adaugă acest cod în src/api/inference.py
    """
    migration_code = '''
@router.post("/admin/migrate-results")
async def migrate_old_results():
    """
    Migra rezultatele existente la noua structură de foldere (doar segmentare)
    """
    try:
        from src.utils.result_migration import migrate_old_results_to_folders

        result = migrate_old_results_to_folders()

        return {
            "message": "Migrare completă",
            "migration_result": result
        }

    except Exception as e:
        raise HTTPException(500, f"Eroare la migrare: {str(e)}")


@router.get("/admin/validate-structure")
async def validate_results_structure():
    """
    Validează structura organizării rezultatelor (segmentare + preprocessed)
    """
    try:
        from src.utils.result_migration import validate_new_structure

        validation = validate_new_structure()

        return {
            "message": "Validare completă",
            "validation_result": validation
        }

    except Exception as e:
        raise HTTPException(500, f"Eroare la validare: {str(e)}")


@router.post("/admin/create-index")
async def create_results_index_endpoint():
    """
    Creează index pentru toate rezultatele (metadata din preprocessed.pt)
    """
    try:
        from src.utils.result_migration import create_results_index

        index = create_results_index()

        return {
            "message": "Index creat cu succes",
            "index": index
        }

    except Exception as e:
        raise HTTPException(500, f"Eroare la crearea index-ului: {str(e)}")
    '''

    return migration_code