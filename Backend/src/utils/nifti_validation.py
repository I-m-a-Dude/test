# -*- coding: utf-8 -*-
"""
Utilități pentru validarea fișierelor NIfTI necesare pentru segmentare
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# Modalitățile necesare pentru modelul de segmentare
REQUIRED_MODALITIES = {
    't1c': 't1c.nii.gz',  # T1 contrast enhanced
    't1n': 't1n.nii.gz',  # T1 native
    't2w': 't2w.nii.gz',  # T2 weighted
    't2f': 't2f.nii.gz'  # T2 FLAIR
}

# Pattern-uri alternative pentru recunoașterea modalităților
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
    Identifică modalitatea unui fișier NIfTI bazat pe nume

    Args:
        filename: Numele fișierului

    Returns:
        Modalitatea identificată ('t1c', 't1n', 't2w', 't2f') sau None
    """
    filename_lower = filename.lower()

    for modality, patterns in MODALITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, filename_lower):
                return modality

    return None


def validate_segmentation_files(folder_path: Path) -> Dict:
    """
    Validează dacă un folder conține toate fișierele necesare pentru segmentare

    Args:
        folder_path: Calea către folderul cu fișiere NIfTI

    Returns:
        Dict cu rezultatul validării
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
            result["validation_errors"].append("Folderul nu există sau nu este director")
            return result

        # Găsește toate fișierele NIfTI
        nifti_files = list(folder_path.glob("*.nii.gz")) + list(folder_path.glob("*.nii"))
        result["total_nifti_files"] = len(nifti_files)

        if len(nifti_files) == 0:
            result["validation_errors"].append("Nu au fost găsite fișiere NIfTI în folder")
            return result

        # Identifică modalitățile
        identified_modalities = {}
        unidentified_files = []

        for nifti_file in nifti_files:
            modality = identify_modality(nifti_file.name)

            if modality:
                if modality in identified_modalities:
                    # Modalitate duplicată
                    result["validation_errors"].append(
                        f"Modalitatea {modality} găsită de mai multe ori: "
                        f"{identified_modalities[modality]} și {nifti_file.name}"
                    )
                else:
                    identified_modalities[modality] = nifti_file.name
            else:
                unidentified_files.append(nifti_file.name)

        result["found_modalities"] = identified_modalities
        result["extra_files"] = unidentified_files

        # Verifică modalitățile lipsă
        required_modalities = set(REQUIRED_MODALITIES.keys())
        found_modalities = set(identified_modalities.keys())
        missing_modalities = required_modalities - found_modalities

        result["missing_modalities"] = list(missing_modalities)

        # Validarea finală
        if len(missing_modalities) == 0:
            result["is_valid"] = True
        else:
            result["validation_errors"].append(
                f"Modalități lipsă: {', '.join(missing_modalities)}"
            )

        print(f"[VALIDATION] Folder: {folder_path.name}")
        print(f"    - Fișiere NIfTI găsite: {len(nifti_files)}")
        print(f"    - Modalități identificate: {list(found_modalities)}")
        if missing_modalities:
            print(f"    - Modalități lipsă: {list(missing_modalities)}")
        if unidentified_files:
            print(f"    - Fișiere neidentificate: {unidentified_files}")
        print(f"    - Valid pentru segmentare: {'DA' if result['is_valid'] else 'NU'}")

        return result

    except Exception as e:
        result["validation_errors"].append(f"Eroare la validare: {str(e)}")
        return result


def get_modality_files_mapping(folder_path: Path) -> Optional[Dict[str, Path]]:
    """
    Returnează mapping-ul modalitate -> cale fișier pentru un folder valid

    Args:
        folder_path: Calea către folderul validat

    Returns:
        Dict cu mapping modalitate -> Path sau None dacă nu e valid
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
    Creează numele standard pentru fișierele de segmentare

    Args:
        base_name: Numele de bază (ex: "patient_001")

    Returns:
        Dict cu mapping modalitate -> nume fișier standard
    """
    return {
        modality: f"{base_name}_{filename}"
        for modality, filename in REQUIRED_MODALITIES.items()
    }


def rename_to_standard_format(folder_path: Path, base_name: Optional[str] = None) -> bool:
    """
    Redenumește fișierele într-un format standard pentru procesare

    Args:
        folder_path: Calea către folder
        base_name: Numele de bază (default: numele folderului)

    Returns:
        True dacă redenumirea a reușit
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

        print(f"[SUCCESS] Fișiere redenumite în format standard pentru {base_name}")
        return True

    except Exception as e:
        print(f"[ERROR] Eroare la redenumire: {str(e)}")
        return False


def get_validation_summary(folder_path: Path) -> str:
    """
    Returnează un rezumat textual al validării

    Args:
        folder_path: Calea către folder

    Returns:
        String cu rezumatul validării
    """
    result = validate_segmentation_files(folder_path)

    if result["is_valid"]:
        return f"✅ Folder valid pentru segmentare cu {len(result['found_modalities'])} modalități"
    else:
        errors = "; ".join(result["validation_errors"])
        return f"❌ Folder invalid: {errors}"


def find_valid_segmentation_folders(base_dir: Path) -> List[Tuple[Path, Dict]]:
    """
    Găsește toate folderele valide pentru segmentare într-un director

    Args:
        base_dir: Directorul de căutat

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

        print(f"[SEARCH] Găsite {len(valid_folders)} foldere valide în {base_dir}")

    except Exception as e:
        print(f"[ERROR] Eroare la căutarea folderelor: {str(e)}")

    return valid_folders