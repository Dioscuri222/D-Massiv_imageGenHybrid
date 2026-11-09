"""
Model Pipeline Module
Menangani manajemen memori VRAM, registry model, serta load/hot-swap Stable Diffusion.
"""
import os
import gc
import time
import torch
from typing import Optional, Dict, Any
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
# MODEL REGISTRY
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

# ==============================================================================
# GLOBAL STATE PIPELINE
# ==============================================================================
pipe = None
current_model_key: str = ""
current_model_id: str = ""
model_loading: bool = False

# ==============================================================================
# PIPELINE MANAGEMENT FUNCTIONS
# ==============================================================================
def _flush_gpu_memory():
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
        print(f"   📦 Loading model (downloading if first time)...")
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
        model_loading = False
        return False

    except Exception as e:
        print(f"   ❌ Error loading model: {e}")
        _flush_gpu_memory()
        model_loading = False
        return False

    finally:
        model_loading = False