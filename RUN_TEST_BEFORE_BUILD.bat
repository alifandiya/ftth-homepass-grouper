@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo Test run aplikasi sebelum build EXE...
echo.
py -3.14 -m pip install --upgrade customtkinter
if errorlevel 1 goto FAIL
py -3.14 run_homepass.py
exit /b 0

:FAIL
echo.
echo [GAGAL] Test run tidak berhasil. Pastikan Python 3.14 64-bit tersedia.
pause
exit /b 1
