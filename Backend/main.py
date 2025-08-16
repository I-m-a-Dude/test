# -*- coding: utf-8 -*-
"""
MediView Backend - Entry Point
"""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configurări
from src.core.config import (
    APP_NAME, VERSION, DESCRIPTION,
    HOST, PORT, RELOAD,
    CORS_ORIGINS, UPLOAD_DIR, get_file_size_mb, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
)

# Import endpoint-uri
from src.api.endpoints import router

# Configurare encoding pentru Windows
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

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
    print(f" Dimensiune max fisier: {get_file_size_mb(MAX_FILE_SIZE)}")
    print(f" Extensii acceptate: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f" CORS origini: {', '.join(CORS_ORIGINS)}")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn

    print(f"Pornire server pe {HOST}:{PORT}")
    print(f"Reload mode: {RELOAD}")
    print("Ctrl+C pentru oprire")

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info"
    )