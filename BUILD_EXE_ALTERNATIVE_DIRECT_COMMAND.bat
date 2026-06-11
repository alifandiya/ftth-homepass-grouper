@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% -m pip install --upgrade pip
%PY% -m pip install --upgrade customtkinter pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

%PY% -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "HomePass Group Tool" ^
  --icon "LOGO_APLIKASI_ALL_SIZE.ico" ^
  --add-data "LOGO_APLIKASI_ALL_SIZE.ico;." ^
  --collect-data customtkinter ^
  "AK47_HOME_PASS_GROUP_TOOL_EXE_READY.py"

if errorlevel 1 (
    echo Build gagal. Screenshot error ini lalu kirimkan.
    pause
    exit /b 1
)

echo EXE berhasil dibuat: dist\HomePass Group Tool.exe
pause
