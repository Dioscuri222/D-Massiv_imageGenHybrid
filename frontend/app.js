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

        // Allow localhost fallback only when opened locally
        let cleanUrl = getNormalizedUrl(rawUrl);
        if (!cleanUrl) {
            const isLocalHost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
            if (isLocalHost) {
                cleanUrl = "http://127.0.0.1:8000";
                tunnelUrlInput.value = cleanUrl;
            } else {
                isConnected = false;
                verifiedApiKey = "";
                lockStep2();
                statusBox.className = "status-box status-error";
                statusMessage.textContent = "URL Tunnel Gateway wajib diisi!";
                tunnelUrlInput.focus();
                return;
            }
        }

        if (!apiKey) {
            isConnected = false;
            verifiedApiKey = "";
            lockStep2();
            statusBox.className = "status-box status-error";
            statusMessage.textContent = "Custom API Key wajib diisi!";
            apiKeyInput.focus();
            return;
        }

        if (apiKey !== "HybridCloud") {
            isConnected = false;
            verifiedApiKey = "";
            lockStep2();
            statusBox.className = "status-box status-error";
            statusMessage.textContent = "401 Unauthorized: Custom API Key salah! Gunakan password yang benar.";
            apiKeyInput.focus();
            return;
        }

        // Set Loading UI
        btnVerifyKey.classList.add("btn-loading");
        btnVerifyKey.disabled = true;
        statusBox.className = "status-box status-idle";
        statusMessage.textContent = "Memverifikasi API Key & menghubungi workstation GPU lokal...";

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 12000);

            const headers = {
                "Accept": "application/json",
                "X-API-Key": apiKey,
                "ngrok-skip-browser-warning": "true"
            };

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
                isConnected = false;
                verifiedApiKey = "";
                lockStep2();
                statusBox.className = "status-box status-error";
                statusMessage.textContent = "401 Unauthorized: Custom API Key salah atau ditolak oleh server lokal.";
            } else {
                isConnected = false;
                verifiedApiKey = "";
                lockStep2();
                statusBox.className = "status-box status-error";
                statusMessage.textContent = `Error HTTP ${response.status}: ${response.statusText}`;
            }

        } catch (err) {
            isConnected = false;
            verifiedApiKey = "";
            lockStep2();
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
    // Lock / Unlock Step 2 Helpers
    // -------------------------------------------------------------------------
    function lockStep2() {
        document.body.classList.add("is-locked-theme");
        step2Card.classList.add("locked-state");
        step2Card.classList.remove("unlocked-celebration");
        if (step2LockShield) {
            step2LockShield.style.display = "";
            step2LockShield.style.opacity = "1";
        }
        promptInput.disabled      = true;
        negPromptInput.disabled   = true;
        stepsSlider.disabled      = true;
        cfgSlider.disabled        = true;
        resolutionSelect.disabled = true;
        seedInput.disabled        = true;
        btnGenerate.disabled      = true;
    }

    // -------------------------------------------------------------------------
    // Wave Animation & Step 2 Unlock Sequence
    // -------------------------------------------------------------------------
    function triggerWaveUnlock() {
        // 1. Play Center-Expanding Golden Radial Wave Animation
        waveOverlay.style.display = "none";
        void waveOverlay.offsetWidth; // restart CSS animation on re-verify
        waveOverlay.style.display = "block";
        setTimeout(() => {
            waveOverlay.style.display = "none";
        }, 1500);

        // 2. Restore full color & unlock Step 2 as the golden wave expands (~260ms)
        setTimeout(() => {
            document.body.classList.remove("is-locked-theme");

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
                    "X-API-Key": verifiedApiKey,
                    "ngrok-skip-browser-warning": "true"
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

    // -------------------------------------------------------------------------
    // Ambient Background: Flowing Isolines + Pointer-Reactive Aura
    // -------------------------------------------------------------------------
    initAmbientBackground();

    function initAmbientBackground() {
        const canvas = document.getElementById("isolines-canvas");
        if (!canvas || !canvas.getContext) return;

        const ctx = canvas.getContext("2d");
        const cards = Array.from(document.querySelectorAll(".panel-card"));
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        let width = 0;
        let height = 0;
        let dpr = 1;

        const pointer = {
            targetX: window.innerWidth * 0.5,
            targetY: window.innerHeight * 0.5,
            x: window.innerWidth * 0.5,
            y: window.innerHeight * 0.5,
            active: false,
            strength: 0,
            bgAuraStrength: 0
        };

        let activeCard = null;

        function resizeCanvas() {
            dpr = Math.min(window.devicePixelRatio || 1, 2);
            width = window.innerWidth;
            height = window.innerHeight;
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        resizeCanvas();
        window.addEventListener("resize", () => {
            resizeCanvas();
            if (reducedMotion) drawIsolines(0);
        });

        window.addEventListener("pointermove", (e) => {
            pointer.targetX = e.clientX;
            pointer.targetY = e.clientY;
            pointer.active = true;
        }, { passive: true });

        document.addEventListener("pointerleave", () => {
            pointer.active = false;
            if (activeCard) {
                activeCard.classList.remove("has-aura");
                activeCard = null;
            }
        });

        function addRoundedRectPath(c, x, y, w, h, r) {
            const radius = Math.min(r, w / 2, h / 2);
            c.moveTo(x + radius, y);
            c.lineTo(x + w - radius, y);
            c.quadraticCurveTo(x + w, y, x + w, y + radius);
            c.lineTo(x + w, y + h - radius);
            c.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
            c.lineTo(x + radius, y + h);
            c.quadraticCurveTo(x, y + h, x, y + h - radius);
            c.lineTo(x, y + radius);
            c.quadraticCurveTo(x, y, x + radius, y);
            c.closePath();
        }

        function updateCardAura() {
            if (!pointer.active) {
                if (activeCard) {
                    activeCard.classList.remove("has-aura");
                    activeCard = null;
                }
                return false;
            }

            let hitCard = null;
            for (const card of cards) {
                const rect = card.getBoundingClientRect();
                if (
                    pointer.x >= rect.left &&
                    pointer.x <= rect.right &&
                    pointer.y >= rect.top &&
                    pointer.y <= rect.bottom
                ) {
                    hitCard = card;
                    card.style.setProperty("--card-aura-x", `${(pointer.x - rect.left).toFixed(1)}px`);
                    card.style.setProperty("--card-aura-y", `${(pointer.y - rect.top).toFixed(1)}px`);
                    break;
                }
            }

            if (activeCard && activeCard !== hitCard) {
                activeCard.classList.remove("has-aura");
            }
            if (hitCard) {
                hitCard.classList.add("has-aura");
            }
            activeCard = hitCard;
            return Boolean(hitCard);
        }

        function drawBackgroundAura() {
            if (pointer.bgAuraStrength <= 0.005) return;

            ctx.save();
            // Clip out the 2 cards so when pointer is between them, only the middle background gap is visible
            ctx.beginPath();
            ctx.rect(0, 0, width, height);
            for (const card of cards) {
                const rect = card.getBoundingClientRect();
                addRoundedRectPath(ctx, rect.left, rect.top, rect.width, rect.height, 15);
            }
            ctx.clip("evenodd");

            const outerRadius = 280;
            const outerGrad = ctx.createRadialGradient(
                pointer.x, pointer.y, 0,
                pointer.x, pointer.y, outerRadius
            );
            outerGrad.addColorStop(0, `rgba(0, 212, 255, ${(0.22 * pointer.bgAuraStrength).toFixed(3)})`);
            outerGrad.addColorStop(0.4, `rgba(73, 118, 140, ${(0.22 * pointer.bgAuraStrength).toFixed(3)})`);
            outerGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = outerGrad;
            ctx.beginPath();
            ctx.arc(pointer.x, pointer.y, outerRadius, 0, Math.PI * 2);
            ctx.fill();

            const innerRadius = 120;
            const innerGrad = ctx.createRadialGradient(
                pointer.x, pointer.y, 0,
                pointer.x, pointer.y, innerRadius
            );
            innerGrad.addColorStop(0, `rgba(165, 243, 252, ${(0.18 * pointer.bgAuraStrength).toFixed(3)})`);
            innerGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = innerGrad;
            ctx.beginPath();
            ctx.arc(pointer.x, pointer.y, innerRadius, 0, Math.PI * 2);
            ctx.fill();

            ctx.restore();
        }

        function drawIsolines(timeSec) {
            ctx.clearRect(0, 0, width, height);

            const lineCount = 18;
            const stepX = 22;
            const margin = 60;
            const cols = Math.ceil((width + margin * 2) / stepX) + 1;
            const auraRadius = 260;

            for (let i = 0; i < lineCount; i++) {
                const ratio = i / (lineCount - 1);
                const baseY = -height * 0.08 + ratio * (height * 1.16);
                const phase = i * 0.42;

                const distY = Math.abs(baseY - pointer.y);
                const bandGlow = pointer.bgAuraStrength * Math.max(0, 1 - distY / (auraRadius * 1.25));
                const alpha = 0.065 + (1 - Math.abs(ratio - 0.5) * 1.2) * 0.06 + bandGlow * 0.16;

                ctx.beginPath();
                ctx.lineWidth = 1 + bandGlow * 0.7;
                ctx.strokeStyle = bandGlow > 0.18
                    ? `rgba(125, 226, 255, ${Math.min(alpha, 0.36).toFixed(3)})`
                    : `rgba(148, 206, 228, ${Math.max(alpha, 0.04).toFixed(3)})`;

                for (let c = 0; c < cols; c++) {
                    const x = -margin + c * stepX;

                    const wave1 = Math.sin(x * 0.0032 + timeSec * 0.35 + phase) * 34;
                    const wave2 = Math.cos(x * 0.0068 - timeSec * 0.24 + phase * 1.4) * 16;
                    const wave3 = Math.sin((x + baseY) * 0.0021 + timeSec * 0.18) * 22;

                    let y = baseY + wave1 + wave2 + wave3;

                    if (pointer.strength > 0.005) {
                        const dx = x - pointer.x;
                        const dy = y - pointer.y;
                        const distSq = dx * dx + dy * dy;
                        if (distSq < auraRadius * auraRadius) {
                            const dist = Math.sqrt(distSq) || 1;
                            const falloff = Math.pow(1 - dist / auraRadius, 2);
                            const push = falloff * 38 * pointer.strength;
                            y += (dy / dist) * push;
                        }
                    }

                    if (c === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                ctx.stroke();
            }

            drawBackgroundAura();
        }

        function animate(now) {
            if (!document.hidden) {
                pointer.x += (pointer.targetX - pointer.x) * 0.12;
                pointer.y += (pointer.targetY - pointer.y) * 0.12;

                const isOverCard = updateCardAura();
                const targetStrength = pointer.active ? 1 : 0;
                const targetBgStrength = pointer.active && !isOverCard ? 1 : 0;

                pointer.strength += (targetStrength - pointer.strength) * 0.08;
                pointer.bgAuraStrength += (targetBgStrength - pointer.bgAuraStrength) * 0.1;

                drawIsolines(now * 0.001);
            }
            window.requestAnimationFrame(animate);
        }

        if (reducedMotion) {
            drawIsolines(0);
        } else {
            window.requestAnimationFrame(animate);
        }
    }
});