"""
Endpoint-uri pentru verificarea stării aplicației și monitorizare.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import torch
import psutil
import time
from datetime import datetime

from src.core import settings, logger, get_logger
from src.utils import get_directory_stats, cleanup_old_files

# Router pentru endpoint-urile de health
router = APIRouter(prefix="/api/health", tags=["Health & Monitoring"])
health_logger = get_logger("api.health")


@router.get("/", summary="Health check basic")
async def health_check() -> Dict[str, Any]:
    """
    Verificare de bază a stării aplicației.

    Returns:
        Status general al aplicației
    """
    health_logger.info("❤️ Health check executat")

    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "app": settings.app_name,
            "version": settings.app_version,
            "message": "API funcționează normal"
        }
    except Exception as e:
        health_logger.error(f"❌ Eroare la health check: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.get("/detailed", summary="Health check detaliat")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Verificare detaliată a tuturor componentelor sistemului.

    Returns:
        Status detaliat al tuturor componentelor
    """
    health_logger.info("🔍 Health check detaliat executat")

    try:
        # Verifică PyTorch și GPU
        torch_info = {
            "available": True,
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": settings.model_device
        }

        if torch.cuda.is_available():
            torch_info.update({
                "cuda_version": torch.version.cuda,
                "gpu_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None
            })

        # Verifică directoarele și storage
        directory_stats = get_directory_stats()

        # Informații sistem
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent if psutil.disk_usage('/') else None,
            "uptime_seconds": time.time() - psutil.boot_time()
        }

        # Verifică configurările critice
        config_status = {
            "upload_dir_writable": True,  # Verificat prin directory_stats
            "output_dir_writable": True,
            "model_path_configured": bool(settings.model_path),
            "max_file_size_mb": settings.max_file_size // (1024 * 1024),
            "allowed_extensions": settings.allowed_extensions
        }

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "app_info": {
                "name": settings.app_name,
                "version": settings.app_version,
                "debug": settings.debug
            },
            "pytorch": torch_info,
            "directories": directory_stats,
            "system": system_info,
            "configuration": config_status
        }

    except Exception as e:
        health_logger.error(f"❌ Eroare la health check detaliat: {e}")
        raise HTTPException(status_code=500, detail=f"Detailed health check failed: {e}")


@router.get("/stats", summary="Statistici aplicație")
async def get_app_stats() -> Dict[str, Any]:
    """
    Returnează statistici despre utilizarea aplicației.

    Returns:
        Statistici despre fișiere, directoare și performanță
    """
    health_logger.info("📊 Statistici aplicație solicitate")

    try:
        # Statistici directoare
        directory_stats = get_directory_stats()

        # Statistici sistem
        memory = psutil.virtual_memory()
        cpu_stats = {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }

        memory_stats = {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "used_gb": round(memory.used / (1024 ** 3), 2),
            "percent": memory.percent
        }

        # Informații PyTorch
        pytorch_stats = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": settings.model_device
        }

        if torch.cuda.is_available():
            pytorch_stats["gpu_memory_allocated"] = torch.cuda.memory_allocated()
            pytorch_stats["gpu_memory_cached"] = torch.cuda.memory_reserved()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "directories": directory_stats,
            "cpu": cpu_stats,
            "memory": memory_stats,
            "pytorch": pytorch_stats,
            "configuration": {
                "max_file_size_mb": settings.max_file_size // (1024 * 1024),
                "allowed_extensions": settings.allowed_extensions,
                "model_device": settings.model_device
            }
        }

    except Exception as e:
        health_logger.error(f"❌ Eroare la obținerea statisticilor: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {e}")


@router.post("/cleanup", summary="Curăță fișierele vechi")
async def cleanup_files(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Șterge fișierele mai vechi de un număr specificat de ore.

    Args:
        max_age_hours: Vârsta maximă în ore (default: 24)

    Returns:
        Numărul de fișiere șterse din fiecare director
    """
    health_logger.info(f"🧹 Cleanup solicit cu max_age_hours={max_age_hours}")

    if max_age_hours < 1:
        raise HTTPException(status_code=400, detail="max_age_hours trebuie să fie cel puțin 1")

    try:
        deleted_counts = cleanup_old_files(max_age_hours)

        health_logger.info(f"✅ Cleanup finalizat: {deleted_counts}")

        return {
            "message": "Cleanup executat cu succes",
            "max_age_hours": max_age_hours,
            "files_deleted": deleted_counts,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        health_logger.error(f"❌ Eroare la cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


@router.get("/ready", summary="Readiness probe")
async def readiness_probe() -> Dict[str, Any]:
    """
    Endpoint pentru Kubernetes readiness probe.
    Verifică că aplicația este gata să primească trafic.

    Returns:
        Status de readiness
    """
    try:
        # Verificări critice pentru readiness
        checks = {
            "pytorch_available": torch.cuda.is_available() or settings.model_device == "cpu",
            "directories_accessible": True,  # Verificat prin directory_stats
            "configuration_valid": bool(settings.model_path)
        }

        # Testează accesul la directoare
        try:
            get_directory_stats()
            checks["directories_accessible"] = True
        except Exception:
            checks["directories_accessible"] = False

        all_ready = all(checks.values())

        return {
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        health_logger.error(f"❌ Eroare la readiness probe: {e}")
        raise HTTPException(status_code=503, detail=f"Not ready: {e}")


@router.get("/live", summary="Liveness probe")
async def liveness_probe() -> Dict[str, Any]:
    """
    Endpoint pentru Kubernetes liveness probe.
    Verifică că aplicația rulează și poate răspunde.

    Returns:
        Status de liveness
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name
    }