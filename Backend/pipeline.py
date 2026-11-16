"""
Model Pipeline Module (AI/ML Engineer)
Menangani manajemen memori VRAM, registry model, load/hot-swap Stable Diffusion,
serta eksekusi inferensi gambar.
"""
import os
import gc
import time
import threading
import torch
from PIL import Image
from typing import Optional, Dict, Any, List, Tuple
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

# ==============================================================================
# FOLDER MODEL CONFIGURATION
# ==============================================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_DIR = os.path.join(PROJECT_ROOT, "modelAI")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = CACHE_DIR
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ==============================================================================
# MODEL REGISTRY — Model-model yang aman untuk 4GB VRAM (RTX 2050)
# ==============================================================================
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "sd-1.5": {
        "id": "runwayml/stable-diffusion-v1-5",
        "name": "Stable Diffusion 1.5 (Base)",
        "description": "Model dasar SD 1.5 — general purpose, cepat, ringan.",
        "max_resolution": 768,
        "recommended_steps": 20,
        "vram_estimate_gb": 2.5,
    },
    "dreamshaper-8": {
        "id": "Lykon/dreamshaper-8",
        "name": "DreamShaper 8",
        "description": "Kualitas artistik tinggi, warna hidup, detail tajam. Cocok untuk art/illustration.",
        "max_resolution": 768,
        "recommended_steps": 25,
        "vram_estimate_gb": 2.5,
    },
    "realistic-vision-5.1": {
        "id": "SG161222/Realistic_Vision_V5.1_noVAE",
        "name": "Realistic Vision 5.1",
        "description": "Fotorealistik tinggi — cocok untuk portrait, landscape, foto natural.",
        "max_resolution": 768,
        "recommended_steps": 25,
        "vram_estimate_gb": 2.6,
    },
    "anything-v5": {
        "id": "stablediffusionapi/anything-v5",
        "name": "Anything V5",
        "description": "Spesialis anime/manga/illustration bergaya Jepang, detail tinggi.",
        "max_resolution": 768,
        "recommended_steps": 25,
        "vram_estimate_gb": 2.5,
    },
    "rev-animated": {
        "id": "stablediffusionapi/rev-animated",
        "name": "ReV Animated",
        "description": "Semi-realistik bergaya animasi 3D/Pixar, bagus untuk karakter & scene.",
        "max_resolution": 768,
        "recommended_steps": 25,
        "vram_estimate_gb": 2.5,
    },
}

DEFAULT_MODEL_KEY = "sd-1.5"
INITIAL_MODEL_KEY = os.getenv("MODEL_KEY", DEFAULT_MODEL_KEY)

# ==============================================================================
# GLOBAL STATE PIPELINE
# ==============================================================================
pipe: Optional[StableDiffusionPipeline] = None
current_model_key: str = ""
current_model_id: str = ""
model_loading: bool = False
model_load_lock = threading.Lock()


