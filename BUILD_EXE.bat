@echo off
setlocal
cd /d "%~dp0"
set "HOMEPASS_BUILD_DIR=%cd%"

REM Bersihkan variable Python lama agar tidak bentrok.
set PYTHONHOME=
set PYTHONPATH=

echo ==========================================================
echo  BUILD EXE - HomePass Group Tool
echo ==========================================================
echo.
echo Catatan penting:
echo - File .pyd Anda adalah cp314-win_amd64.
echo - Jadi build wajib memakai Windows 64-bit + Python 3.14 64-bit.
echo.

py -3.14 -c "import struct, sys; print('Python:', sys.version); print('Architecture:', struct.calcsize('P')*8, 'bit')"
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.14 tidak ditemukan. Install Python 3.14 64-bit dulu.
    pause
    exit /b 1
)

py -3.14 -m pip install --upgrade pip
py -3.14 -m pip install --upgrade -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

py -3.14 -m PyInstaller --noconfirm --clean HomePass_Group_Tool.spec

if exist "dist\HomePass Group Tool.exe" (
    echo.
    echo ==========================================================
    echo  BERHASIL
    echo  File EXE: %cd%\dist\HomePass Group Tool.exe
    echo ==========================================================
) else (
    echo.
    echo [ERROR] EXE belum terbentuk. Cek log error di atas.
)

pause
