"""
Backend API Server Module
Menangani HTTP API endpoint dan koneksi CORS untuk Frontend (Hugging Face).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pipeline

app = FastAPI(title="D-Massiv ImageGen Hybrid API")

# Izinkan akses dari Frontend di Hugging Face
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "current_model": pipeline.current_model_key or None,
        "model_loading": pipeline.model_loading,
    }


# TODO: Tambahkan endpoint API (mis. /models, /switch-model, /generate) di sini


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
