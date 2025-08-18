# -*- coding: utf-8 -*-
"""
Toate endpoint-urile API pentru MediView Backend
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import mimetypes

from src.core.config import APP_NAME, VERSION, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, TEMP_PREPROCESSING_DIR
from src.utils.file_utils import validate_file, save_file, list_files, delete_file

# Import ML și Services pentru test endpoints
try:
    from src.ml import get_model_wrapper, ensure_model_loaded

    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] ML dependencies nu sunt disponibile: {e}")
    ML_AVAILABLE = False

try:
    from src.services import get_preprocessor, preprocess_folder_simple
    from src.utils.nifti_validation import find_valid_segmentation_folders

    SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Service dependencies nu sunt disponibile: {e}")
    SERVICE_AVAILABLE = False

# Adaugă aceste import-uri la începutul fișierului
import base64
import io
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend non-interactive pentru server
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

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


@router.get("/files")
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


@router.delete("/files/{filename}")
async def delete_uploaded_file(filename: str):
    """
    Șterge un fișier sau folder încărcat
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


@router.get("/files/{filename}/info")
async def get_file_info(filename: str):
    """
    Obține informații despre un fișier specific
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

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
        raise HTTPException(status_code=500, detail=f"Eroare la citirea informațiilor: {str(e)}")


@router.get("/ml/status")
async def get_ml_status():
    """
    Verifică statusul sistemului ML
    """
    if not ML_AVAILABLE:
        return {
            "ml_available": False,
            "error": "Dependențele ML nu sunt instalate",
            "required_packages": ["torch", "monai", "nibabel"]
        }

    try:
        wrapper = get_model_wrapper()
        model_info = wrapper.get_model_info()

        return {
            "ml_available": True,
            "model_info": model_info,
            "status": "ready" if wrapper.is_loaded else "not_loaded"
        }

    except Exception as e:
        return {
            "ml_available": True,
            "error": str(e),
            "status": "error"
        }


@router.post("/ml/load-model")
async def load_model_endpoint():
    """
    Încarcă modelul ML în memorie
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        print("[API] Încercare încărcare model...")
        success = ensure_model_loaded()

        if success:
            wrapper = get_model_wrapper()
            model_info = wrapper.get_model_info()

            print("[API] Model încărcat cu succes!")
            return {
                "message": "Model încărcat cu succes",
                "model_info": model_info
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Încărcarea modelului a eșuat"
            )

    except Exception as e:
        print(f"[API] Eroare la încărcarea modelului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la încărcarea modelului: {str(e)}"
        )


@router.get("/preprocess/status")
async def get_preprocess_status():
    """
    Verifică statusul sistemului de preprocesare
    """
    if not SERVICE_AVAILABLE:
        return {
            "preprocess_available": False,
            "error": "Dependențele pentru preprocesare nu sunt instalate",
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


@router.get("/preprocess/folders")
async def get_valid_folders():
    """
    Găsește folderele valide pentru segmentare
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
            detail=f"Eroare la căutarea folderelor: {str(e)}"
        )


@router.post("/preprocess/folder/{folder_name}")
async def preprocess_folder_endpoint(folder_name: str, save_data: bool = True):
    """
    Preprocesează un folder specific pentru inferență și salvează datele
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
                detail=f"Folderul {folder_name} nu există"
            )

        print(f"[API] Încercare preprocesare folder: {folder_name}")

        # Preprocesează folderul
        result = preprocess_folder_simple(folder_path)

        # Debug: afișează cheile disponibile
        print(f"[DEBUG] Chei disponibile în result: {list(result.keys())}")

        # Salvează datele preprocesate dacă e solicitat
        saved_path = None
        if save_data:
            import torch

            # Încearcă să găsească tensorul preprocesат sub diferite chei posibile
            preprocessed_tensor = None
            # FIXED: Added "image_tensor" to the possible keys
            possible_keys = ["image_tensor", "preprocessed_data", "data", "tensor", "processed_tensor", "output"]

            for key in possible_keys:
                if key in result:
                    preprocessed_tensor = result[key]
                    print(f"[DEBUG] Tensorul găsit sub cheia: {key}")
                    break

            if preprocessed_tensor is None:
                # Dacă nu găsește tensorul, afișează toate valorile pentru debugging
                print(f"[ERROR] Nu s-a găsit tensorul preprocesат. Result keys: {list(result.keys())}")
                for key, value in result.items():
                    print(f"[DEBUG] {key}: {type(value)} - {value if not hasattr(value, 'shape') else f'shape: {value.shape}'}")
                raise HTTPException(
                    status_code=500,
                    detail="Tensorul preprocesат nu a fost găsit în rezultat"
                )

            # Convert MetaTensor to regular tensor if needed
            if hasattr(preprocessed_tensor, 'as_tensor'):
                preprocessed_tensor = preprocessed_tensor.as_tensor()
            elif not isinstance(preprocessed_tensor, torch.Tensor):
                preprocessed_tensor = torch.tensor(preprocessed_tensor)

            # Creează directorul pentru date preprocesate
            preprocessed_dir = TEMP_PREPROCESSING_DIR
            preprocessed_dir.mkdir(exist_ok=True)

            # Salvează tensorul
            output_path = preprocessed_dir / f"{folder_name}_preprocessed.pt"
            torch.save(preprocessed_tensor, output_path)
            saved_path = str(output_path)

            print(f"[API] Date preprocesate salvate în: {saved_path}")

        # Extrage informații pentru răspuns (fără tensorul mare)
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

        print(f"[API] Preprocesare completă pentru {folder_name}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Eroare la preprocesarea folderului {folder_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la preprocesare: {str(e)}"
        )