# ==============================================================================
# VRAM & HARDWARE MONITORING FUNCTIONS
# ==============================================================================
def get_vram_info() -> Dict[str, float]:
    """Mengambil metrik penggunaan VRAM GPU saat ini dalam satuan GB."""
    if not torch.cuda.is_available():
        return {}

    try:
        allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(0) / (1024 ** 3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        return {
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "free_gb": round(total - allocated, 2),
        }
    except Exception:
        return {}


def get_pipeline_status() -> Dict[str, Any]:
    """Mengembalikan status kesiapan model, device, dan informasi VRAM."""
    cuda_available = torch.cuda.is_available()
    model_state = "loading" if model_loading else ("ready" if pipe is not None else "unloaded")

    return {
        "model_status": model_state,
        "current_model_key": current_model_key,
        "model_id": current_model_id,
        "device": "cuda" if cuda_available else "cpu",
        "gpu_available": cuda_available,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else "CPU (No CUDA)",
        "vram": get_vram_info(),
    }


def get_registered_models() -> List[Dict[str, Any]]:
    """Mengembalikan daftar seluruh model di registry beserta status aktifnya."""
    models: List[Dict[str, Any]] = []
    for key, info in MODEL_REGISTRY.items():
        models.append({
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "huggingface_id": info["id"],
            "max_resolution": info["max_resolution"],
            "recommended_steps": info["recommended_steps"],
            "vram_estimate_gb": info["vram_estimate_gb"],
            "is_active": (key == current_model_key),
        })
    return models


# ==============================================================================
# PIPELINE MANAGEMENT FUNCTIONS
# ==============================================================================
def _flush_gpu_memory() -> None:
    """Agresif membersihkan VRAM sebelum load model baru."""
    global pipe
    if pipe is not None:
        try:
            pipe.to("cpu")
        except Exception:
            pass
        del pipe
        pipe = None

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()


def _load_pipeline(model_key: str) -> bool:
    """
    Load Stable Diffusion pipeline dari HuggingFace Hub ke GPU.
    """
    global pipe, current_model_key, current_model_id, model_loading

    if model_key not in MODEL_REGISTRY:
        print(f"❌ Model key '{model_key}' tidak ada di registry!")
        return False

    model_info = MODEL_REGISTRY[model_key]
    model_id = model_info["id"]

    print("=" * 60)
    print(f"🔄 Switching to model: {model_info['name']}")
    print(f"   HuggingFace ID: {model_id}")
    print(f"   Estimated VRAM: ~{model_info['vram_estimate_gb']} GB")
    print(f"   📁 Cache folder: {CACHE_DIR}")

    cuda_available = torch.cuda.is_available()
    device = "cuda" if cuda_available else "cpu"
    dtype = torch.float16 if cuda_available else torch.float32

    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"   🎮 GPU: {gpu_name} ({total_vram:.2f} GB VRAM)")

        if model_info["vram_estimate_gb"] > total_vram:
            print(f"   ⚠️ Warning: Estimated VRAM ({model_info['vram_estimate_gb']} GB) "
                  f"exceeds total VRAM ({total_vram:.2f} GB)!")
    else:
        print("   ⚠️ No CUDA GPU — running on CPU (will be slow)")

    print("   🧹 Clearing GPU memory...")
    _flush_gpu_memory()

    try:
        model_loading = True
        print("   📦 Loading model (downloading if first time)...")
        load_start = time.time()

        new_pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
            cache_dir=CACHE_DIR,
        )

        scheduler_config = dict(new_pipe.scheduler.config)
        scheduler_config["final_sigmas_type"] = "sigma_min"
        scheduler_config["algorithm_type"] = "dpmsolver++"
        new_pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)

        if cuda_available:
            new_pipe = new_pipe.to("cuda")
            new_pipe.enable_attention_slicing()
            try:
                new_pipe.enable_vae_slicing()
            except Exception:
                pass

        load_time = round(time.time() - load_start, 2)

        pipe = new_pipe
        current_model_key = model_key
        current_model_id = model_id

        if cuda_available:
            allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
            print(f"   📊 VRAM used after load: {allocated:.2f} GB")

        print(f"   ✅ Model '{model_info['name']}' loaded in {load_time}s on {device}!")
        print("=" * 60)
        return True

    except torch.cuda.OutOfMemoryError:
        print(f"   ❌ CUDA OOM! Model '{model_info['name']}' too large for available VRAM.")
        _flush_gpu_memory()
        return False

    except Exception as e:
        print(f"   ❌ Error loading model: {e}")
        _flush_gpu_memory()
        return False

    finally:
        model_loading = False


def init_default_model() -> bool:
    """Dipanggil saat startup server untuk memuat model awal."""
    print(f"📁 Model cache directory: {CACHE_DIR}")
    print(f"📋 Registered models: {len(MODEL_REGISTRY)}")
    for key, info in MODEL_REGISTRY.items():
        marker = " ← (default)" if key == INITIAL_MODEL_KEY else ""
        print(f"   • {key}: {info['name']}{marker}")

    return _load_pipeline(INITIAL_MODEL_KEY)


