from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import-uri de bază (fără API routere pentru moment)
try:
    from src.core import settings, logger, log_processing_step

    core_loaded = True
except Exception as e:
    print(f"❌ Core import error: {e}")
    core_loaded = False


    # Fallback basic
    class MockSettings:
        app_name = "Pediatric Segmentation API"
        app_version = "1.0.0"
        debug = True
        cors_origins = ["*"]
        cors_credentials = True
        cors_methods = ["*"]
        cors_headers = ["*"]


    settings = MockSettings()

try:
    from src.utils import get_directory_stats, file_manager

    utils_loaded = True
except Exception as e:
    print(f"❌ Utils import error: {e}")
    utils_loaded = False

# Configurează aplicația FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="API pentru segmentarea pediatrica a imaginilor medicale NIfTI"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


@app.on_event("startup")
async def startup_event():
    """Eveniment la pornirea aplicației."""
    if core_loaded:
        logger.info(f"🚀 {settings.app_name} v{settings.app_version} porneste...")
        log_processing_step("startup")
    else:
        print("🚀 API porneste (core module cu probleme)")


@app.get("/")
async def root():
    """Endpoint principal cu diagnostice."""
    return {
        "message": "Pediatric Segmentation API",
        "status": "running",
        "modules": {
            "core": "✅ Loaded" if core_loaded else "❌ Failed",
            "utils": "✅ Loaded" if utils_loaded else "❌ Failed"
        },
        "endpoints_available": [
            "GET /",
            "GET /health",
            "GET /test-core",
            "GET /test-utils"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check simplu."""
    if core_loaded:
        logger.info("❤️ Health check executat")

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "modules_loaded": {
            "core": core_loaded,
            "utils": utils_loaded
        }
    }


@app.get("/test-core")
async def test_core():
    """Testează modulul core."""
    if not core_loaded:
        return {"error": "Core module nu s-a incarcat"}

    try:
        return {
            "core_status": "✅ Functional",
            "settings": {
                "app_name": settings.app_name,
                "debug": settings.debug,
                "upload_dir": getattr(settings, 'upload_dir', 'N/A'),
                "model_device": getattr(settings, 'model_device', 'N/A')
            },
            "logger": "✅ Functional"
        }
    except Exception as e:
        return {"error": f"Core test failed: {e}"}


@app.get("/test-utils")
async def test_utils():
    """Testează modulul utils."""
    if not utils_loaded:
        return {"error": "Utils module nu s-a incarcat"}

    try:
        stats = get_directory_stats()
        validation = file_manager.validate_file_upload("test.nii.gz", 50000000)

        return {
            "utils_status": "✅ Functional",
            "directory_stats": stats,
            "file_validation_test": validation
        }
    except Exception as e:
        return {"error": f"Utils test failed: {e}"}


@app.get("/test-torch")
async def test_torch():
    """Testează PyTorch."""
    try:
        import torch
        return {
            "torch_status": "✅ Disponibil",
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
    except Exception as e:
        return {"error": f"PyTorch test failed: {e}"}


@app.get("/debug")
async def debug_info():
    """Informații de debug pentru toate modulele."""
    import sys
    from pathlib import Path

    debug_info = {
        "python_version": sys.version,
        "working_directory": str(Path.cwd()),
        "python_path": sys.path[:3],  # Primele 3 pentru brevitate
        "modules_imported": {
            "core": core_loaded,
            "utils": utils_loaded
        }
    }

    # Încearcă să importe fiecare dependență
    dependencies = ['fastapi', 'torch', 'nibabel', 'numpy', 'pydantic_settings']
    dep_status = {}

    for dep in dependencies:
        try:
            __import__(dep)
            dep_status[dep] = "✅ OK"
        except Exception as e:
            dep_status[dep] = f"❌ {str(e)[:50]}..."

    debug_info["dependencies"] = dep_status

    return debug_info