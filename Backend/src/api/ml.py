# -*- coding: utf-8 -*-
"""
API Endpoints pentru sistemul ML
"""
from fastapi import APIRouter, HTTPException

# Import ML pentru test endpoints
try:
    from src.ml import get_model_wrapper, ensure_model_loaded

    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] ML dependencies nu sunt disponibile: {e}")
    ML_AVAILABLE = False

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get("/status")
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


@router.post("/load-model")
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


@router.post("/unload-model")
async def unload_model_endpoint():
    """
    Descarcă modelul din memorie pentru a elibera resurse
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        from src.ml import unload_global_model

        print("[API] Încercare descărcare model...")
        success = unload_global_model()

        if success:
            print("[API] Model descărcat cu succes!")
            return {
                "message": "Model descărcat cu succes",
                "memory_freed": True
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Descărcarea modelului a eșuat"
            )

    except Exception as e:
        print(f"[API] Eroare la descărcarea modelului: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la descărcarea modelului: {str(e)}"
        )


@router.get("/memory-usage")
async def get_memory_usage():
    """
    Verifică utilizarea memoriei pentru sistemul ML
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        from src.ml import get_global_memory_usage

        memory_info = get_global_memory_usage()

        return {
            "memory_usage": memory_info,
            "timestamp": "current"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la obținerea informațiilor despre memorie: {str(e)}"
        )


@router.post("/cleanup")
async def force_cleanup():
    """
    Forțează cleanup complet al tuturor resurselor ML
    """
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistemul ML nu este disponibil"
        )

    try:
        from src.ml import force_global_cleanup

        print("[API] Cleanup forțat al resurselor ML...")
        force_global_cleanup()

        print("[API] Cleanup complet!")
        return {
            "message": "Cleanup forțat completat cu succes",
            "resources_cleaned": True
        }

    except Exception as e:
        print(f"[API] Eroare la cleanup forțat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la cleanup: {str(e)}"
        )