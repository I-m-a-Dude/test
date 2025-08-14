"""
Endpoint-uri pentru upload și procesare a fișierelor NIfTI.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import uuid
from datetime import datetime
import traceback

from src.core import settings, logger, get_logger, log_processing_step
from src.utils import (
    validate_upload,
    save_uploaded_file,
    file_manager,
    validate_nifti,
    get_nifti_info
)

# Router pentru endpoint-urile de upload
router = APIRouter(prefix="/api/upload", tags=["File Upload & Processing"])
upload_logger = get_logger("api.upload")

# Storage temporar pentru task-uri în background (în producție ar fi Redis/DB)
processing_tasks = {}


class ProcessingStatus:
    """Clasa pentru tracking status procesare."""

    def __init__(self, task_id: str, filename: str):
        self.task_id = task_id
        self.filename = filename
        self.status = "queued"  # queued, processing, completed, failed
        self.progress = 0
        self.message = "Task în coadă"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.result_file = None
        self.error_message = None
        self.processing_time = None

    def update(self, status: str, progress: int = None, message: str = None,
               result_file: str = None, error: str = None):
        """Actualizează statusul task-ului."""
        self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        if result_file:
            self.result_file = result_file
        if error:
            self.error_message = error
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convertește la dicționar pentru API response."""
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result_file": self.result_file,
            "error_message": self.error_message,
            "processing_time_seconds": self.processing_time
        }


