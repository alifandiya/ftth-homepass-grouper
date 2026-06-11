@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  BUILD EXE - HomePass Group Tool
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

echo [1/4] Mengecek Python...
%PY% --version
if errorlevel 1 (
    echo.
    echo ERROR: Python tidak ditemukan. Install Python Windows terlebih dahulu.
    pause
    exit /b 1
)

echo.
echo [2/4] Install/update dependency...
%PY% -m pip install --upgrade pip
%PY% -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Gagal install dependency. Coba Run as Administrator atau cek internet.
    pause
    exit /b 1
)

echo.
echo [3/4] Membersihkan build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [4/4] Membuat EXE one-file dengan icon all-size...
%PY% -m PyInstaller --clean --noconfirm AK47_HOME_PASS_GROUP_TOOL_ONEFILE.spec
if errorlevel 1 (
    echo.
    echo ERROR: Build EXE gagal. Screenshot bagian error ini lalu kirimkan.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SELESAI
echo  File EXE ada di:
echo  %cd%\dist\HomePass Group Tool.exe
echo ============================================================
echo.
pause
