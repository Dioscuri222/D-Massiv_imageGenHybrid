"""
Backend API Server Module
Menangani HTTP API endpoint, autentikasi API Key, dan koneksi CORS untuk Frontend (Hugging Face).
"""
import os
import io
import sys
import time
import base64
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List

# Set utf-8 encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Pastikan folder Backend ada di sys.path saat dijalankan dari root project
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI, HTTPException, Security, Header, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import torch
import pipeline

# ==============================================================================
# ENVIRONMENT & SERVER CONFIGURATION (NETWORK ENGINEER)
# ==============================================================================
DEFAULT_API_KEY = os.getenv("LOCAL_API_KEY", "sk-local-gpu-hybrid-2026")
PORT = int(os.getenv("PORT", 8000))
startup_time = time.time()

# Registered API Keys store
VALID_API_KEYS: Dict[str, Dict[str, Any]] = {
    DEFAULT_API_KEY: {
        "device_name": "default-local-key",
        "created_at": datetime.now().isoformat()
    }
}

app = FastAPI(
    title="D-Massiv ImageGen Hybrid API",
    description="Backend inferensi lokal berbasis GPU untuk WebUI Hugging Face Spaces — mendukung hot-swap model",
    version="2.0.0"
)

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
# REQUEST / RESPONSE MODELS (NETWORK & BACKEND ENGINEER)
# ==============================================================================
class ApiKeyRequest(BaseModel):
    device_name: str = "remote-client"


class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Prompt teks untuk pembuatan gambar")
    negative_prompt: str = Field("", description="Teks negatif prompt")
    steps: int = Field(20, ge=1, le=50, description="Jumlah langkah inferensi")
    cfg_scale: float = Field(7.0, ge=1.0, le=20.0, description="Guidance scale")
    width: int = Field(512, ge=256, le=1024, description="Lebar gambar")
    height: int = Field(512, ge=256, le=1024, description="Tinggi gambar")
    seed: Optional[int] = Field(None, description="Random seed untuk reproduksibilitas")


class SwitchModelRequest(BaseModel):
    model_key: str = Field(..., description="Key model dari registry (misal: 'sd-1.5', 'dreamshaper-8')")


# ==============================================================================
# STARTUP EVENT (BACKEND ENGINEER)
# ==============================================================================
@app.on_event("startup")
def load_initial_pipeline():
    """Load model default saat server pertama kali start."""
    print("🚀 Initializing Local Inference Engine v2.0...")
    print(f"🔑 Default API Key: {DEFAULT_API_KEY}")
    print(f"📁 Model cache directory: {pipeline.CACHE_DIR}")
    print(f"📋 Registered models: {len(pipeline.MODEL_REGISTRY)}")
    for key, info in pipeline.MODEL_REGISTRY.items():
        marker = " ← (default)" if key == pipeline.INITIAL_MODEL_KEY else ""
        print(f"   • {key}: {info['name']}{marker}")

    success = pipeline._load_pipeline(pipeline.INITIAL_MODEL_KEY)
    if not success:
        print("⚠️ Initial model load failed. Server is running but generation is unavailable.")
        print("   Use POST /api/switch-model to try loading a different model.")


