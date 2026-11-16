"""
Hugging Face Space Web UI - Hybrid Cloud-to-Local Architecture
Frontend interface deployed on Hugging Face Spaces (Free CPU Tier)
Communicates via Secure Tunnel (Cloudflare/Ngrok) with Local GPU Workstation

UI: Matches Halaman_LOGIN.svg (1:1)
Lock strategy:
  - Locked cards get a transparent click-shield overlay (position:absolute, z-index:50)
  - All inputs/buttons inside locked sections are set to `disabled` via JS
  - On successful connection: wave animation fires, overlays removed, inputs re-enabled
"""
import os
import io
import time
import base64
import requests
from PIL import Image
import gradio as gr

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_TUNNEL_URL = os.getenv("TUNNEL_URL", "")
DEFAULT_API_KEY    = os.getenv("API_KEY", "sk-local-gpu-hybrid-2026")

# ---------------------------------------------------------------------------
# Backend Logic
# ---------------------------------------------------------------------------

def check_connection(tunnel_url: str, api_key: str):
    if not tunnel_url or not tunnel_url.strip():
        return (
            "⚠️ **Status:** URL Tunnel belum diisi!  \n"
            "Masukkan URL Cloudflare Tunnel atau Ngrok.",
            False
        )
    clean_url = tunnel_url.strip().rstrip("/")
    headers   = {"X-API-Key": api_key.strip()} if api_key and api_key.strip() else {}
    t0 = time.time()
    try:
        resp      = requests.get(f"{clean_url}/api/status", headers=headers, timeout=10)
        roundtrip = round((time.time() - t0) * 1000, 1)
        if resp.status_code == 200:
            d = resp.json()
            vram   = d.get("vram", {})
            vstr   = f" | VRAM: {vram.get('total_gb','?')} GB" if vram else ""
            return (
                f"✅ **Terhubung!**  \n"
                f"**Device:** `{d.get('gpu_name','?')}` ({d.get('device','?').upper()})  \n"
                f"**Model:** `{d.get('model_status','?')}` | **Ping:** `{roundtrip} ms`{vstr}",
                True
            )
        elif resp.status_code == 401:
            return "❌ **401 Unauthorized:** API Key tidak valid.", False
        else:
            return f"⚠️ **HTTP {resp.status_code}:** {resp.text[:200]}", False
    except requests.exceptions.Timeout:
        return "❌ **Timeout:** Server tidak merespon (10s).", False
    except requests.exceptions.ConnectionError:
        return "❌ **Connection Error:** URL tunnel tidak dapat dijangkau.", False
    except Exception as e:
        return f"❌ **Error:** {str(e)}", False


def handle_test(tunnel_url: str, api_key: str):
    """Returns (status_md, signal_html)."""
    text, valid = check_connection(tunnel_url, api_key)
    signal = (
        '<span id="hig-unlock-signal" style="display:none" aria-hidden="true"></span>'
        if valid else ""
    )
    return text, gr.update(value=signal)


