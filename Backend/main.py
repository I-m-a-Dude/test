# -*- coding: utf-8 -*-
"""
MediView Backend - Entry Point
"""
import sys
import signal
import atexit
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurări
from src.core.config import (
    APP_NAME, VERSION, DESCRIPTION,
    HOST, PORT, RELOAD,
    CORS_ORIGINS, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
)

# Import endpoint-uri
from src.api import router

# Import ML pentru cleanup
try:
    from src.ml import force_global_cleanup

    ML_CLEANUP_AVAILABLE = True
except ImportError:
    ML_CLEANUP_AVAILABLE = False
    force_global_cleanup = None

# Configurare encoding pentru Windows
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


def cleanup_resources():
    """Funcție de cleanup la închiderea aplicației"""
    print("\n[SHUTDOWN] Cleanup resurse la închiderea aplicației...")

    if ML_CLEANUP_AVAILABLE and force_global_cleanup:
        try:
            force_global_cleanup()
            print("[SHUTDOWN] Cleanup ML completat")
        except Exception as e:
            print(f"[SHUTDOWN] Eroare la cleanup ML: {str(e)}")

    print("[SHUTDOWN] Aplikația s-a închis cu succes")


def signal_handler(signum, frame):
    """Handler pentru semnale de închidere"""
    print(f"\n[SHUTDOWN] Semnal primit: {signum}")
    cleanup_resources()
    sys.exit(0)


# Înregistrează cleanup-ul pentru diferite moduri de închidere
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Închidere normală

# Windows specific
if sys.platform.startswith('win'):
    try:
        signal.signal(signal.SIGBREAK, signal_handler)  # Ctrl+Break pe Windows
    except AttributeError:
        pass

# Creează aplicația FastAPI
app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description=DESCRIPTION
)

# Configurează CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adaugă endpoint-urile
app.include_router(router)


# Funcție de startup
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print(f" {APP_NAME} v{VERSION}")
    print("=" * 60)
    print(f" Director upload: {UPLOAD_DIR.absolute()}")
    print(f" Dimensiune max fișier: {get_file_size_mb(MAX_FILE_SIZE)}")
    print(f" Extensii acceptate: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f" CORS origini: {', '.join(CORS_ORIGINS)}")

    if ML_CLEANUP_AVAILABLE:
        print(" Sistem ML disponibil")
    else:
        print("  Sistem ML indisponibil")

    print("=" * 60)


# Funcție de shutdown
@app.on_event("shutdown")
async def shutdown_event():
    print("\n[FASTAPI SHUTDOWN] Oprirea aplicației FastAPI...")
    cleanup_resources()


if __name__ == "__main__":
    import uvicorn

    print(f"Pornire server pe {HOST}:{PORT}")
    print(f"Reload mode: {RELOAD}")
    print("Ctrl+C pentru oprire")

    try:
        uvicorn.run(
            "main:app",
            host=HOST,
            port=PORT,
            reload=RELOAD,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[MAIN] Oprire forțată prin Ctrl+C")
    except Exception as e:
        print(f"\n[MAIN] Eroare neașteptată: {str(e)}")
    finally:
        print("[MAIN] Cleanup final...")
        cleanup_resources()