# ==============================================================================
# ENDPOINTS (NETWORK & BACKEND ENGINEER)
# ==============================================================================
@app.get("/")
def root():
    return {
        "service": "Hybrid Image Generation - Local GPU Backend",
        "version": "2.0.0",
        "status": "online",
        "current_model": pipeline.current_model_key or "none",
        "model_loading": pipeline.model_loading,
        "uptime_seconds": round(time.time() - startup_time, 2),
        "docs_url": "/docs"
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


@app.get("/api/status")
def get_status(api_key: Optional[str] = None):
    """Cek kesehatan backend, ketersediaan GPU, status model, dan VRAM."""
    cuda_available = torch.cuda.is_available()

    vram_info = {}
    if cuda_available:
        try:
            allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
            reserved = torch.cuda.memory_reserved(0) / (1024 ** 3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            vram_info = {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                "total_gb": round(total, 2),
                "free_gb": round(total - allocated, 2),
            }
        except Exception:
            pass

    model_state = (
        "loading" if pipeline.model_loading
        else ("ready" if pipeline.pipe is not None else "unloaded")
    )

    return {
        "status": "healthy",
        "model_status": model_state,
        "current_model_key": pipeline.current_model_key,
        "model_id": pipeline.current_model_id,
        "device": "cuda" if cuda_available else "cpu",
        "gpu_available": cuda_available,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else "CPU (No CUDA)",
        "vram": vram_info,
        "active_api_keys": len(VALID_API_KEYS),
    }


@app.get("/api/models")
def list_models():
    """
    Daftar semua model yang tersedia di registry, beserta info mana yang sedang aktif.
    Endpoint ini bersifat publik (tanpa API key) agar mudah di-query.
    """
    models: List[Dict[str, Any]] = []
    for key, info in pipeline.MODEL_REGISTRY.items():
        models.append({
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "huggingface_id": info["id"],
            "max_resolution": info["max_resolution"],
            "recommended_steps": info["recommended_steps"],
            "vram_estimate_gb": info["vram_estimate_gb"],
            "is_active": (key == pipeline.current_model_key),
        })
    return {
        "models": models,
        "current_model_key": pipeline.current_model_key,
        "total": len(models),
    }


@app.post("/api/switch-model")
def switch_model(
    request: SwitchModelRequest,
    api_key: str = Security(verify_api_key),
):
    """
    Hot-swap model inferensi. Pipeline lama dibersihkan dari VRAM,
    lalu model baru dimuat dari cache (atau diunduh jika belum ada).
    """
    requested_key = request.model_key.strip().lower()

    # Validasi model key
    if requested_key not in pipeline.MODEL_REGISTRY:
        available = list(pipeline.MODEL_REGISTRY.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"Model key '{requested_key}' tidak ditemukan di registry.",
                "available_models": available,
                "hint": "Gunakan GET /api/models untuk melihat daftar lengkap.",
            }
        )

    # Cek apakah model yang diminta sudah aktif
    if requested_key == pipeline.current_model_key and pipeline.pipe is not None:
        model_info = pipeline.MODEL_REGISTRY[requested_key]
        return {
            "success": True,
            "message": f"Model '{model_info['name']}' sudah aktif, tidak perlu reload.",
            "model_key": requested_key,
            "model_id": model_info["id"],
            "was_reloaded": False,
        }

    # Cek apakah sedang loading model lain
    if pipeline.model_loading:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sedang dalam proses loading model lain. Tunggu hingga selesai."
        )

    # Thread-safe model loading menggunakan lock dari modul pipeline
    acquired = pipeline.model_load_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Proses switch model sedang berjalan. Tunggu hingga selesai."
        )

    try:
        t0 = time.time()
        model_info = pipeline.MODEL_REGISTRY[requested_key]

        success = pipeline._load_pipeline(requested_key)

        if success:
            elapsed = round(time.time() - t0, 2)

            vram_after = {}
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
                total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                vram_after = {
                    "allocated_gb": round(allocated, 2),
                    "total_gb": round(total, 2),
                    "free_gb": round(total - allocated, 2),
                }

            return {
                "success": True,
                "message": f"Model berhasil diganti ke '{model_info['name']}'.",
                "model_key": requested_key,
                "model_id": model_info["id"],
                "model_name": model_info["name"],
                "was_reloaded": True,
                "load_time_seconds": elapsed,
                "vram_after_load": vram_after,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": f"Gagal memuat model '{model_info['name']}'.",
                    "hint": "Periksa log konsol backend untuk detail error. "
                            "Kemungkinan VRAM tidak cukup atau model tidak tersedia.",
                }
            )
    finally:
        pipeline.model_load_lock.release()


@app.post("/api/generate")
def generate_image(
    request: GenerationRequest,
    api_key: str = Security(verify_api_key)
):
    """
    Endpoint utama inferensi gambar dengan GPU lokal.
    Mengembalikan gambar dalam format Base64 PNG beserta metrik latensi.
    """
    if pipeline.pipe is None:
        if pipeline.model_loading:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model sedang dalam proses loading. Tunggu beberapa saat lalu coba lagi."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tidak ada model aktif. Gunakan POST /api/switch-model untuk memuat model."
        )

    # Validasi dimensi (harus kelipatan 8)
    if request.width % 8 != 0 or request.height % 8 != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Width and Height must be multiples of 8."
        )

    # Validasi resolusi terhadap batas model aktif
    active_model_info = pipeline.MODEL_REGISTRY.get(pipeline.current_model_key, {})
    max_res = active_model_info.get("max_resolution", 768)
    if request.width > max_res or request.height > max_res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolusi melebihi batas model aktif ({max_res}x{max_res}). "
                   f"Kurangi ukuran gambar untuk menghindari CUDA OOM pada VRAM 4GB."
        )

    t0 = time.time()
    try:
        # Penanganan seed
        generator = None
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
        if request.seed is not None and request.seed >= 0:
            generator = torch.Generator(device_str).manual_seed(request.seed)

        # Proses inferensi pada GPU menggunakan pipeline.pipe
        with torch.inference_mode():
            result = pipeline.pipe(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt if request.negative_prompt else None,
                num_inference_steps=request.steps,
                guidance_scale=request.cfg_scale,
                width=request.width,
                height=request.height,
                generator=generator
            )
            image = result.images[0]

        # Konversi output gambar ke Base64 PNG
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        latency = round(time.time() - t0, 3)
        print(f"✨ [{pipeline.current_model_key}] Image generated in {latency}s "
              f"[{request.width}x{request.height}, steps={request.steps}] on {device_str}")

        return JSONResponse({
            "success": True,
            "image_base64": img_str,
            "latency_seconds": latency,
            "device": device_str,
            "model_key": pipeline.current_model_key,
            "model_name": active_model_info.get("name", "Unknown"),
            "resolution": f"{request.width}x{request.height}",
            "timestamp": datetime.now().isoformat()
        })

    except torch.cuda.OutOfMemoryError:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CUDA Out of Memory! Kurangi resolusi gambar (misal 512x512) atau jumlah steps."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on http://0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)