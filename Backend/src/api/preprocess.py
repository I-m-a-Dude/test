# -*- coding: utf-8 -*-
"""
API Endpoints pentru preprocesare
"""
from fastapi import APIRouter, HTTPException
import base64
import io

from src.core.config import UPLOAD_DIR, TEMP_PREPROCESSING_DIR, get_file_size_mb

# Import services pentru preprocesare
try:
    from src.services import get_preprocessor, preprocess_folder_simple
    from src.utils.nifti_validation import find_valid_segmentation_folders

    SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Service dependencies nu sunt disponibile: {e}")
    SERVICE_AVAILABLE = False

# Import pentru vizualizare
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend non-interactive pentru server
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

router = APIRouter(prefix="/preprocess", tags=["Preprocessing"])


@router.get("/status")
async def get_preprocess_status():
    """
    Verifica statusul sistemului de preprocesare
    """
    if not SERVICE_AVAILABLE:
        return {
            "preprocess_available": False,
            "error": "Dependentele pentru preprocesare nu sunt instalate",
            "required_packages": ["monai", "torch", "nibabel"]
        }

    try:
        preprocessor = get_preprocessor()
        info = preprocessor.get_preprocessing_info()

        return {
            "preprocess_available": True,
            "preprocessing_info": info,
            "status": "ready" if info["is_initialized"] else "not_initialized"
        }

    except Exception as e:
        return {
            "preprocess_available": True,
            "error": str(e),
            "status": "error"
        }


@router.get("/folders")
async def get_valid_folders():
    """
    Gaseste folderele valide pentru segmentare
    """
    if not SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de preprocesare nu este disponibil"
        )

    try:
        valid_folders = find_valid_segmentation_folders(UPLOAD_DIR)

        folders_info = []
        for folder_path, validation_result in valid_folders:
            folders_info.append({
                "folder_name": folder_path.name,
                "folder_path": str(folder_path),
                "found_modalities": validation_result["found_modalities"],
                "total_nifti_files": validation_result["total_nifti_files"]
            })

        return {
            "valid_folders_count": len(folders_info),
            "valid_folders": folders_info
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la cautarea folderelor: {str(e)}"
        )


@router.post("/folder/{folder_name}")
async def preprocess_folder_endpoint(folder_name: str, save_data: bool = True):
    """
    Preproceseaza un folder specific pentru inferenta si salveaza datele
    """
    if not SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de preprocesare nu este disponibil"
        )

    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul {folder_name} nu exista"
            )

        print(f"[API] incercare preprocesare folder: {folder_name}")

        # Preproceseaza folderul
        result = preprocess_folder_simple(folder_path)

        # Debug: afiseaza cheile disponibile
        print(f"[DEBUG] Chei disponibile in result: {list(result.keys())}")

        # Salveaza datele preprocesate daca e solicitat
        saved_path = None
        if save_data:
            import torch

            # incearca sa gaseasca tensorul preprocesат sub diferite chei posibile
            preprocessed_tensor = None
            # FIXED: Added "image_tensor" to the possible keys
            possible_keys = ["image_tensor", "preprocessed_data", "data", "tensor", "processed_tensor", "output"]

            for key in possible_keys:
                if key in result:
                    preprocessed_tensor = result[key]
                    print(f"[DEBUG] Tensorul gasit sub cheia: {key}")
                    break

            if preprocessed_tensor is None:
                # Daca nu gaseste tensorul, afiseaza toate valorile pentru debugging
                print(f"[ERROR] Nu s-a gasit tensorul preprocesат. Result keys: {list(result.keys())}")
                for key, value in result.items():
                    print(f"[DEBUG] {key}: {type(value)} - {value if not hasattr(value, 'shape') else f'shape: {value.shape}'}")
                raise HTTPException(
                    status_code=500,
                    detail="Tensorul preprocesат nu a fost gasit in rezultat"
                )

            # Convert MetaTensor to regular tensor if needed
            if hasattr(preprocessed_tensor, 'as_tensor'):
                preprocessed_tensor = preprocessed_tensor.as_tensor()
            elif not isinstance(preprocessed_tensor, torch.Tensor):
                preprocessed_tensor = torch.tensor(preprocessed_tensor)

            # Creeaza directorul pentru date preprocesate
            preprocessed_dir = TEMP_PREPROCESSING_DIR
            preprocessed_dir.mkdir(exist_ok=True)

            # Salveaza tensorul
            output_path = preprocessed_dir / f"{folder_name}_preprocessed.pt"
            torch.save(preprocessed_tensor, output_path)
            saved_path = str(output_path)

            print(f"[API] Date preprocesate salvate in: {saved_path}")

        # Extrage informatii pentru raspuns (fara tensorul mare)
        response_data = {
            "message": f"Folder {folder_name} preprocesат cu succes",
            "folder_name": result["folder_name"],
            "processed_shape": result["processed_shape"],
            "original_modalities": list(result["original_paths"].keys()),
            "preprocessing_config": result["preprocessing_config"]
        }

        if saved_path:
            response_data["saved_path"] = saved_path
            response_data["saved_filename"] = f"{folder_name}_preprocessed.pt"

        print(f"[API] Preprocesare completa pentru {folder_name}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Eroare la preprocesarea folderului {folder_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la preprocesare: {str(e)}"
        )