# Adaugă acest endpoint în routerul tău
@router.get("/preprocess/visualize/{filename}")
async def visualize_preprocessed_data(filename: str,
                                      slice_axis: str = "axial",
                                      slice_index: int = None,
                                      modality: str = "all"):
    """
    Vizualizează datele preprocesate salvate

    Args:
        filename: Numele fișierului .pt
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
                detail=f"Fișierul preprocesат {filename} nu există"
            )

        print(f"[VISUALIZE] Încarcă și vizualizează: {filename}")

        # Încarcă tensorul
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            tensor = data['image_tensor']
            metadata = data.get('metadata', {})
        else:
            tensor = data
            metadata = {}

        # Convertește la numpy pentru matplotlib
        if hasattr(tensor, 'numpy'):
            array = tensor.numpy()
        else:
            array = np.array(tensor)

        print(f"[VISUALIZE] Shape tensor: {array.shape}")

        # Verifică dimensiunile [4, H, W, D]
        if len(array.shape) != 4 or array.shape[0] != 4:
            raise HTTPException(
                status_code=400,
                detail=f"Format tensor neașteptat: {array.shape}. Se așteaptă [4, H, W, D]"
            )

        channels, height, width, depth = array.shape
        modality_names = ["t1n", "t1c", "t2w", "t2f"]

        # Determină indexul slice-ului
        axis_mapping = {
            "axial": 2,  # slice pe axa Z (depth)
            "coronal": 1,  # slice pe axa Y (height)
            "sagital": 0  # slice pe axa X (width)
        }

        if slice_axis not in axis_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Axă invalidă: {slice_axis}. Opțiuni: {list(axis_mapping.keys())}"
            )

        axis_idx = axis_mapping[slice_axis]
        max_slice = array.shape[axis_idx + 1]  # +1 pentru că primul index e channel-ul

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

        # Generează vizualizarea
        if modality == "all":
            # Creează o figură cu toate modalitățile
            fig, axes = plt.subplots(2, 2, figsize=(12, 12))
            fig.suptitle(f'{filename} - {slice_axis.title()} Slice #{slice_index}', fontsize=16)

            for i, (ax, mod_name) in enumerate(zip(axes.flat, modality_names)):
                im = ax.imshow(slice_data[i], cmap='gray', interpolation='nearest')
                ax.set_title(f'{mod_name.upper()}')
                ax.axis('off')
                plt.colorbar(im, ax=ax, shrink=0.8)

            plt.tight_layout()

        else:
            # Vizualizează o singură modalitate
            if modality not in modality_names:
                raise HTTPException(
                    status_code=400,
                    detail=f"Modalitate invalidă: {modality}. Opțiuni: {modality_names}"
                )

            mod_idx = modality_names.index(modality)

            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
            im = ax.imshow(slice_data[mod_idx], cmap='gray', interpolation='nearest')
            ax.set_title(f'{filename} - {modality.upper()} - {slice_axis.title()} Slice #{slice_index}')
            ax.axis('off')
            plt.colorbar(im, ax=ax)

        # Convertește figura în base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        # Calculează statistici pentru slice
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
            "message": "Vizualizare generată cu succes",
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


@router.get("/preprocess/slice-info/{filename}")
async def get_slice_info(filename: str):
    """
    Obține informații despre dimensiunile tensorului pentru navigare
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
                detail=f"Fișierul preprocesат {filename} nu există"
            )

        # Încarcă doar header-ul pentru informații rapide
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
                detail=f"Format tensor neașteptat: {shape}"
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
            detail=f"Eroare la obținerea informațiilor: {str(e)}"
        )


