# IMAGE GENERATION HUGGING FACE WEB UI DENGAN ARSITEKTUR HYBRID CLOUD-TO-LOCAL HARDWARE

Proyek implementasi arsitektur **Hybrid Cloud-to-Local Hardware** untuk Text-to-Image Generation (Stable Diffusion).

Arsitektur ini memisahkan **antarmuka web publik (Frontend)** yang di-deploy secara ringan di **Hugging Face Spaces** dengan **mesin inferensi (Backend)** yang dieksekusi di workstation **GPU Local**. Komunikasi antar-node diamankan melalui **Secure Tunneling (Cloudflare Tunnel / Ngrok)** dan autentikasi berbasis **Custom API Key**.

---

## 🏗️ Diagram Arsitektur

```
┌─────────────────────────────────┐
│   User Browser (Klien / Publik) │
└────────────────┬────────────────┘
                 │ HTTP / HTTPS (Web UI)
                 ▼
┌────────────────────────────────────────────────────────┐
│ Hugging Face Spaces (Frontend - Static Web UI)         │
│ - HTML5 / CSS3 / Vanilla JS (index.html, app.js)       │
│ - Step 1: Verifikasi URL Tunnel & Custom API Key       │
│ - Step 2: Prompt, Negative Prompt, Steps, CFG, Seed    │
│ - Ringan (tanpa beban komputasi GPU di cloud)          │
└────────────────┬───────────────────────────────────────┘
                 │ HTTPS (REST API + Header X-API-Key)
                 ▼
┌────────────────────────────────────────────────────────┐
│ Secure Tunnel (Cloudflare Tunnel / Ngrok)              │
│ - Public URL (misal: https://xxxx.trycloudflare.com)   │
│ - Menembus NAT/Firewall lokal tanpa port-forwarding    │
└────────────────┬───────────────────────────────────────┘
                 │ Reverse Proxy ke http://127.0.0.1:8000
                 ▼
┌────────────────────────────────────────────────────────┐
│ Workstation GPU Local (Backend - FastAPI Server)       │
│ - Framework: FastAPI + Uvicorn (Backend/server.py)     │
│ - Pipeline: PyTorch + Diffusers (Backend/pipeline.py)  │
│ - Penyimpanan Model Lokal: folder modelAI/             │
│ - Akselerasi: NVIDIA GPU Local (4GB VRAM)              │
│ - Optimasi: FP16 + Attention Slicing + VAE Slicing     │
│ - Autentikasi: Custom API Key Verification Middleware  │
│ - Respon: Base64 Encoded PNG Image + Latency Metrics   │
└────────────────────────────────────────────────────────┘
```

---

## 📁 Struktur Repositori

```
D-Massiv_imageGenHybrid/
├── Backend/
│   ├── pipeline.py            # Modul pipeline AI, manajemen VRAM, registry & hot-swap model
│   ├── server.py              # Server REST API FastAPI, CORS, dan autentikasi API Key
│   └── requirements.txt       # Dependensi backend (FastAPI, PyTorch CUDA, Diffusers, dll)
├── frontend/                  # Antarmuka WebUI yang di-upload ke Hugging Face Spaces
│   ├── index.html             # Struktur halaman Step 1 (Auth) & Step 2 (Generator)
│   ├── style.css              # Styling antarmuka, animasi wave, dan lock overlay
│   └── app.js                 # Logika verifikasi API Key, fetch API, dan lightbox hasil
├── modelAI/                   # Folder penyimpanan cache/bobot model AI lokal (di-ignore Git)
│   └── .gitkeep
├── run_backend.bat            # Launcher interaktif pemilihan model [1-5] & server backend
├── run_tunnel.bat             # Launcher Cloudflare Tunnel / Ngrok ke port 8000
├── .gitignore                 # Konfigurasi file & model besar yang diabaikan Git
└── README.md                  # Dokumentasi proyek
```

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Persiapan Akselerasi GPU Local

Pastikan dependensi backend dan PyTorch versi CUDA terpasang di workstation **GPU Local** Anda:
```powershell
pip install -r Backend/requirements.txt
```

Jika PyTorch yang terpasang masih versi CPU (`+cpu`), aktifkan dukungan CUDA untuk **GPU Local** Anda dengan menjalankan:
```powershell
pip uninstall -y torch torchvision torchaudio
pip install torch --index-url https://download.pytorch.org/whl/cu132
```
*(Catatan: Script `run_backend.bat` juga sudah dilengkapi deteksi otomatis untuk mengganti PyTorch `+cpu` ke versi CUDA).*

