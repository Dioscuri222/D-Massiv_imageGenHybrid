@echo off
chcp 65001 >nul 2>&1
title Frontend HTML Server - Hybrid Image Generation
cd /d "%~dp0"
echo ========================================================
echo   Launching Frontend HTML Server on http://localhost:7860
echo ========================================================
start http://localhost:7860
python -m http.server 7860 --directory "%~dp0frontend\html"
pause