@router.get("/preprocess/saved")
async def get_preprocessed_files():
    """
    Listează fișierele preprocesate salvate
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
            detail=f"Eroare la listarea fișierelor preprocesate: {str(e)}"
        )

@router.get("/preprocess/load/{filename}")
async def load_preprocessed_data(filename: str):
    """
    Încarcă date preprocesate salvate
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
                detail=f"Fișierul preprocesат {filename} nu există"
            )

        # Încarcă tensorul
        data = torch.load(file_path)

        return {
            "message": f"Date preprocesate încărcate cu succes",
            "filename": filename,
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "device": str(data.device)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la încărcarea datelor: {str(e)}"
        )


# -*- coding: utf-8 -*-
"""
API Endpoints pentru serviciul de inferență
Adaugă acestea în endpoints.py
"""

# Adaugă la începutul fișierului endpoints.py, în secțiunea de import-uri:
from pathlib import Path

# Import servicii inferență (după celelalte import-uri services):
try:
    from src.services import (
        get_inference_service,
        run_inference_on_folder,
        run_inference_on_preprocessed,
        get_postprocessor
    )

    INFERENCE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Inference dependencies nu sunt disponibile: {e}")
    INFERENCE_AVAILABLE = False


# Adaugă aceste endpoint-uri în router:

@router.get("/inference/status")
async def get_inference_status():
    """
    Verifică statusul sistemului de inferență
    """
    if not INFERENCE_AVAILABLE:
        return {
            "inference_available": False,
            "error": "Dependențele pentru inferență nu sunt instalate",
            "required_services": ["preprocess", "ml", "postprocess"]
        }

    try:
        service = get_inference_service()

        # Verifică toate componentele
        preprocessor_info = service.preprocessor.get_preprocessing_info()
        model_info = service.model_wrapper.get_model_info()
        memory_info = service.model_wrapper.get_memory_usage()

        return {
            "inference_available": True,
            "components": {
                "preprocessor": {
                    "initialized": preprocessor_info["is_initialized"],
                    "monai_available": preprocessor_info["monai_available"]
                },
                "model": {
                    "loaded": model_info["is_loaded"],
                    "device": model_info["device"],
                    "parameters": model_info.get("total_parameters", 0)
                },
                "postprocessor": {
                    "initialized": True
                }
            },
            "memory_usage": memory_info,
            "status": "ready" if model_info["is_loaded"] else "model_not_loaded"
        }

    except Exception as e:
        return {
            "inference_available": True,
            "error": str(e),
            "status": "error"
        }