def generate_hybrid(
    tunnel_url, api_key, model_key,
    prompt, negative_prompt,
    steps, cfg_scale, dimensions, seed, randomize_seed,
    progress=gr.Progress(track_tqdm=True)
):
    if not tunnel_url or not tunnel_url.strip():
        raise gr.Error("URL Tunnel wajib diisi!")
    if not prompt or not prompt.strip():
        raise gr.Error("Prompt tidak boleh kosong!")

    clean_url = tunnel_url.strip().rstrip("/")
    try:
        w, h = (int(x) for x in dimensions.split("x"))
    except Exception:
        w, h = 512, 512

    actual_seed = None if randomize_seed or seed < 0 else int(seed)
    payload = {
        "prompt":          prompt.strip(),
        "negative_prompt": negative_prompt.strip() if negative_prompt else "",
        "steps":           int(steps),
        "cfg_scale":       float(cfg_scale),
        "width":           w,
        "height":          h,
        "seed":            actual_seed,
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-Key":    api_key.strip() if api_key else "",
    }
    progress(0.1, desc="Mengirim ke GPU lokal...")
    t0 = time.time()
    try:
        progress(0.3, desc="Inferensi Stable Diffusion...")
        resp = requests.post(
            f"{clean_url}/api/generate",
            json=payload, headers=headers, timeout=180
        )
        total = round(time.time() - t0, 2)
        if resp.status_code == 200:
            progress(0.9, desc="Memproses gambar...")
            d        = resp.json()
            img_b64  = d.get("image_base64")
            if not img_b64:
                raise gr.Error("Response backend tidak valid.")
            image    = Image.open(io.BytesIO(base64.b64decode(img_b64)))
            latency  = d.get("latency_seconds", total)
            info = (
                f"✨ **Berhasil!**  \n"
                f"**Hardware:** `{d.get('device','GPU').upper()}` | "
                f"**Model:** `{d.get('model_name', model_key)}`  \n"
                f"**Waktu:** `{latency}s` (total `{total}s`) | "
                f"**Resolusi:** `{w}x{h}` | Steps: `{steps}` | CFG: `{cfg_scale}`  \n"
                f"**Seed:** `{actual_seed if actual_seed is not None else 'Random'}`"
            )
            return image, info
        elif resp.status_code == 401:
            raise gr.Error("401 Unauthorized: API Key salah!")
        elif resp.status_code == 503:
            raise gr.Error("503: Model masih loading, coba lagi.")
        else:
            detail = resp.json().get("detail", resp.text) if resp.content else resp.text
            raise gr.Error(f"Backend Error {resp.status_code}: {detail}")
    except requests.exceptions.Timeout:
        raise gr.Error("Timeout (180s): GPU lokal tidak merespon.")
    except requests.exceptions.ConnectionError:
        raise gr.Error("Connection Error: Tunnel tidak aktif.")


# ---------------------------------------------------------------------------
# CSS — matches Halaman_LOGIN.svg color palette + card geometry
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
/* ================================================================
   TOKENS — derived from SVG radial gradient #1a1a3e → #2d2b55
   ================================================================ */
:root {
    --c-bg:            #0f0f1e;
    --c-bg2:           #15152b;
    --c-purple:        #7c5cfc;
    --c-blue:          #4fa3f7;
    --c-cyan:          #00d4ff;
    --c-grad:          linear-gradient(135deg, #7c5cfc 0%, #4fa3f7 55%, #00d4ff 100%);
    --c-glass:         rgba(255,255,255,0.055);
    --c-glass-hover:   rgba(255,255,255,0.09);
    --c-edge:          rgba(255,255,255,0.12);
    --c-edge-active:   rgba(124,92,252,0.45);
    --c-shadow:        0 8px 40px rgba(0,0,0,0.55);
    --c-txt:           #ffffff;
    --c-muted:         rgba(235,235,245,0.55);
    --c-lock-bg:       rgba(255,255,255,0.025);
    --c-lock-edge:     rgba(255,255,255,0.065);
    --r:               15px;
    --transition:      0.38s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* ================================================================
   SHELL RESET
   ================================================================ */
html, body, .gradio-container, .main {
    background: var(--c-bg) !important;
    color: var(--c-txt) !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                 "Segoe UI", Helvetica, Arial, sans-serif !important;
    margin: 0 !important; padding: 0 !important;
}
.gradio-container { max-width: 100% !important; }
footer { display: none !important; }

/* Gradio default panel/block borders */
.gr-panel, .gr-block, .gr-box, .gr-padded {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ================================================================
   HEADER — matches SVG top gradient band
   ================================================================ */
#hig-header {
    background: linear-gradient(160deg, #1a1a3e 0%, #2a2860 45%, #1e1e4f 100%);
    padding: 1.75rem 2rem 1.4rem;
    position: relative;
    overflow: hidden;
    border-bottom: 0.5px solid rgba(255,255,255,0.08);
}
#hig-header::after {
    content: "";
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 55% 90% at 75% 50%,
                rgba(124,92,252,0.22), transparent 70%);
    pointer-events: none;
}
#hig-header .hig-title {
    font-size: 1.65rem; font-weight: 700;
    letter-spacing: -0.02em; color: #fff;
    margin: 0 0 0.3rem;
}
#hig-header .hig-sub {
    font-size: 0.875rem; color: var(--c-muted); margin: 0;
}
#hig-header .hig-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(124,92,252,0.18);
    border: 0.5px solid rgba(124,92,252,0.4);
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.72rem; font-weight: 600;
    color: #c8b4ff; letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.65rem;
}

/* ================================================================
   MAIN 2-COL ROW
   ================================================================ */
