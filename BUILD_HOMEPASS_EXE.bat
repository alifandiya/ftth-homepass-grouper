@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  BUILD EXE - HomePass Group Tool
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python Launcher "py" tidak ditemukan.
    echo Install Python 3.14 64-bit dari python.org, lalu centang "Add python.exe to PATH".
    pause
    exit /b 1
)

py -3.14 -c "import sys, struct; print('Python:', sys.version); print('Bit:', struct.calcsize('P')*8); assert struct.calcsize('P')*8 == 64" 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] File .pyd ini membutuhkan Python 3.14 64-bit.
    echo Install Python 3.14 64-bit, atau compile ulang .pyd sesuai versi Python yang dipakai.
    pause
    exit /b 1
)

echo.
echo [1/4] Upgrade pip dan install dependency build...
py -3.14 -m pip install --upgrade pip
if errorlevel 1 goto FAIL

py -3.14 -m pip install --upgrade pyinstaller customtkinter
if errorlevel 1 goto FAIL

echo.
echo [2/4] Bersihkan folder build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo [3/4] Build executable dengan PyInstaller...
py -3.14 -m PyInstaller AK47_HomePass.spec --clean --noconfirm
if errorlevel 1 goto FAIL

echo.
echo [4/4] Selesai.
echo File EXE ada di:
echo %CD%\dist\HomePass_Group_Tool.exe
echo.
pause
exit /b 0

:FAIL
echo.
echo [GAGAL] Build tidak selesai. Cek pesan error di atas.
echo Tips cepat:
echo - Pastikan pakai Python 3.14 64-bit.
echo - Jalankan CMD/PowerShell sebagai Administrator jika akses folder ditolak.
echo - Pastikan koneksi internet aktif saat install pyinstaller/customtkinter.
echo.
pause
exit /b 1
