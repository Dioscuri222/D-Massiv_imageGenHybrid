@echo off
setlocal
chcp 65001 >nul 2>&1
title Cloudflare Secure Tunnel - Hybrid Image Generation
cd /d "%~dp0"

if "%PORT%"=="" set PORT=8000
if "%LOCAL_API_KEY%"=="" set LOCAL_API_KEY=sk-local-gpu-hybrid-2026

echo ========================================================
echo   Starting Cloudflare Tunnel to Local Backend (Port %PORT%)
echo ========================================================
echo   Local Target : http://127.0.0.1:%PORT%
echo   API Key      : %LOCAL_API_KEY%
echo ========================================================
echo Tunggu beberapa detik sampai muncul URL publik:
echo misal: https://xxxx-xxxx-xxxx.trycloudflare.com
echo.
echo Salin URL tersebut beserta API Key di atas ke Step 1
echo pada antarmuka Hugging Face Spaces / Frontend WebUI!
echo ========================================================
echo.

set "CF_PATH="

where cloudflared >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    cloudflared tunnel --url http://127.0.0.1:%PORT%
    goto :end
)

if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    set "CF_PATH=C:\Program Files (x86)\cloudflared\cloudflared.exe"
    goto :run_cf
)

if exist "C:\Program Files\cloudflared\cloudflared.exe" (
    set "CF_PATH=C:\Program Files\cloudflared\cloudflared.exe"
    goto :run_cf
)

where ngrok >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [i] cloudflared tidak ditemukan, menggunakan Ngrok...
    ngrok http %PORT%
    goto :end
)

echo [!] Cloudflared / Ngrok tidak ditemukan. Silakan install atau jalankan manual:
echo     winget install Cloudflare.cloudflared
echo     cloudflared tunnel --url http://127.0.0.1:%PORT%
pause
goto :end

:run_cf
"%CF_PATH%" tunnel --url http://127.0.0.1:%PORT%

:end
