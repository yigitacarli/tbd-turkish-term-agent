@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_v2.py
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        py -3 run_v2.py
    ) else (
        python run_v2.py
    )
)

if errorlevel 1 (
    echo.
    echo Baslatma basarisiz oldu. Python 3.9+ ve Ollama kurulumunu kontrol edin.
    pause
)