@router.get("/visualize/{filename}")
async def visualize_preprocessed_data(filename: str,
                                      slice_axis: str = "axial",
                                      slice_index: int = None,
                                      modality: str = "all"):
    """
    Vizualizeaza datele preprocesate salvate

    Args:
        filename: Numele fisierului .pt
        slice_axis: Axa pentru slice ("axial", "coronal", "sagital")
        slice_index: Indexul slice-ului (None pentru mijloc)
        modality: Modalitatea de vizualizat ("all", "t1n", "t1c", "t2w", "t2f")
    """
    if not SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de preprocesare nu este disponibil"
        )

    if not MATPLOTLIB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Matplotlib nu este disponibil pentru vizualizare"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul preprocesат {filename} nu exista"
            )

        print(f"[VISUALIZE] incarca si vizualizeaza: {filename}")

        # incarca tensorul
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            tensor = data['image_tensor']
            metadata = data.get('metadata', {})
        else:
            tensor = data
            metadata = {}

        # Converteste la numpy pentru matplotlib
        if hasattr(tensor, 'numpy'):
            array = tensor.numpy()
        else:
            array = np.array(tensor)

        print(f"[VISUALIZE] Shape tensor: {array.shape}")

        # Verifica dimensiunile [4, H, W, D]
        if len(array.shape) != 4 or array.shape[0] != 4:
            raise HTTPException(
                status_code=400,
                detail=f"Format tensor neasteptat: {array.shape}. Se asteapta [4, H, W, D]"
            )

        channels, height, width, depth = array.shape
        modality_names = ["t1n", "t1c", "t2w", "t2f"]

        # Determina indexul slice-ului
        axis_mapping = {
            "axial": 2,  # slice pe axa Z (depth)
            "coronal": 1,  # slice pe axa Y (height)
            "sagital": 0  # slice pe axa X (width)
        }

        if slice_axis not in axis_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Axa invalida: {slice_axis}. Optiuni: {list(axis_mapping.keys())}"
            )

        axis_idx = axis_mapping[slice_axis]
        max_slice = array.shape[axis_idx + 1]  # +1 pentru ca primul index e channel-ul

        if slice_index is None:
            slice_index = max_slice // 2
        elif slice_index < 0 or slice_index >= max_slice:
            raise HTTPException(
                status_code=400,
                detail=f"Index slice invalid: {slice_index}. Range: 0-{max_slice - 1}"
            )

        # Extrage slice-urile
        if slice_axis == "axial":
            slice_data = array[:, :, :, slice_index]  # [4, H, W]
        elif slice_axis == "coronal":
            slice_data = array[:, :, slice_index, :]  # [4, H, D]
        else:  # sagital
            slice_data = array[:, slice_index, :, :]  # [4, W, D]

        print(f"[VISUALIZE] Slice {slice_axis} #{slice_index}, shape: {slice_data.shape}")

        # Genereaza vizualizarea
        if modality == "all":
            # Creeaza o figura cu toate modalitatile
            fig, axes = plt.subplots(2, 2, figsize=(12, 12))
            fig.suptitle(f'{filename} - {slice_axis.title()} Slice #{slice_index}', fontsize=16)

            for i, (ax, mod_name) in enumerate(zip(axes.flat, modality_names)):
                im = ax.imshow(slice_data[i], cmap='gray', interpolation='nearest')
                ax.set_title(f'{mod_name.upper()}')
                ax.axis('off')
                plt.colorbar(im, ax=ax, shrink=0.8)

            plt.tight_layout()

        else:
            # Vizualizeaza o singura modalitate
            if modality not in modality_names:
                raise HTTPException(
                    status_code=400,
                    detail=f"Modalitate invalida: {modality}. Optiuni: {modality_names}"
                )

            mod_idx = modality_names.index(modality)

            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
            im = ax.imshow(slice_data[mod_idx], cmap='gray', interpolation='nearest')
            ax.set_title(f'{filename} - {modality.upper()} - {slice_axis.title()} Slice #{slice_index}')
            ax.axis('off')
            plt.colorbar(im, ax=ax)

        # Converteste figura in base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        # Calculeaza statistici pentru slice
        slice_stats = {}
        for i, mod_name in enumerate(modality_names):
            mod_slice = slice_data[i]
            slice_stats[mod_name] = {
                "min": float(mod_slice.min()),
                "max": float(mod_slice.max()),
                "mean": float(mod_slice.mean()),
                "std": float(mod_slice.std())
            }

        return {
            "message": "Vizualizare generata cu succes",
            "filename": filename,
            "tensor_info": {
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "modalities": modality_names
            },
            "slice_info": {
                "axis": slice_axis,
                "index": slice_index,
                "max_index": max_slice - 1,
                "shape": list(slice_data.shape)
            },
            "visualization": {
                "image_base64": image_base64,
                "modality_shown": modality,
                "stats": slice_stats
            },
            "metadata": metadata,
            "navigation": {
                "prev_slice": max(0, slice_index - 1),
                "next_slice": min(max_slice - 1, slice_index + 1),
                "total_slices": max_slice
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VISUALIZE] Eroare la vizualizare: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la vizualizare: {str(e)}"
        )