@router.post("/validate", summary="Validează fișier înainte de upload")
async def validate_file(
        filename: str,
        file_size_mb: float,
        content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validează un fișier înainte de upload efectiv.

    Args:
        filename: Numele fișierului
        file_size_mb: Dimensiunea în MB
        content_type: MIME type (opțional)

    Returns:
        Rezultatul validării
    """
    upload_logger.info(f"🔍 Validare fișier: {filename} ({file_size_mb}MB)")

    try:
        file_size_bytes = int(file_size_mb * 1024 * 1024)

        validation_result = validate_upload(filename, file_size_bytes, content_type)

        # Adaugă informații suplimentare
        validation_result["unique_filename"] = file_manager.generate_unique_filename(filename)
        validation_result["estimated_processing_time"] = _estimate_processing_time(file_size_mb)

        if validation_result["valid"]:
            upload_logger.info(f"✅ Validare OK pentru {filename}")
        else:
            upload_logger.warning(f"⚠️ Validare eșuată pentru {filename}: {validation_result['errors']}")

        return validation_result

    except Exception as e:
        upload_logger.error(f"❌ Eroare la validarea {filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")


@router.post("/", summary="Upload și procesare fișier NIfTI")
async def upload_and_process(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        process_immediately: bool = True
) -> Dict[str, Any]:
    """
    Upload unui fișier NIfTI și opțional procesare imediată.

    Args:
        file: Fișierul uploadat
        process_immediately: Dacă să înceapă procesarea automat

    Returns:
        Informații despre upload și task ID pentru tracking
    """
    upload_logger.info(f"📤 Upload fișier: {file.filename} ({file.size} bytes)")

    try:
        # Validează fișierul
        validation_result = validate_upload(
            file.filename,
            file.size,
            file.content_type
        )

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Fișier invalid: {validation_result['errors']}"
            )

        # Citește conținutul fișierului
        file_content = await file.read()

        # Salvează fișierul
        saved_path = save_uploaded_file(file_content, file.filename)

        # Validează că e NIfTI valid
        if not validate_nifti(saved_path):
            # Șterge fișierul invalid
            saved_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="Fișierul nu este un NIfTI valid"
            )

        # Extrage informații NIfTI
        nifti_info = get_nifti_info(saved_path)

        # Creează task ID pentru tracking
        task_id = str(uuid.uuid4())
        processing_task = ProcessingStatus(task_id, file.filename)
        processing_tasks[task_id] = processing_task

        upload_logger.info(f"✅ Upload complet: {saved_path}")
        log_processing_step("file_uploaded", str(saved_path),
                            task_id=task_id, nifti_shape=nifti_info.get("shape"))

        response = {
            "message": "Fișier uploadat cu succes",
            "task_id": task_id,
            "filename": file.filename,
            "saved_path": str(saved_path),
            "file_size_mb": round(file.size / (1024 * 1024), 2),
            "nifti_info": nifti_info,
            "processing_status": processing_task.to_dict()
        }

        # Începe procesarea în background dacă e cerută
        if process_immediately:
            background_tasks.add_task(_process_nifti_async, task_id, saved_path)
            processing_task.update("processing", 10, "Procesare începută în background")
            response["message"] += " - procesarea a început"

        return response

    except HTTPException:
        raise
    except Exception as e:
        upload_logger.error(f"❌ Eroare la upload {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/status/{task_id}", summary="Verifică statusul procesării")
async def get_processing_status(task_id: str) -> Dict[str, Any]:
    """
    Verifică statusul unui task de procesare.

    Args:
        task_id: ID-ul task-ului

    Returns:
        Statusul curent al procesării
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task ID nu a fost găsit")

    task = processing_tasks[task_id]
    upload_logger.info(f"📊 Status task {task_id}: {task.status}")

    return {
        "task": task.to_dict(),
        "can_download": task.status == "completed" and task.result_file,
        "estimated_remaining_time": _estimate_remaining_time(task) if task.status == "processing" else None
    }


@router.get("/download/{task_id}", summary="Descarcă rezultatul procesării")
async def download_result(task_id: str) -> FileResponse:
    """
    Descarcă fișierul rezultat al procesării.

    Args:
        task_id: ID-ul task-ului

    Returns:
        Fișierul NIfTI procesat
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task ID nu a fost găsit")

    task = processing_tasks[task_id]

    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task nu este completat (status: {task.status})")

    if not task.result_file or not Path(task.result_file).exists():
        raise HTTPException(status_code=404, detail="Fișierul rezultat nu a fost găsit")

    upload_logger.info(f"📥 Download rezultat pentru task {task_id}")

    result_path = Path(task.result_file)
    return FileResponse(
        path=result_path,
        filename=f"segmented_{task.filename}",
        media_type="application/octet-stream"
    )


@router.delete("/task/{task_id}", summary="Șterge task și fișierele asociate")
async def delete_task(task_id: str) -> Dict[str, Any]:
    """
    Șterge un task și toate fișierele asociate.

    Args:
        task_id: ID-ul task-ului

    Returns:
        Confirmarea ștergerii
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task ID nu a fost găsit")

    task = processing_tasks[task_id]

    try:
        # Șterge fișierele asociate (input și output)
        files_deleted = 0

        # Găsește și șterge fișierul input
        upload_files = list(Path(settings.upload_dir).glob(f"*{task.filename.split('.')[0]}*"))
        for file_path in upload_files:
            if file_path.exists():
                file_path.unlink()
                files_deleted += 1

        # Șterge fișierul output dacă există
        if task.result_file and Path(task.result_file).exists():
            Path(task.result_file).unlink()
            files_deleted += 1

        # Șterge task-ul din memorie
        del processing_tasks[task_id]

        upload_logger.info(f"🗑️ Task {task_id} și {files_deleted} fișiere șterse")

        return {
            "message": "Task șters cu succes",
            "task_id": task_id,
            "files_deleted": files_deleted
        }

    except Exception as e:
        upload_logger.error(f"❌ Eroare la ștergerea task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")


@router.get("/tasks", summary="Listează toate task-urile")
async def list_tasks(status_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Listează toate task-urile cu opțiune de filtrare.

    Args:
        status_filter: Filtrează după status (opțional)

    Returns:
        Lista task-urilor
    """
    tasks = list(processing_tasks.values())

    if status_filter:
        tasks = [task for task in tasks if task.status == status_filter]

    return {
        "tasks": [task.to_dict() for task in tasks],
        "total_count": len(tasks),
        "status_filter": status_filter
    }


async def _process_nifti_async(task_id: str, input_path: Path):
    """
    Procesează un fișier NIfTI în background.
    PLACEHOLDER - va fi implementat când services vor fi gata.
    """
    task = processing_tasks[task_id]

    try:
        upload_logger.info(f"🔄 Începe procesarea task {task_id}")
        task.update("processing", 20, "Preprocesare...")

        # PLACEHOLDER: Aici vor fi apelate services
        # from src.services import preprocessing, inference, postprocessing

        await asyncio.sleep(2)  # Simulează preprocesarea
        task.update("processing", 50, "Inferență model...")

        await asyncio.sleep(3)  # Simulează inferența
        task.update("processing", 80, "Postprocesare...")

        await asyncio.sleep(1)  # Simulează postprocesarea

        # Simulează salvarea rezultatului
        output_path = file_manager.create_output_path(input_path.name)
        # Pentru moment, copiază fișierul input ca output
        import shutil
        shutil.copy2(input_path, output_path)

        processing_time = (datetime.utcnow() - task.created_at).total_seconds()
        task.processing_time = processing_time
        task.update("completed", 100, "Procesare completă", str(output_path))

        upload_logger.info(f"✅ Task {task_id} completat în {processing_time:.2f}s")
        log_processing_step("processing_completed", str(output_path),
                            task_id=task_id, processing_time=processing_time)

    except Exception as e:
        error_msg = f"Eroare procesare: {str(e)}"
        upload_logger.error(f"❌ Task {task_id} eșuat: {error_msg}")
        upload_logger.error(traceback.format_exc())
        task.update("failed", task.progress, error_msg, error=error_msg)


def _estimate_processing_time(file_size_mb: float) -> str:
    """Estimează timpul de procesare bazat pe dimensiunea fișierului."""
    # Estimare simplă: ~1 minut per 50MB
    estimated_minutes = max(1, int(file_size_mb / 50))
    return f"~{estimated_minutes} minute(s)"


def _estimate_remaining_time(task: ProcessingStatus) -> Optional[str]:
    """Estimează timpul rămas pentru un task în procesare."""
    if task.status != "processing" or task.progress <= 0:
        return None

    elapsed = (datetime.utcnow() - task.created_at).total_seconds()
    estimated_total = elapsed * (100 / task.progress)
    remaining = max(0, estimated_total - elapsed)

    if remaining < 60:
        return f"~{int(remaining)}s"
    else:
        return f"~{int(remaining / 60)}m"