def switch_model_pipeline(requested_key: str) -> Dict[str, Any]:
    """
    Thread-safe hot-swap model. Mengembalikan dictionary hasil proses
    yang siap dikonsumsi oleh endpoint /api/switch-model di server.py.
    """
    key = requested_key.strip().lower()

    if key not in MODEL_REGISTRY:
        raise ValueError(f"Model key '{key}' tidak ditemukan di registry.")

    model_info = MODEL_REGISTRY[key]

    if key == current_model_key and pipe is not None:
        return {
            "success": True,
            "message": f"Model '{model_info['name']}' sudah aktif, tidak perlu reload.",
            "model_key": key,
            "model_id": model_info["id"],
            "was_reloaded": False,
        }

    if model_loading or not model_load_lock.acquire(blocking=False):
        raise RuntimeError("Proses switch model lain sedang berjalan. Tunggu hingga selesai.")

    try:
        t0 = time.time()
        success = _load_pipeline(key)
        if not success:
            raise MemoryError(f"Gagal memuat model '{model_info['name']}'. Kemungkinan VRAM tidak cukup.")

        return {
            "success": True,
            "message": f"Model berhasil diganti ke '{model_info['name']}'.",
            "model_key": key,
            "model_id": model_info["id"],
            "model_name": model_info["name"],
            "was_reloaded": True,
            "load_time_seconds": round(time.time() - t0, 2),
            "vram_after_load": get_vram_info(),
        }
    finally:
        model_load_lock.release()


# ==============================================================================
# INFERENCE FUNCTION
# ==============================================================================
def run_inference(
    prompt: str,
    negative_prompt: str = "",
    steps: int = 20,
    cfg_scale: float = 7.0,
    width: int = 512,
    height: int = 512,
    seed: Optional[int] = None,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Menjalankan proses inferensi Stable Diffusion pada GPU/CPU.
    Mengembalikan tuple: (PIL.Image, metadata_dict).
    Konversi gambar ke Base64 ditangani oleh Backend/server.py.
    """
    if pipe is None:
        if model_loading:
            raise RuntimeError("Model sedang dalam proses loading. Tunggu beberapa saat lalu coba lagi.")
        raise RuntimeError("Tidak ada model aktif. Muat model terlebih dahulu.")

    # Validasi dimensi kelipatan 8
    if width % 8 != 0 or height % 8 != 0:
        raise ValueError("Width and Height must be multiples of 8.")

    # Validasi resolusi maksimum berdasarkan model aktif
    active_model_info = MODEL_REGISTRY.get(current_model_key, {})
    max_res = active_model_info.get("max_resolution", 768)
    if width > max_res or height > max_res:
        raise ValueError(
            f"Resolusi melebihi batas model aktif ({max_res}x{max_res}). "
            f"Kurangi ukuran gambar untuk menghindari CUDA OOM pada VRAM 4GB."
        )

    t0 = time.time()
    device_str = "cuda" if torch.cuda.is_available() else "cpu"

    try:
        generator = None
        if seed is not None and seed >= 0:
            generator = torch.Generator(device_str).manual_seed(seed)

        with torch.inference_mode():
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                num_inference_steps=steps,
                guidance_scale=cfg_scale,
                width=width,
                height=height,
                generator=generator,
            )
            image: Image.Image = result.images[0]

        latency = round(time.time() - t0, 3)
        print(
            f"✨ [{current_model_key}] Image generated in {latency}s "
            f"[{width}x{height}, steps={steps}] on {device_str}"
        )

        metadata = {
            "latency_seconds": latency,
            "device": device_str,
            "model_key": current_model_key,
            "model_name": active_model_info.get("name", "Unknown"),
            "resolution": f"{width}x{height}",
        }
        return image, metadata

    except torch.cuda.OutOfMemoryError as oom_err:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise MemoryError(
            "CUDA Out of Memory! Kurangi resolusi gambar (misal 512x512) atau jumlah steps."
        ) from oom_err