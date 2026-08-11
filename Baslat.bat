@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        py -3 run.py
    ) else (
        python run.py
    )
)

if errorlevel 1 (
    echo.
    echo Baslatma basarisiz oldu. Python 3.9+ ve Ollama kurulumunu kontrol edin.
    pause
)
