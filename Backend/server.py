"""
Backend API Server Module
Menangani HTTP API endpoint, autentikasi API Key, dan koneksi CORS untuk Frontend (Hugging Face).
"""
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Security, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pipeline

# ==============================================================================
# ENVIRONMENT & SERVER CONFIGURATION (NETWORK ENGINEER)
# ==============================================================================
DEFAULT_API_KEY = os.getenv("LOCAL_API_KEY", "sk-local-gpu-hybrid-2026")
PORT = int(os.getenv("PORT", 8000))

# Registered API Keys store
VALID_API_KEYS: Dict[str, Dict[str, Any]] = {
    DEFAULT_API_KEY: {
        "device_name": "default-local-key",
        "created_at": datetime.now().isoformat()
    }
}

app = FastAPI(title="D-Massiv ImageGen Hybrid API")

# Izinkan akses dari Frontend di Hugging Face
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# AUTH (NETWORK ENGINEER)
# ==============================================================================
def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> str:
    """Verifikasi Custom API Key dari Header X-API-Key atau Authorization Bearer"""
    token = x_api_key
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token or token not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="401 Unauthorized: Invalid or missing API Key"
        )
    return token


# ==============================================================================
# REQUEST MODELS & ENDPOINTS (NETWORK ENGINEER)
# ==============================================================================
class ApiKeyRequest(BaseModel):
    device_name: str = "remote-client"


@app.get("/")
def root():
    return {
        "status": "ok",
        "current_model": pipeline.current_model_key or None,
        "model_loading": pipeline.model_loading,
    }


@app.post("/api/key")
def generate_api_key(request: ApiKeyRequest):
    """Menghasilkan Custom API Key baru untuk client."""
    new_key = f"sk-local-{secrets.token_urlsafe(16)}"
    VALID_API_KEYS[new_key] = {
        "device_name": request.device_name,
        "created_at": datetime.now().isoformat()
    }
    return {
        "success": True,
        "api_key": new_key,
        "message": f"API Key created for {request.device_name}"
    }


# ==============================================================================
# TODO: BAGIAN BACKEND ENGINEER
# Tambahkan endpoint /api/status, /api/models, /api/switch-model, /api/generate di sini.
# Gunakan `api_key: str = Security(verify_api_key)` pada endpoint yang butuh autentikasi.
# ==============================================================================


if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on http://0.0.0.0:{PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)