### 2. Menjalankan Backend Inferensi Lokal

Jalankan server backend:
- **Cara 1 (Launcher Interaktif — Rekomendasi):**
  ```powershell
  .\run_backend.bat
  ```
  Pilih model awal `[1-5]` yang ingin dimuat (`Stable Diffusion 1.5`, `DreamShaper 8`, `Realistic Vision 5.1`, `Anything V5`, atau `ReV Animated`). Seluruh model yang diunduh akan otomatis tersimpan di dalam folder `modelAI/`.
- **Cara 2 (Manual Python):**
  ```powershell
  python Backend/server.py
  ```

Server akan aktif pada `http://127.0.0.1:8000`.
- **Custom API Key Default:** `HybridCloud`
- **Status Endpoint:** `http://127.0.0.1:8000/api/status`

### 3. Mengaktifkan Secure Tunnel (Cloudflare Tunnel)

Gunakan Cloudflare Tunnel untuk menghubungkan server lokal ke internet tanpa perlu membuka port router/IP publik:
- **Cara 1:**
  ```powershell
  .\run_tunnel.bat
  ```
- **Cara 2 (Manual):**
  ```powershell
  cloudflared tunnel --url http://127.0.0.1:8000
  ```

Salin URL HTTPS publik yang muncul di terminal, contoh:
`https://example-random-subdomain.trycloudflare.com`

### 4. Menggunakan Frontend (Hugging Face Spaces / Lokal)

1. Buka antarmuka WebUI di Hugging Face Spaces Anda.
2. Pada panel **STEP 1 : AUTENTIKASI API KEY & CONNECTION**:
   - **URL Tunnel Gateway (Ngrok / Cloudflare):** Tempelkan URL publik dari Langkah 3 (misal: `https://xxxx.trycloudflare.com`).
   - **Custom API KEY:** Masukkan `HybridCloud`.
   - Klik **CEK DAN VERIFIKASI API KEY** hingga muncul status hijau terhubung dengan nama **GPU Local** Anda dan panel **STEP 2** terbuka.
3. Pada panel **STEP 2 : MAIN WORKSPACE GENERATOR**, masukkan prompt gambar, atur parameter (*Inference Step*, *CFG Scale*, *Resolusi*, *Seed*), lalu klik **Generate Image (kirim ke GPU lokal)**. Gambar akan diinferensi oleh **GPU Local** Anda dan langsung tampil di browser!

---

## 🔒 Keamanan & Penanganan Kesalahan

1. **401 Unauthorized & Penguncian Step 2:**
   Panel generator pada **Step 2** terkunci secara default. Jika permintaan tidak menyertakan `X-API-Key` yang valid (`HybridCloud`), baik frontend maupun endpoint backend (`/api/status`, `/api/switch-model`, `/api/generate`) akan menolak akses dengan status `401 Unauthorized` dan menjaga Step 2 tetap terkunci.
2. **Connection Timeout & Error Handling:**
   Jika backend lokal mati atau tunnel terputus, frontend menangani *timeout* (12 detik pada verifikasi koneksi) serta menampilkan pesan kesalahan yang jelas kepada pengguna.
3. **Optimasi VRAM 4GB (GPU Local):**
   - Menggunakan presisi `FP16` (`torch.float16`).
   - Mengaktifkan `enable_attention_slicing()` dan `enable_vae_slicing()`.
   - Pembersihan VRAM agresif (`gc.collect()` & `torch.cuda.empty_cache()`) saat melakukan *hot-swap* model.
   - Scheduler `DPMSolverMultistepScheduler` (`dpmsolver++`) menghasilkan gambar berkualitas tinggi hanya dalam 20–25 langkah inferensi dengan penggunaan VRAM sekitar ~2.5 GB.

---

## 🔄 Deployment Frontend ke Hugging Face Spaces

Untuk meng-upload atau memperbarui antarmuka di Hugging Face Spaces, cukup unggah isi folder `frontend/` (`index.html`, `style.css`, dan `app.js`) ke repositori Hugging Face Space Anda:
```bash
cd frontend
git add index.html style.css app.js
git commit -m "Update Hybrid Architecture Frontend WebUI"
git push
```