@router.get("/slice-info/{filename}")
async def get_slice_info(filename: str):
    """
    Obtine informatii despre dimensiunile tensorului pentru navigare
    """
    if not SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de preprocesare nu este disponibil"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul preprocesат {filename} nu exista"
            )

        # incarca doar header-ul pentru informatii rapide
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            tensor = data['image_tensor']
            metadata = data.get('metadata', {})
        else:
            tensor = data
            metadata = {}

        shape = list(tensor.shape)

        if len(shape) != 4 or shape[0] != 4:
            raise HTTPException(
                status_code=400,
                detail=f"Format tensor neasteptat: {shape}"
            )

        channels, height, width, depth = shape

        return {
            "filename": filename,
            "tensor_shape": shape,
            "modalities": ["t1n", "t1c", "t2w", "t2f"],
            "slice_ranges": {
                "axial": {"max": depth - 1, "mid": depth // 2},
                "coronal": {"max": height - 1, "mid": height // 2},
                "sagital": {"max": width - 1, "mid": width // 2}
            },
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la obtinerea informatiilor: {str(e)}"
        )


@router.get("/saved")
async def get_preprocessed_files():
    """
    Listeaza fisierele preprocesate salvate
    """
    try:
        preprocessed_dir = TEMP_PREPROCESSING_DIR

        if not preprocessed_dir.exists():
            return {
                "preprocessed_files": [],
                "count": 0,
                "preprocessed_dir": str(preprocessed_dir)
            }

        files = []
        for file_path in preprocessed_dir.glob("*.pt"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            })

        return {
            "preprocessed_files": files,
            "count": len(files),
            "preprocessed_dir": str(preprocessed_dir)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la listarea fisierelor preprocesate: {str(e)}"
        )


@router.get("/load/{filename}")
async def load_preprocessed_data(filename: str):
    """
    incarca date preprocesate salvate
    """
    if not SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de preprocesare nu este disponibil"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fisierul preprocesат {filename} nu exista"
            )

        # incarca tensorul
        data = torch.load(file_path)

        return {
            "message": f"Date preprocesate incarcate cu succes",
            "filename": filename,
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "device": str(data.device)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la incarcarea datelor: {str(e)}"
        )