#hig-layout {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 1rem;
    padding: 1rem;
    min-height: calc(100vh - 120px);
    box-sizing: border-box;
}
#hig-col-left, #hig-col-right {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

/* ================================================================
   CARD — base glass morphism (matches SVG rect black 0.4 opacity)
   ================================================================ */
.hig-card {
    position: relative;
    background: var(--c-glass);
    border: 0.5px solid var(--c-edge);
    border-radius: var(--r);
    backdrop-filter: blur(18px) saturate(1.5);
    -webkit-backdrop-filter: blur(18px) saturate(1.5);
    box-shadow: var(--c-shadow);
    transition: border-color var(--transition), background var(--transition),
                box-shadow var(--transition);
    overflow: hidden;
}
/* Rim highlight (Glisse-style) */
.hig-card::before {
    content: "";
    position: absolute; inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg,
        rgba(255,255,255,0.09) 0%,
        rgba(255,255,255,0.03) 35%,
        transparent 60%);
    pointer-events: none; z-index: 0;
}

/* ================================================================
   STEP HEADER STRIP (top of each card, 74px in SVG)
   ================================================================ */
.hig-step-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 1rem 1.25rem;
    border-bottom: 0.5px solid var(--c-edge);
    position: relative; z-index: 1;
    transition: background var(--transition);
}
.hig-step-num {
    width: 30px; height: 30px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
    flex-shrink: 0;
    transition: background var(--transition), color var(--transition),
                box-shadow var(--transition);
}
.hig-step-title { font-size: 0.95rem; font-weight: 600; line-height: 1.2; }
.hig-step-sub   { font-size: 0.72rem; color: var(--c-muted); margin-top: 0.1rem; }

/* -- ACTIVE state (Step 1 on load; all after unlock) -- */
.hig-state-active .hig-step-header {
    background: rgba(124,92,252,0.14);
}
.hig-state-active .hig-step-num {
    background: var(--c-grad);
    color: #fff;
    box-shadow: 0 0 12px rgba(124,92,252,0.5);
}
.hig-state-active { border-color: rgba(124,92,252,0.3) !important; }

/* -- LOCKED state -- */
.hig-state-locked {
    background: var(--c-lock-bg) !important;
    border-color: var(--c-lock-edge) !important;
}
.hig-state-locked .hig-step-header {
    background: rgba(255,255,255,0.025);
}
.hig-state-locked .hig-step-num {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.3);
}
.hig-state-locked .hig-step-title { color: rgba(255,255,255,0.3); }
.hig-state-locked .hig-step-sub   { color: rgba(255,255,255,0.18); }

/* Click-shield overlay — the REAL lock */
.hig-lock-shield {
    position: absolute;
    inset: 0;
    z-index: 50;
    background: transparent;
    cursor: not-allowed;
    border-radius: inherit;
}

/* ================================================================
   CARD BODY
   ================================================================ */
.hig-card-body {
    padding: 1.25rem;
    position: relative; z-index: 1;
    transition: opacity var(--transition);
}
.hig-state-locked .hig-card-body { opacity: 0.3; }

/* ================================================================
   GRADIO COMPONENT OVERRIDES
   ================================================================ */
