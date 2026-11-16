/**
 * IMAGE GENERATION WEB UI - FRONTEND APP
 * Pure Vanilla JavaScript matching Halaman _LOGIN_.svg
 * Features:
 *   - Step 1 Active / Step 2 Locked (unclickable) on load
 *   - Real backend verification via Secure Tunnel / Local GPU FastAPI
 *   - Luminous Directional Wave sweep animation upon successful API Key validation
 *   - Liquid Glass UI unlock with interactive sliders, generate, and lightbox
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------------------
    // DOM Element References
    // -------------------------------------------------------------------------
    // Step 1 Elements
    const tunnelUrlInput    = document.getElementById("tunnel-url-input");
    const apiKeyInput       = document.getElementById("api-key-input");
    const btnVerifyKey      = document.getElementById("btn-verify-key");
    const statusBox         = document.getElementById("connection-status-box");
    const statusMessage     = document.getElementById("status-message");
    const step1Card         = document.getElementById("step1-card");

    // Step 2 Elements
    const step2Card         = document.getElementById("step2-card");
    const step2LockShield   = document.getElementById("step2-lock-shield");
    const promptInput       = document.getElementById("prompt-input");
    const negPromptInput    = document.getElementById("negative-prompt-input");
    const stepsSlider       = document.getElementById("steps-slider");
    const stepsValDisplay   = document.getElementById("steps-value-display");
    const stepsFillTrack    = document.getElementById("steps-fill");
    const cfgSlider         = document.getElementById("cfg-slider");
    const cfgValDisplay     = document.getElementById("cfg-value-display");
    const cfgFillTrack      = document.getElementById("cfg-fill");
    const resolutionSelect  = document.getElementById("resolution-select");
    const seedInput         = document.getElementById("seed-input");
    const btnGenerate       = document.getElementById("btn-generate-image");

    // Output & Metric Elements
    const imageDisplayBox   = document.getElementById("image-display-box");
    const imagePlaceholder  = document.getElementById("image-placeholder-content");
    const generatedImage    = document.getElementById("generated-image");
    const metricHardware    = document.getElementById("metric-hardware");
    const metricTime        = document.getElementById("metric-time");
    const metricResolution  = document.getElementById("metric-resolution");
    const metricStatus      = document.getElementById("metric-status");

    // Wave Overlay & Modal
    const waveOverlay       = document.getElementById("wave-screen-overlay");
    const imageModal        = document.getElementById("image-modal");
    const modalImg          = document.getElementById("modal-enlarged-img");
    const modalClose        = document.getElementById("modal-close");
    const modalBackdrop     = document.getElementById("modal-backdrop");

    // State Variables
    let isConnected         = false;
    let verifiedTunnelUrl   = "";
    let verifiedApiKey      = "";

    // -------------------------------------------------------------------------
    // Initialize Slider Fill & Values
    // -------------------------------------------------------------------------
    function updateSlider(slider, displayEl, fillEl, isDecimal = false) {
        const min = parseFloat(slider.min);
        const max = parseFloat(slider.max);
        const val = parseFloat(slider.value);
        const percent = ((val - min) / (max - min)) * 100;

        if (isDecimal) {
            displayEl.textContent = val.toFixed(1).replace(".", ",");
        } else {
            displayEl.textContent = Math.round(val);
        }

        if (fillEl) {
            fillEl.style.width = `${percent}%`;
        }
    }

    stepsSlider.addEventListener("input", () => {
        updateSlider(stepsSlider, stepsValDisplay, stepsFillTrack, false);
    });

    cfgSlider.addEventListener("input", () => {
        updateSlider(cfgSlider, cfgValDisplay, cfgFillTrack, true);
    });

    // Initial slider track rendering
    updateSlider(stepsSlider, stepsValDisplay, stepsFillTrack, false);
    updateSlider(cfgSlider, cfgValDisplay, cfgFillTrack, true);

    // -------------------------------------------------------------------------
    // Helper: Normalize URL
    // -------------------------------------------------------------------------
    function getNormalizedUrl(url) {
        if (!url || !url.trim()) return "";
        let clean = url.trim().replace(/\/+$/, "");
        if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
            // Default to https for trycloudflare/ngrok or http for localhost
            if (clean.includes("localhost") || clean.includes("127.0.0.1")) {
                clean = `http://${clean}`;
            } else {
                clean = `https://${clean}`;
            }
        }
        return clean;
    }

    // -------------------------------------------------------------------------
    // STEP 1: Verify API Key & Connection to Local GPU Backend
    // -------------------------------------------------------------------------
    btnVerifyKey.addEventListener("click", async () => {
        const rawUrl = tunnelUrlInput.value.trim();
        const apiKey = apiKeyInput.value.trim();

        // Allow localhost fallback if blank
        let cleanUrl = getNormalizedUrl(rawUrl);
        if (!cleanUrl) {
            // Check if local backend port 8000 is running
            cleanUrl = "http://127.0.0.1:8000";
            tunnelUrlInput.value = cleanUrl;
        }

        // Set Loading UI
        btnVerifyKey.classList.add("btn-loading");
        btnVerifyKey.disabled = true;
        statusBox.className = "status-box status-idle";
        statusMessage.textContent = "Menghubungi workstation GPU lokal...";

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 12000);

            const headers = {
                "Accept": "application/json"
            };
            if (apiKey) {
                headers["X-API-Key"] = apiKey;
            }

            const response = await fetch(`${cleanUrl}/api/status`, {
                method: "GET",
                headers: headers,
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                const gpuName = data.gpu_name || "GPU Workstation";
                const totalVram = (data.vram && data.vram.total_gb) ? `${data.vram.total_gb}GB` : "4GB";
                
                // Connection Valid!
                isConnected = true;
                verifiedTunnelUrl = cleanUrl;
                verifiedApiKey = apiKey;

                // Update Status Box
                statusBox.className = "status-box status-success";
                statusMessage.textContent = `API Key Valid! Connected to ${gpuName} (VRAM ${totalVram})`;

                // Trigger Directional Wave & Unlock Step 2
                triggerWaveUnlock();

            } else if (response.status === 401) {
                statusBox.className = "status-box status-error";
                statusMessage.textContent = "401 Unauthorized: API Key tidak valid atau ditolak oleh server lokal.";
            } else {
                statusBox.className = "status-box status-error";
                statusMessage.textContent = `Error HTTP ${response.status}: ${response.statusText}`;
            }

        } catch (err) {
            statusBox.className = "status-box status-error";
            if (err.name === "AbortError") {
                statusMessage.textContent = "Connection Timeout: Server GPU lokal tidak merespon (12s).";
            } else {
                statusMessage.textContent = `Connection Error: Tidak dapat menghubungi server (${cleanUrl}).`;
            }
        } finally {
            btnVerifyKey.classList.remove("btn-loading");
            btnVerifyKey.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Wave Animation & Step 2 Unlock Sequence
    // -------------------------------------------------------------------------
    function triggerWaveUnlock() {
        // 1. Play Wave Light Beam Animation
        waveOverlay.style.display = "block";
        setTimeout(() => {
            waveOverlay.style.display = "none";
        }, 1300);

        // 2. Unlock Step 2 as the beam passes it (~300ms)
        setTimeout(() => {
            // Remove gray/locked state
            step2Card.classList.remove("locked-state");
            step2Card.classList.add("unlocked-celebration");

            // Fade out and remove click-shield
            if (step2LockShield) {
                step2LockShield.style.opacity = "0";
                setTimeout(() => {
                    step2LockShield.style.display = "none";
                }, 400);
            }

            // Enable all form controls in Step 2
            promptInput.disabled      = false;
            negPromptInput.disabled   = false;
            stepsSlider.disabled      = false;
            cfgSlider.disabled        = false;
            resolutionSelect.disabled = false;
            seedInput.disabled        = false;
            btnGenerate.disabled      = false;

            // Update initial metrics display
            metricHardware.textContent = "Local GPU (Ready)";
            metricStatus.textContent   = "Ready";
            metricStatus.className     = "metric-val status-badge-idle";

        }, 320);
    }

    // -------------------------------------------------------------------------
    // STEP 2: Generate Image from Local GPU Workstation
    // -------------------------------------------------------------------------
    btnGenerate.addEventListener("click", async () => {
        if (!isConnected) {
            alert("Harap selesaikan koneksi dan verifikasi API Key di Step 1 terlebih dahulu!");
            return;
        }

        const promptText = promptInput.value.trim();
        if (!promptText) {
            alert("Prompt pembuatan gambar tidak boleh kosong!");
            promptInput.focus();
            return;
        }

        const negPromptText = negPromptInput.value.trim();
        const stepsVal      = parseInt(stepsSlider.value, 10) || 20;
        const cfgVal        = parseFloat(cfgSlider.value) || 7.5;
        const resChoice     = resolutionSelect.value || "512x512";
        const [wStr, hStr]  = resChoice.split("x");
        const widthVal      = parseInt(wStr, 10) || 512;
        const heightVal     = parseInt(hStr, 10) || 512;
        const seedVal       = parseInt(seedInput.value, 10);
        const actualSeed    = (isNaN(seedVal) || seedVal < 0) ? null : seedVal;

        // UI Loading State
        btnGenerate.classList.add("btn-loading");
        btnGenerate.disabled = true;
        metricStatus.textContent = "Generating...";
        metricStatus.className   = "metric-val status-badge-active";
        metricTime.textContent   = "Processing...";

        const payload = {
            prompt: promptText,
            negative_prompt: negPromptText,
            steps: stepsVal,
            cfg_scale: cfgVal,
            width: widthVal,
            height: heightVal,
            seed: actualSeed
        };

        const startTime = Date.now();

        try {
            const response = await fetch(`${verifiedTunnelUrl}/api/generate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": verifiedApiKey
                },
                body: JSON.stringify(payload)
            });

            const totalClientSeconds = ((Date.now() - startTime) / 1000).toFixed(2);

            if (response.ok) {
                const data = await response.json();
                const imgB64 = data.image_base64;
                const latency = data.latency_seconds || totalClientSeconds;
                const device = data.device || "GPU";

                if (imgB64) {
                    // Display image
                    generatedImage.src = `data:image/png;base64,${imgB64}`;
                    generatedImage.style.display = "block";
                    imagePlaceholder.style.display = "none";

                    // Update Metrics
                    metricHardware.textContent   = device.toUpperCase();
                    metricTime.textContent       = `${latency}s (total ${totalClientSeconds}s)`;
                    metricResolution.textContent = `${widthVal}x${heightVal}`;
                    metricStatus.textContent     = "Completed";
                    metricStatus.className       = "metric-val status-badge-success";
                } else {
                    throw new Error("Respon server tidak memuat data gambar.");
                }

            } else if (response.status === 401) {
                alert("401 Unauthorized: API Key ditolak saat pembuatan gambar!");
                metricStatus.textContent = "401 Unauthorized";
                metricStatus.className   = "metric-val status-badge-idle";
            } else if (response.status === 503) {
                alert("503 Service Unavailable: Model di server lokal masih loading. Coba beberapa saat lagi.");
                metricStatus.textContent = "Model Loading...";
            } else {
                let errDetail = "Terjadi kesalahan";
                try {
                    const errJson = await response.json();
                    errDetail = errJson.detail || errJson.error || JSON.stringify(errJson);
                } catch (e) {
                    errDetail = await response.text();
                }
                alert(`Gagal membuat gambar: ${errDetail}`);
                metricStatus.textContent = "Error";
            }

        } catch (err) {
            alert(`Network / Generation Error: ${err.message}`);
            metricStatus.textContent = "Failed";
            metricTime.textContent   = "-";
        } finally {
            btnGenerate.classList.remove("btn-loading");
            btnGenerate.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Image Enlargement / Lightbox Modal
    // -------------------------------------------------------------------------
    imageDisplayBox.addEventListener("click", () => {
        if (generatedImage.style.display !== "none" && generatedImage.src) {
            modalImg.src = generatedImage.src;
            imageModal.classList.add("open");
            imageModal.setAttribute("aria-hidden", "false");
        }
    });

    function closeModal() {
        imageModal.classList.remove("open");
        imageModal.setAttribute("aria-hidden", "true");
    }

    modalClose.addEventListener("click", closeModal);
    modalBackdrop.addEventListener("click", closeModal);
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && imageModal.classList.contains("open")) {
            closeModal();
        }
    });
});