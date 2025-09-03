# -*- coding: utf-8 -*-
"""
MediView Backend - Entry Point cu shutdown graceful fix
"""
import sys
import signal
import atexit
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurari
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

# Flag global pentru shutdown graceful
shutdown_event = threading.Event()


def cleanup_resources():
    """Functie de cleanup la inchiderea aplicatiei"""
    print("\n[SHUTDOWN] Cleanup resurse la inchiderea aplicatiei...")

    if ML_CLEANUP_AVAILABLE and force_global_cleanup:
        try:
            force_global_cleanup()
            print("[SHUTDOWN] Cleanup ML completat")
        except Exception as e:
            print(f"[SHUTDOWN] Eroare la cleanup ML: {str(e)}")

    print("[SHUTDOWN] Aplicatia s-a inchis cu succes")


def signal_handler(signum, frame):
    """Handler pentru semnale de inchidere - FIXED"""
    print(f"\n[SHUTDOWN] Semnal primit: {signum}")

    # Seteaza flag-ul pentru shutdown
    shutdown_event.set()

    # NU mai folosim sys.exit(0) - lasam uvicorn sa gestioneze shutdown-ul
    print("[SHUTDOWN] Shutdown graceful initiat...")


# Inregistreaza cleanup-ul pentru diferite moduri de inchidere
atexit.register(cleanup_resources)

# Inregistreaza signal handlers DOAR daca nu ruleaza in reload mode
if not RELOAD:
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # inchidere normala

    # Windows specific
    if sys.platform.startswith('win'):
        try:
            signal.signal(signal.SIGBREAK, signal_handler)  # Ctrl+Break pe Windows
        except AttributeError:
            pass

# Creeaza aplicatia FastAPI
app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description=DESCRIPTION
)

# Configureaza CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adauga endpoint-urile
app.include_router(router)


# Functie de startup
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print(f" {APP_NAME} v{VERSION}")
    print("=" * 60)
    print(f" Director upload: {UPLOAD_DIR.absolute()}")
    print(f" Dimensiune max fisier: {get_file_size_mb(MAX_FILE_SIZE)}")
    print(f" Extensii acceptate: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f" CORS origini: {', '.join(CORS_ORIGINS)}")

    if ML_CLEANUP_AVAILABLE:
        print(" Sistem ML disponibil")
    else:
        print(" Sistem ML indisponibil")

    print("=" * 60)


# Functie de shutdown - FIXED
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event pentru FastAPI - gestioneaza cleanup graceful"""
    print("\n[FASTAPI SHUTDOWN] Oprirea aplicatiei FastAPI...")

    # Cleanup resursele
    cleanup_resources()

    print("[FASTAPI SHUTDOWN] Shutdown complet")


if __name__ == "__main__":
    import uvicorn

    print(f"Pornire server pe {HOST}:{PORT}")
    print(f"Reload mode: {RELOAD}")

    if RELOAD:
        print("NOTA: Signal handlers dezactivati in reload mode")

    print("Ctrl+C pentru oprire")

    try:
        # Configurare uvicorn cu gestionare imbunatatita a signal-urilor
        config = uvicorn.Config(
            "main:app",
            host=HOST,
            port=PORT,
            reload=RELOAD,
            log_level="info",
            # Timeout mai mare pentru shutdown graceful
            timeout_graceful_shutdown=10
        )

        server = uvicorn.Server(config)
        server.run()

    except KeyboardInterrupt:
        print("\n[MAIN] Oprire prin Ctrl+C")
    except Exception as e:
        print(f"\n[MAIN] Eroare neasteptata: {str(e)}")
    finally:
        print("[MAIN] Cleanup final...")

        # Cleanup final doar daca nu s-a facut deja
        if not shutdown_event.is_set():
            cleanup_resources()