/* Labels */
.gradio-container label span,
.gradio-container .label-wrap span,
.gradio-container .svelte-1gfkn6j {
    color: var(--c-muted) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

/* Inputs & textareas */
.gradio-container input[type=text],
.gradio-container input[type=password],
.gradio-container textarea,
.gradio-container .gr-input {
    background: rgba(255,255,255,0.07) !important;
    border: 0.5px solid rgba(255,255,255,0.14) !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-size: 0.875rem !important;
    padding: 0.6rem 0.9rem !important;
    transition: border-color 0.2s, background 0.2s !important;
    caret-color: var(--c-purple);
}
.gradio-container input:focus,
.gradio-container textarea:focus {
    border-color: var(--c-purple) !important;
    background: rgba(124,92,252,0.1) !important;
    outline: none !important;
}
.gradio-container input::placeholder,
.gradio-container textarea::placeholder { color: rgba(255,255,255,0.3) !important; }

/* Select / Dropdown */
.gradio-container select,
.gradio-container .gr-dropdown {
    background: rgba(255,255,255,0.07) !important;
    border: 0.5px solid rgba(255,255,255,0.14) !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-size: 0.875rem !important;
}

/* Primary button */
.gradio-container button.primary,
.gradio-container .gr-button-primary,
.gradio-container button[data-testid="submit-btn"] {
    background: var(--c-grad) !important;
    border: none !important;
    border-radius: 9px !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1.4rem !important;
    box-shadow: 0 4px 18px rgba(124,92,252,0.4) !important;
    transition: opacity 0.2s, transform 0.15s !important;
}
.gradio-container button.primary:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
.gradio-container button.primary:active { transform: translateY(0) !important; }
.gradio-container button.primary:disabled {
    opacity: 0.3 !important; cursor: not-allowed !important; transform: none !important;
}

/* Secondary button */
.gradio-container button.secondary,
.gradio-container .gr-button-secondary {
    background: rgba(255,255,255,0.08) !important;
    border: 0.5px solid rgba(255,255,255,0.18) !important;
    border-radius: 9px !important;
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.875rem !important;
    padding: 0.6rem 1.2rem !important;
    transition: background 0.2s !important;
}
.gradio-container button.secondary:hover { background: rgba(255,255,255,0.14) !important; }

/* Slider */
.gradio-container input[type=range] { accent-color: var(--c-purple) !important; }

/* Markdown prose */
.gradio-container .prose { color: var(--c-muted) !important; }
.gradio-container .prose strong { color: #fff !important; }
.gradio-container .prose code {
    background: rgba(124,92,252,0.2) !important;
    color: #c8b8ff !important;
    border-radius: 4px !important;
    padding: 0.1em 0.4em !important;
    font-size: 0.85em !important;
}

/* Image output */
.gradio-container .image-container {
    background: rgba(0,0,0,0.3) !important;
    border: 0.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    overflow: hidden;
}

/* Number input */
.gradio-container input[type=number] {
    background: rgba(255,255,255,0.07) !important;
    border: 0.5px solid rgba(255,255,255,0.14) !important;
    border-radius: 10px !important;
    color: #fff !important;
    padding: 0.6rem 0.75rem !important;
}

/* Checkbox */
.gradio-container input[type=checkbox] { accent-color: var(--c-purple); }

/* Examples section */
.gradio-container .gr-examples { opacity: 0.7; }

/* ================================================================
   STATUS OUTPUT
   ================================================================ */
#hig-status .prose { font-size: 0.84rem !important; line-height: 1.6 !important; }

/* ================================================================
   WAVE FILL ANIMATION
   ================================================================ */
@keyframes hig-wave {
    0%   { transform: translateX(-110%) skewX(-6deg); opacity: 0; }
    5%   { opacity: 1; }
    95%  { opacity: 1; }
    100% { transform: translateX(110%) skewX(-6deg); opacity: 0; }
}
#hig-wave-layer {
    position: fixed; inset: 0;
    pointer-events: none; z-index: 9000;
    overflow: hidden; display: none;
}
.hig-wave {
    position: absolute; top: -30%; left: 0;
    width: 55%; height: 160%;
    animation: hig-wave 1.05s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
.hig-wave-1 {
    background: linear-gradient(90deg,
        transparent 0%, rgba(124,92,252,0.3) 25%,
        rgba(79,163,247,0.4) 55%, rgba(0,212,255,0.3) 80%, transparent 100%);
}
.hig-wave-2 {
    animation-delay: 0.1s;
    background: linear-gradient(90deg,
        transparent 0%, rgba(0,212,255,0.14) 30%,
        rgba(124,92,252,0.2) 65%, transparent 100%);
}
.hig-wave-3 {
    animation-delay: 0.22s;
    background: linear-gradient(90deg,
        transparent 0%, rgba(79,163,247,0.1) 40%,
        rgba(0,212,255,0.14) 70%, transparent 100%);
}

/* Post-unlock border pulse */
@keyframes hig-border-pulse {
    0%, 100% { box-shadow: var(--c-shadow), 0 0 0 1px rgba(124,92,252,0.2); }
    50%       { box-shadow: var(--c-shadow), 0 0 0 2px rgba(124,92,252,0.45); }
}
.hig-state-unlocked {
    animation: hig-border-pulse 2s ease-in-out 3;
    border-color: rgba(124,92,252,0.35) !important;
}
.hig-state-unlocked .hig-step-header { background: rgba(79,163,247,0.1); }
.hig-state-unlocked .hig-step-num {
    background: var(--c-grad);
    color: #fff;
    box-shadow: 0 0 10px rgba(79,163,247,0.4);
}
.hig-state-unlocked .hig-step-title { color: #fff; }
.hig-state-unlocked .hig-card-body  { opacity: 1 !important; }

/* ================================================================
   RESPONSIVE
   ================================================================ */
@media (max-width: 800px) {
    #hig-layout { flex-direction: column !important; }
    #hig-header .hig-title { font-size: 1.2rem; }
}
"""

# ---------------------------------------------------------------------------
# Inline HTML/JS — wave animation + hard lock/unlock logic
# ---------------------------------------------------------------------------

BOOTSTRAP_HTML = """
<!-- Wave layer -->
<div id="hig-wave-layer" aria-hidden="true">
  <div class="hig-wave hig-wave-1"></div>
  <div class="hig-wave hig-wave-2"></div>
  <div class="hig-wave hig-wave-3"></div>
</div>

<script>
(function () {
  "use strict";

  /* IDs of locked card wrappers — set by Python via elem_id */
  var LOCKED_IDS = ["hig-card2", "hig-card3", "hig-card4"];
  var unlocked   = false;

  /* ---- Utility: find all interactive elements inside a container ---- */
  function getInteractives(el) {
    return el.querySelectorAll(
      'input, textarea, select, button, [role="slider"], [tabindex]'
    );
  }

  /* ---- Disable all interactives in a card (called at startup) ---- */
  function disableCard(id) {
    var card = document.getElementById(id);
    if (!card) return;
    getInteractives(card).forEach(function (el) {
      el.disabled       = true;
      el.tabIndex       = -1;
      el.style.pointerEvents = "none";
    });
  }

  /* ---- Enable all interactives in a card ---- */
  function enableCard(id) {
    var card = document.getElementById(id);
    if (!card) return;
    getInteractives(card).forEach(function (el) {
      el.disabled       = false;
      el.tabIndex       = 0;
      el.style.pointerEvents = "";
    });
    /* Swap classes */
    card.classList.remove("hig-state-locked");
    card.classList.add("hig-state-active", "hig-state-unlocked");
    /* Remove click-shield */
    var shield = card.querySelector(".hig-lock-shield");
    if (shield) shield.remove();
  }

  /* ---- Wave sweep ---- */
  function triggerWave() {
    var layer = document.getElementById("hig-wave-layer");
    if (!layer) return;
    layer.style.display = "block";
    setTimeout(function () { layer.style.display = "none"; }, 1300);
  }

  /* ---- Full unlock sequence ---- */
  function unlock() {
    if (unlocked) return;
    unlocked = true;

    triggerWave();
    setTimeout(function () {
      LOCKED_IDS.forEach(function (id) { enableCard(id); });
    }, 250);
  }

  /* ---- Watch for the signal span injected by Python ---- */
  function watchSignal() {
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var nodes = mutations[i].addedNodes;
        for (var j = 0; j < nodes.length; j++) {
          var n = nodes[j];
          if (n.id === "hig-unlock-signal" ||
              (n.querySelector && n.querySelector("#hig-unlock-signal"))) {
            observer.disconnect();
            unlock();
            return;
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ---- Run after Gradio has rendered ---- */
  function init() {
    /* 1. Add lock shields & disable interactives for each locked card */
    LOCKED_IDS.forEach(function (id) {
      var card = document.getElementById(id);
      if (!card) return;

      /* Transparent overlay — blocks all pointer events absolutely */
      if (!card.querySelector(".hig-lock-shield")) {
        var shield = document.createElement("div");
        shield.className  = "hig-lock-shield";
        shield.setAttribute("aria-hidden", "true");
        shield.setAttribute("title", "Selesaikan koneksi di Step 1 terlebih dahulu");
        card.appendChild(shield);
      }

      /* Programmatically disable every interactive child */
      disableCard(id);
    });

    /* 2. Start watching for unlock signal */
    watchSignal();
  }

  /* Wait for Gradio's DOM to settle before running init */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(init, 600);
    });
  } else {
    setTimeout(init, 600);
  }

  /* Re-run init after Gradio re-renders (e.g., hot reload) */
  window.addEventListener("gradio:loaded", function () {
    setTimeout(init, 400);
  });
})();
</script>
"""

# ---------------------------------------------------------------------------
# Model choices
# ---------------------------------------------------------------------------
MODEL_CHOICES = [
    ("Stable Diffusion 1.5 (Base)",          "sd-1.5"),
    ("DreamShaper 8 (Art / Illustration)",   "dreamshaper-8"),
    ("Realistic Vision 5.1 (Fotorealistik)", "realistic-vision-5.1"),
    ("Anything V5 (Anime / Manga)",          "anything-v5"),
    ("ReV Animated (3D / Pixar Style)",      "rev-animated"),
]

# ---------------------------------------------------------------------------
# Build Gradio app
# ---------------------------------------------------------------------------
with gr.Blocks(
    title="Hybrid Image Generation WebUI",
    css=CUSTOM_CSS,
    theme=gr.themes.Base(
        primary_hue="purple",
        secondary_hue="blue",
        neutral_hue="slate",
    ),
) as demo:

    # ---- Inject bootstrap JS + wave layer ----
    gr.HTML(BOOTSTRAP_HTML)

    # ================================================================
    # HEADER
    # ================================================================
    gr.HTML("""
    <div id="hig-header">
      <div class="hig-badge">&#x2b22; Hybrid Cloud &rarr; Local GPU</div>
      <div class="hig-title">&#x1f3a8; IMAGE GENERATION &nbsp;&mdash;&nbsp; HUGGING FACE WEB UI</div>
      <div class="hig-sub">
        Frontend ringan di <strong>Hugging Face Spaces</strong> yang meneruskan inferensi ke
        <strong>GPU Workstation Lokal</strong> via Secure Tunnel (Cloudflare / Ngrok)
      </div>
    </div>
    """)

    # ================================================================
    # MAIN LAYOUT — 2 columns
    # ================================================================
    gr.HTML('<div id="hig-layout">')

    # ---- LEFT COLUMN ----
    gr.HTML('<div id="hig-col-left">')

    # ---- CARD 1 — Koneksi (ACTIVE on load) ----
    with gr.Group(elem_id="hig-card1", elem_classes=["hig-card", "hig-state-active"]):
        gr.HTML("""
        <div class="hig-step-header">
          <div class="hig-step-num">1</div>
          <div>
            <div class="hig-step-title">Koneksi Node Lokal</div>
            <div class="hig-step-sub">Secure Tunnel &amp; API Key</div>
          </div>
        </div>
        """)
        with gr.Column(elem_classes=["hig-card-body"]):
            tunnel_url = gr.Textbox(
                label="URL Tunnel Backend Lokal",
                placeholder="https://xxxx.trycloudflare.com",
                value=DEFAULT_TUNNEL_URL,
                info="URL publik Cloudflare Tunnel / Ngrok yang mengarah ke port 8000.",
            )
            api_key = gr.Textbox(
                label="Custom API Key",
                placeholder="sk-local-gpu-hybrid-2026",
                value=DEFAULT_API_KEY,
                type="password",
                info="API key untuk autentikasi akses GPU lokal.",
            )
            btn_check = gr.Button("Test Koneksi", variant="secondary")

            # Hidden signal carrier
            unlock_signal = gr.HTML(value="", visible=True, elem_id="hig-signal-host")

            status_md = gr.Markdown(
                "Tekan **Test Koneksi** untuk memverifikasi kesiapan GPU lokal.",
                elem_id="hig-status",
            )

    # ---- CARD 2 — Model (LOCKED on load) ----
    with gr.Group(elem_id="hig-card2", elem_classes=["hig-card", "hig-state-locked"]):
        gr.HTML("""
        <div class="hig-step-header">
          <div class="hig-step-num">2</div>
          <div>
            <div class="hig-step-title">Pilih Model AI</div>
            <div class="hig-step-sub">Hot-swap tersedia setelah koneksi aktif</div>
          </div>
        </div>
        """)
        with gr.Column(elem_classes=["hig-card-body"]):
            model_key = gr.Dropdown(
                label="Model Inferensi",
                choices=MODEL_CHOICES,
                value="sd-1.5",
                info="Semua model dioptimalkan untuk VRAM 4GB (RTX 2050).",
            )

    gr.HTML('</div>')  # close hig-col-left

    # ---- RIGHT COLUMN ----
    gr.HTML('<div id="hig-col-right">')

    # ---- CARD 3 — Parameter (LOCKED on load) ----
    with gr.Group(elem_id="hig-card3", elem_classes=["hig-card", "hig-state-locked"]):
        gr.HTML("""
        <div class="hig-step-header">
          <div class="hig-step-num">3</div>
          <div>
            <div class="hig-step-title">Parameter Pembuatan Gambar</div>
            <div class="hig-step-sub">Prompt, resolusi &amp; konfigurasi inferensi</div>
          </div>
        </div>
        """)
        with gr.Column(elem_classes=["hig-card-body"]):
            prompt = gr.Textbox(
                label="Prompt",
                lines=3,
                placeholder="Contoh: A high-tech cyberpunk lab with glowing neon lights, ultra realistic 8k...",
                value="A futuristic cybernetic cat sitting on a neon rooftop, cyberpunk city in the background, highly detailed, 8k resolution, cinematic lighting",
            )
            negative_prompt = gr.Textbox(
                label="Negative Prompt",
                lines=2,
                placeholder="Elemen yang ingin dihindari...",
                value="blurry, distorted, low quality, bad anatomy, out of frame, watermark",
            )
            with gr.Row():
                steps = gr.Slider(
                    minimum=10, maximum=50, value=20, step=1,
                    label="Inference Steps",
                    info="20 steps optimal untuk DPMSolver",
                )
                cfg_scale = gr.Slider(
                    minimum=1.0, maximum=15.0, value=7.5, step=0.5,
                    label="CFG Guidance Scale",
                    info="Tingkat kepatuhan terhadap prompt",
                )
            with gr.Row():
                dimensions = gr.Dropdown(
                    choices=["512x512", "512x768", "768x512"],
                    value="512x512",
                    label="Resolusi",
                    info="512x512 optimal untuk VRAM 4GB",
                )
                seed = gr.Number(
                    value=-1, label="Seed",
                    info="-1 untuk acak",
                )
                randomize_seed = gr.Checkbox(
                    value=True, label="Randomize Seed",
                    info="Seed baru tiap generasi",
                )
            btn_generate = gr.Button(
                "Generate Image (Kirim ke GPU Lokal)",
                variant="primary", size="lg",
            )

    # ---- CARD 4 — Output (LOCKED on load) ----
    with gr.Group(elem_id="hig-card4", elem_classes=["hig-card", "hig-state-locked"]):
        gr.HTML("""
        <div class="hig-step-header">
          <div class="hig-step-num">4</div>
          <div>
            <div class="hig-step-title">Hasil Gambar</div>
            <div class="hig-step-sub">Output dari GPU Workstation Lokal</div>
          </div>
        </div>
        """)
        with gr.Column(elem_classes=["hig-card-body"]):
            output_image = gr.Image(
                label="Generated Output",
                type="pil",
                interactive=False,
            )
            output_info = gr.Markdown(
                "Hasil generasi dan metrik latensi akan tampil di sini."
            )

    gr.HTML('</div>')  # close hig-col-right
    gr.HTML('</div>')  # close hig-layout

    # Examples (outside locked area)
    gr.Examples(
        examples=[
            [
                "A serene Japanese garden in autumn, vibrant red maple leaves, stone lanterns, koi pond, cinematic morning light",
                "blurry, ugly, distorted, lowres",
                20, 7.5, "512x512",
            ],
            [
                "Detailed digital painting of an astronaut exploring alien ruins on Mars, atmospheric dust, dramatic lighting",
                "bad quality, oversaturated, deformed",
                25, 8.0, "512x512",
            ],
        ],
        inputs=[prompt, negative_prompt, steps, cfg_scale, dimensions],
        label="Contoh Prompt",
    )

    # ================================================================
    # EVENT HANDLERS
    # ================================================================
    btn_check.click(
        fn=handle_test,
        inputs=[tunnel_url, api_key],
        outputs=[status_md, unlock_signal],
    )

    btn_generate.click(
        fn=generate_hybrid,
        inputs=[
            tunnel_url, api_key, model_key,
            prompt, negative_prompt,
            steps, cfg_scale, dimensions, seed, randomize_seed,
        ],
        outputs=[output_image, output_info],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")