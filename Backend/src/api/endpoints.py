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
            possible_keys = ["preprocessed_data", "data", "tensor", "processed_tensor", "output"]

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