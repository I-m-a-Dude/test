"""
API module pentru aplicația de segmentare pediatrică.

Acest modul conține toate endpoint-urile FastAPI organizate pe routere.
"""

from .health import router as health_router
from .upload import router as upload_router, processing_tasks, ProcessingStatus

__all__ = [
    # Routere FastAPI
    "health_router",
    "upload_router",

    # Clase și utilități pentru upload
    "processing_tasks",
    "ProcessingStatus",
]

# Versiunea modulului API
__version__ = "1.0.0"

# Informații despre API
API_INFO = {
    "title": "Pediatric Segmentation API",
    "description": "API pentru segmentarea pediatrica a imaginilor medicale NIfTI",
    "version": __version__,
    "endpoints": {
        "health": {
            "/api/health/": "Health check basic",
            "/api/health/detailed": "Health check detaliat",
            "/api/health/stats": "Statistici aplicatie",
            "/api/health/cleanup": "Curata fisierele vechi",
            "/api/health/ready": "Readiness probe pentru K8s",
            "/api/health/live": "Liveness probe pentru K8s"
        },
        "upload": {
            "/api/upload/validate": "Valideaza fisier inainte de upload",
            "/api/upload/": "Upload si procesare fisier NIfTI",
            "/api/upload/status/{task_id}": "Verifica statusul procesarii",
            "/api/upload/download/{task_id}": "Descarca rezultatul",
            "/api/upload/task/{task_id}": "Sterge task si fisiere",
            "/api/upload/tasks": "Listeaza toate task-urile"
        }
    }
}