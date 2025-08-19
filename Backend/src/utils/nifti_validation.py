# -*- coding: utf-8 -*-
"""
Utilitati pentru validarea fisierelor NIfTI necesare pentru segmentare
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# Modalitatile necesare pentru modelul de segmentare
REQUIRED_MODALITIES = {
    't1c': 't1c.nii.gz',  # T1 contrast enhanced
    't1n': 't1n.nii.gz',  # T1 native
    't2w': 't2w.nii.gz',  # T2 weighted
    't2f': 't2f.nii.gz'  # T2 FLAIR
}

# Pattern-uri alternative pentru recunoasterea modalitatilor
MODALITY_PATTERNS = {
    't1c': [
        r't1c\.nii\.gz$',
        r't1_c\.nii\.gz$',
        r't1-c\.nii\.gz$',
        r't1ce\.nii\.gz$',
        r't1_ce\.nii\.gz$',
        r't1-ce\.nii\.gz$',
        r't1_contrast\.nii\.gz$',
        r't1_gd\.nii\.gz$'
    ],
    't1n': [
        r't1n\.nii\.gz$',
        r't1_n\.nii\.gz$',
        r't1-n\.nii\.gz$',
        r't1\.nii\.gz$',
        r't1_native\.nii\.gz$'
    ],
    't2w': [
        r't2w\.nii\.gz$',
        r't2_w\.nii\.gz$',
        r't2-w\.nii\.gz$',
        r't2\.nii\.gz$',
        r't2_weighted\.nii\.gz$'
    ],
    't2f': [
        r't2f\.nii\.gz$',
        r't2_f\.nii\.gz$',
        r't2-f\.nii\.gz$',
        r't2_flair\.nii\.gz$',
        r't2-flair\.nii\.gz$',
        r'flair\.nii\.gz$',
        r't2_fluid\.nii\.gz$'
    ]
}


def identify_modality(filename: str) -> Optional[str]:
    """
    Identifica modalitatea unui fisier NIfTI bazat pe nume

    Args:
        filename: Numele fisierului

    Returns:
        Modalitatea identificata ('t1c', 't1n', 't2w', 't2f') sau None
    """
    filename_lower = filename.lower()

    for modality, patterns in MODALITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, filename_lower):
                return modality

    return None


def validate_segmentation_files(folder_path: Path) -> Dict:
    """
    Valideaza daca un folder contine toate fisierele necesare pentru segmentare

    Args:
        folder_path: Calea catre folderul cu fisiere NIfTI

    Returns:
        Dict cu rezultatul validarii
    """
    result = {
        "is_valid": False,
        "found_modalities": {},
        "missing_modalities": [],
        "extra_files": [],
        "total_nifti_files": 0,
        "validation_errors": []
    }

    try:
        if not folder_path.exists() or not folder_path.is_dir():
            result["validation_errors"].append("Folderul nu exista sau nu este director")
            return result

        # Gaseste toate fisierele NIfTI
        nifti_files = list(folder_path.glob("*.nii.gz")) + list(folder_path.glob("*.nii"))
        result["total_nifti_files"] = len(nifti_files)

        if len(nifti_files) == 0:
            result["validation_errors"].append("Nu au fost gasite fisiere NIfTI in folder")
            return result

        # Identifica modalitatile
        identified_modalities = {}
        unidentified_files = []

        for nifti_file in nifti_files:
            modality = identify_modality(nifti_file.name)

            if modality:
                if modality in identified_modalities:
                    # Modalitate duplicata
                    result["validation_errors"].append(
                        f"Modalitatea {modality} gasita de mai multe ori: "
                        f"{identified_modalities[modality]} si {nifti_file.name}"
                    )
                else:
                    identified_modalities[modality] = nifti_file.name
            else:
                unidentified_files.append(nifti_file.name)

        result["found_modalities"] = identified_modalities
        result["extra_files"] = unidentified_files

        # Verifica modalitatile lipsa
        required_modalities = set(REQUIRED_MODALITIES.keys())
        found_modalities = set(identified_modalities.keys())
        missing_modalities = required_modalities - found_modalities

        result["missing_modalities"] = list(missing_modalities)

        # Validarea finala
        if len(missing_modalities) == 0:
            result["is_valid"] = True
        else:
            result["validation_errors"].append(
                f"Modalitati lipsa: {', '.join(missing_modalities)}"
            )

        print(f"[VALIDATION] Folder: {folder_path.name}")
        print(f"    - Fisiere NIfTI gasite: {len(nifti_files)}")
        print(f"    - Modalitati identificate: {list(found_modalities)}")
        if missing_modalities:
            print(f"    - Modalitati lipsa: {list(missing_modalities)}")
        if unidentified_files:
            print(f"    - Fisiere neidentificate: {unidentified_files}")
        print(f"    - Valid pentru segmentare: {'DA' if result['is_valid'] else 'NU'}")

        return result

    except Exception as e:
        result["validation_errors"].append(f"Eroare la validare: {str(e)}")
        return result


def get_modality_files_mapping(folder_path: Path) -> Optional[Dict[str, Path]]:
    """
    Returneaza mapping-ul modalitate -> cale fisier pentru un folder valid

    Args:
        folder_path: Calea catre folderul validat

    Returns:
        Dict cu mapping modalitate -> Path sau None daca nu e valid
    """
    validation_result = validate_segmentation_files(folder_path)

    if not validation_result["is_valid"]:
        return None

    mapping = {}
    for modality, filename in validation_result["found_modalities"].items():
        mapping[modality] = folder_path / filename

    return mapping


def create_standard_filenames(base_name: str) -> Dict[str, str]:
    """
    Creeaza numele standard pentru fisierele de segmentare

    Args:
        base_name: Numele de baza (ex: "patient_001")

    Returns:
        Dict cu mapping modalitate -> nume fisier standard
    """
    return {
        modality: f"{base_name}_{filename}"
        for modality, filename in REQUIRED_MODALITIES.items()
    }


def rename_to_standard_format(folder_path: Path, base_name: Optional[str] = None) -> bool:
    """
    Redenumeste fisierele intr-un format standard pentru procesare

    Args:
        folder_path: Calea catre folder
        base_name: Numele de baza (default: numele folderului)

    Returns:
        True daca redenumirea a reusit
    """
    if base_name is None:
        base_name = folder_path.name

    validation_result = validate_segmentation_files(folder_path)

    if not validation_result["is_valid"]:
        print(f"[ERROR] Nu se poate redenumi - folderul nu e valid pentru segmentare")
        return False

    try:
        standard_names = create_standard_filenames(base_name)

        for modality, current_filename in validation_result["found_modalities"].items():
            current_path = folder_path / current_filename
            new_filename = standard_names[modality]
            new_path = folder_path / new_filename

            if current_path != new_path:
                current_path.rename(new_path)
                print(f"[RENAME] {current_filename} -> {new_filename}")

        print(f"[SUCCESS] Fisiere redenumite in format standard pentru {base_name}")
        return True

    except Exception as e:
        print(f"[ERROR] Eroare la redenumire: {str(e)}")
        return False


def get_validation_summary(folder_path: Path) -> str:
    """
    Returneaza un rezumat textual al validarii

    Args:
        folder_path: Calea catre folder

    Returns:
        String cu rezumatul validarii
    """
    result = validate_segmentation_files(folder_path)

    if result["is_valid"]:
        return f"✅ Folder valid pentru segmentare cu {len(result['found_modalities'])} modalitati"
    else:
        errors = "; ".join(result["validation_errors"])
        return f"❌ Folder invalid: {errors}"


def find_valid_segmentation_folders(base_dir: Path) -> List[Tuple[Path, Dict]]:
    """
    Gaseste toate folderele valide pentru segmentare intr-un director

    Args:
        base_dir: Directorul de cautat

    Returns:
        Lista de tuple (folder_path, validation_result)
    """
    valid_folders = []

    try:
        for folder_path in base_dir.iterdir():
            if folder_path.is_dir():
                validation_result = validate_segmentation_files(folder_path)
                if validation_result["is_valid"]:
                    valid_folders.append((folder_path, validation_result))

        print(f"[SEARCH] Gasite {len(valid_folders)} foldere valide in {base_dir}")

    except Exception as e:
        print(f"[ERROR] Eroare la cautarea folderelor: {str(e)}")

    return valid_folders