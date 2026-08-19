@echo off
setlocal
cd /d "%~dp0"

rem Bu dosya cift tiklanarak calistirilir. Turkce karakter kullanilmaz;
rem komut istemi varsayilan kod sayfasinda bozuk gorunmemesi icin.

rem --- 1) Python yorumlayicisini bul ---------------------------------------
set "PY="
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
    goto :python_bulundu
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY=py -3"
    goto :python_bulundu
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY=python"
    goto :python_bulundu
)

echo.
echo  [!] Python bulunamadi.
echo.
echo  Yapmaniz gereken:
echo    1. https://www.python.org/downloads/ adresinden Python 3.9 veya
echo       uzerini indirin.
echo    2. Kurulum ekraninda "Add Python to PATH" kutusunu MUTLAKA isaretleyin.
echo    3. Kurulum bitince bu dosyaya yeniden cift tiklayin.
echo.
pause
exit /b 1

:python_bulundu

rem --- 2) Surum yeterli mi -------------------------------------------------
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [!] Kurulu Python surumu bu program icin cok eski.
    echo      En az Python 3.9 gerekiyor.
    echo.
    pause
    exit /b 1
)

rem --- 3) Gerekli kutuphaneler var mi --------------------------------------
%PY% -c "import pdfplumber, openpyxl" >nul 2>nul
if errorlevel 1 goto :kutuphane_eksik
goto :baslat

:kutuphane_eksik
echo.
echo  [!] Gerekli kutuphaneler kurulu degil (pdfplumber, openpyxl).
echo      Bu tek seferlik bir islemdir ve internet baglantisi gerektirir.
echo.
set "CEVAP="
set /p "CEVAP=  Simdi kurulsun mu? (E/H): "
if /i not "%CEVAP%"=="E" (
    echo.
    echo  Kurulumu daha sonra su komutla yapabilirsiniz:
    echo      pip install -e .
    echo.
    pause
    exit /b 1
)
echo.
echo  Kuruluyor, lutfen bekleyin...
%PY% -m pip install -e .
if errorlevel 1 (
    echo.
    echo  [!] Kurulum basarisiz oldu. Internet baglantinizi kontrol edin
    echo      veya komut isteminde "pip install -e ." komutunu deneyin.
    echo.
    pause
    exit /b 1
)

:baslat
%PY% run.py
if errorlevel 1 (
    echo.
    echo  [!] Baslatma basarisiz oldu. Hata aciklamasi yukaridadir.
    echo.
    pause
)
