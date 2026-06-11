@echo off
setlocal
cd /d "%~dp0"

title Build HomePass Group Tool EXE

echo ==========================================================
echo  BUILD HOMEPASS GROUP TOOL - PY TO EXE
echo ==========================================================
echo.

echo [1/6] Cek Python 3.14 Windows 64-bit...
py -3.14 -c "import platform,sys; raise SystemExit(0 if platform.architecture()[0]=='64bit' else 1)" >nul 2>&1
if %errorlevel%==0 (
    set PY_CMD=py -3.14
) else (
    python -c "import sys,platform; raise SystemExit(0 if sys.version_info[:2]==(3,14) and platform.architecture()[0]=='64bit' else 1)" >nul 2>&1
    if %errorlevel%==0 (
        set PY_CMD=python
    ) else (
        echo ERROR: Python 3.14 Windows 64-bit tidak ditemukan.
        echo File .pyd yang diberikan terdeteksi CPython 3.14 Win AMD64.
        echo Install Python 3.14 64-bit, lalu jalankan ulang file ini.
        pause
        exit /b 1
    )
)
%PY_CMD% --version

echo.
echo [2/6] Buat virtual environment...
%PY_CMD% -m venv .venv
if errorlevel 1 goto BUILD_FAIL

call .venv\Scripts\activate.bat
if errorlevel 1 goto BUILD_FAIL

echo.
echo [3/6] Upgrade pip...
python -m pip install --upgrade pip
if errorlevel 1 goto BUILD_FAIL

echo.
echo [4/6] Install dependencies...
pip install -r requirements_build.txt
if errorlevel 1 goto BUILD_FAIL

echo.
echo [5/6] Bersihkan build lama...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.log 2>nul

echo.
echo [6/6] Build EXE dengan PyInstaller...
pyinstaller --clean --noconfirm HomePass_Group_Tool.spec
if errorlevel 1 goto BUILD_FAIL

echo.
echo ==========================================================
echo  BUILD SELESAI
echo  File EXE ada di: dist\HomePass_Group_Tool.exe
echo ==========================================================
echo.
pause
exit /b 0

:BUILD_FAIL
echo.
echo ==========================================================
echo  BUILD GAGAL
echo ==========================================================
echo Periksa error di atas.
echo Catatan penting: file .pyd harus cocok dengan Python 3.14 Windows 64-bit.
echo.
pause
exit /b 1
