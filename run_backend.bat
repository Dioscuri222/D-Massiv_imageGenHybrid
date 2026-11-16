@echo off
chcp 65001 >nul 2>&1
title Hybrid Image Generation - Backend Launcher
cd /d "%~dp0"
cls

REM -------------------------------------------------
REM  Model Selection Menu + Start FastAPI Backend
REM  All models are downloaded & cached in .\modelAI
REM -------------------------------------------------

set "HF_HOME=%~dp0modelAI"
set "HF_HUB_CACHE=%~dp0modelAI"
set "DIFFUSERS_CACHE=%~dp0modelAI"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
if "%PORT%"=="" set PORT=8000
if "%LOCAL_API_KEY%"=="" set LOCAL_API_KEY=HybridCloud

if not exist "%HF_HOME%" mkdir "%HF_HOME%"

REM Aktifkan virtual environment jika tersedia
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist "Backend\.venv\Scripts\activate.bat" (
    call "Backend\.venv\Scripts\activate.bat"
) else if exist "Backend\venv\Scripts\activate.bat" (
    call "Backend\venv\Scripts\activate.bat"
)

REM Cek apakah dependensi utama di Backend\requirements.txt sudah terinstall
python -c "import fastapi, uvicorn, diffusers, transformers, accelerate, PIL, torch" >nul 2>&1
if errorlevel 1 (
    echo ============================================================
    echo  [!] Beberapa library di Backend\requirements.txt belum terpasang.
    echo      Menginstall dependensi dari Backend\requirements.txt...
    echo ============================================================
    pip install -r "%~dp0Backend\requirements.txt"
    echo.
)

REM Cek apakah PyTorch masih versi CPU-only padahal ada GPU NVIDIA
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    python -c "import sys, torch; sys.exit(0 if torch.version.cuda else 1)" >nul 2>&1
    if errorlevel 1 (
        echo ============================================================
        echo  [!] Terdeteksi GPU NVIDIA, tetapi PyTorch yang terpasang adalah versi CPU-only!
        echo      Mengganti PyTorch ke versi CUDA GPU ^(cu132^)...
        echo ============================================================
        pip uninstall -y torch torchvision torchaudio
        pip install torch --index-url https://download.pytorch.org/whl/cu132
        echo.
    )
)

echo ============================================================
echo    HYBRID IMAGE GENERATION - LOCAL GPU BACKEND
echo    RTX 2050 4GB VRAM - Model Selector
echo    Password API Key: HybridCloud
echo ============================================================
echo.
echo  Pilih model yang ingin digunakan:
echo.
echo    [1] Stable Diffusion 1.5 (Base)       ~2.5 GB VRAM  [DEFAULT]
echo        General purpose, cepat, ringan.
echo.
echo    [2] DreamShaper 8                      ~2.5 GB VRAM
echo        Artistik tinggi, warna hidup, cocok illustration.
echo.
echo    [3] Realistic Vision 5.1               ~2.6 GB VRAM
echo        Fotorealistik - portrait, landscape, foto natural.
echo.
echo    [4] Anything V5                        ~2.5 GB VRAM
echo        Spesialis anime/manga bergaya Jepang.
echo.
echo    [5] ReV Animated                       ~2.5 GB VRAM
echo        Semi-realistik 3D/Pixar style.
echo.
echo ============================================================

set "CHOICE="
set "MODEL_KEY="
set /p CHOICE="  Masukkan pilihan [1-5] (Enter = 1/default): "

if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    set MODEL_KEY=sd-1.5
    set MODEL_NAME=Stable Diffusion 1.5
)
if "%CHOICE%"=="2" (
    set MODEL_KEY=dreamshaper-8
    set MODEL_NAME=DreamShaper 8
)
if "%CHOICE%"=="3" (
    set MODEL_KEY=realistic-vision-5.1
    set MODEL_NAME=Realistic Vision 5.1
)
if "%CHOICE%"=="4" (
    set MODEL_KEY=anything-v5
    set MODEL_NAME=Anything V5
)
if "%CHOICE%"=="5" (
    set MODEL_KEY=rev-animated
    set MODEL_NAME=ReV Animated
)

if not defined MODEL_KEY (
    echo.
    echo  [!] Pilihan tidak valid: "%CHOICE%". Menggunakan default SD 1.5.
    set MODEL_KEY=sd-1.5
    set MODEL_NAME=Stable Diffusion 1.5
)

echo.
echo  ^>^> Model terpilih: %MODEL_NAME% [%MODEL_KEY%]
echo  ^>^> Semua file model disimpan di: %HF_HOME%
echo  ^>^> Default API Key: %LOCAL_API_KEY%
echo  ^>^> Memulai server di http://0.0.0.0:%PORT% ...
echo.

python -u "%~dp0Backend\server.py"
pause