@router.post("/inference/folder/{folder_name}")
async def run_inference_on_folder_endpoint(
        folder_name: str,
        save_result: bool = True,
        output_filename: str = None
):
    """
    Rulează inferența completă pe un folder cu modalități
    Pipeline: preprocess -> inference -> postprocess -> save
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferență nu este disponibil"
        )

    try:
        folder_path = UPLOAD_DIR / folder_name

        if not folder_path.exists() or not folder_path.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Folderul {folder_name} nu există"
            )

        print(f"[INFERENCE API] Start pipeline pentru folder: {folder_name}")

        # Rulează pipeline-ul complet
        result = run_inference_on_folder(folder_path, save_result)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferența a eșuat: {result.get('error', 'Eroare necunoscută')}"
            )

        # Pregătește răspunsul (fără array-ul mare)
        response_data = {
            "message": f"Inferență completă pentru {folder_name}",
            "folder_name": result["folder_name"],
            "timing": result["timing"],
            "segmentation_info": {
                "shape": list(result["segmentation"]["shape"]),
                "classes_found": result["segmentation"]["classes_found"],
                "class_counts": result["segmentation"]["class_counts"],
                "total_segmented_voxels": result["segmentation"]["total_segmented_voxels"]
            },
            "saved_file": result["saved_path"],
            "preprocessing_config": result["preprocessing_config"]
        }

        # Redenumește fișierul dacă este specificat
        if save_result and result["saved_path"] and output_filename:
            try:
                old_path = Path(result["saved_path"])
                new_path = old_path.parent / output_filename
                old_path.rename(new_path)
                response_data["saved_file"] = str(new_path)
                print(f"[INFERENCE API] Fișier redenumit: {output_filename}")
            except Exception as e:
                print(f"[WARNING] Nu s-a putut redenumi fișierul: {e}")

        print(f"[INFERENCE API] Inferență completă în {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare neașteptată: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare internă la inferență: {str(e)}"
        )


@router.post("/inference/preprocessed/{filename}")
async def run_inference_on_preprocessed_endpoint(filename: str):
    """
    Rulează inferența pe date preprocesate salvate
    Pipeline: load -> inference -> postprocess
    """
    if not INFERENCE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul de inferență nu este disponibil"
        )

    try:
        import torch

        preprocessed_dir = TEMP_PREPROCESSING_DIR
        file_path = preprocessed_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fișierul preprocesат {filename} nu există"
            )

        print(f"[INFERENCE API] Încarcă și procesează: {filename}")

        # Încarcă tensorul preprocesат
        data = torch.load(file_path, map_location='cpu')

        if isinstance(data, dict) and 'image_tensor' in data:
            preprocessed_tensor = data['image_tensor']
            folder_name = data.get('metadata', {}).get('folder_name', filename.replace('.pt', ''))
        else:
            preprocessed_tensor = data
            folder_name = filename.replace('.pt', '')

        # Verifică shape-ul
        expected_shape = (4, 128, 128, 128)  # (C, H, W, D)
        if preprocessed_tensor.shape != expected_shape:
            raise HTTPException(
                status_code=400,
                detail=f"Shape tensor invalid: {preprocessed_tensor.shape}. Se așteaptă: {expected_shape}"
            )

        # Rulează inferența
        result = run_inference_on_preprocessed(preprocessed_tensor, folder_name)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Inferența a eșuat: {result.get('error', 'Eroare necunoscută')}"
            )

        response_data = {
            "message": f"Inferență completă pe date preprocesate",
            "source_file": filename,
            "folder_name": result["folder_name"],
            "timing": result["timing"],
            "segmentation_info": {
                "shape": list(result["segmentation"]["shape"]),
                "classes_found": result["segmentation"]["classes_found"],
                "class_counts": result["segmentation"]["class_counts"]
            }
        }

        print(f"[INFERENCE API] Inferență pe {filename} completă în {result['timing']['total_time']:.2f}s")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la inferența pe preprocesate: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la inferență: {str(e)}"
        )


@router.get("/inference/results")
async def get_inference_results():
    """
    Listează rezultatele de inferență salvate
    """
    try:
        results_dir = Path("results")

        if not results_dir.exists():
            return {
                "inference_results": [],
                "count": 0,
                "results_dir": str(results_dir)
            }

        results = []
        # Caută fișiere cu pattern *-seg.nii.gz
        for result_path in results_dir.glob("*-seg.nii.gz"):
            stat = result_path.stat()

            # Extrage numele folderului din nume fișier (elimină -seg.nii.gz)
            folder_name = result_path.name.replace('-seg.nii.gz', '')

            results.append({
                "filename": result_path.name,
                "folder_name": folder_name,
                "full_path": str(result_path),
                "size_mb": get_file_size_mb(stat.st_size),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            })

        # Sortează după data creării
        results.sort(key=lambda x: x["created"], reverse=True)

        return {
            "inference_results": results,
            "count": len(results),
            "results_dir": str(results_dir)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la listarea rezultatelor: {str(e)}"
        )


@router.get("/inference/results/{folder_name}/download")
async def download_inference_result(folder_name: str):
    """
    Descarcă rezultatul de inferență pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu există"
            )

        print(f"[INFERENCE API] Descărcare rezultat: {folder_name}")

        return FileResponse(
            path=str(result_path),
            media_type="application/gzip",
            filename=f"{folder_name}-seg.nii.gz",
            headers={"Content-Disposition": f"attachment; filename={folder_name}-seg.nii.gz"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la descărcarea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descărcare: {str(e)}"
        )


@router.delete("/inference/results/{folder_name}")
async def delete_inference_result(folder_name: str):
    """
    Șterge rezultatul de inferență pentru un folder
    """
    try:
        result_path = Path("results") / f"{folder_name}-seg.nii.gz"

        if not result_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Rezultatul pentru {folder_name} nu există"
            )

        file_size = result_path.stat().st_size
        result_path.unlink()

        print(f"[INFERENCE API] Rezultat șters: {folder_name}")

        return {
            "message": f"Rezultatul pentru {folder_name} a fost șters",
            "deleted_file": result_path.name,
            "size_freed_mb": get_file_size_mb(file_size)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INFERENCE API] Eroare la ștergerea rezultatului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la ștergere: {str(e)}"
        )




@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Descarcă un fișier (returnează fișierul direct în browser)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

    try:
        print(f"[INFO] Descărcare fișier: {filename}")

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
        print(f"[ERROR] Eroare la descărcarea fișierului {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")


@router.get("/files/{filename}/download")
async def download_file_attachment(filename: str):
    """
    Descarcă un fișier ca attachment (forțează salvarea)
    """
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fișierul nu există")

    try:
        print(f"[INFO] Descărcare attachment: {filename}")

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
        print(f"[ERROR] Eroare la descărcarea attachment {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Eroare la descărcare: {str(e)}")