@echo off
setlocal
cd /d "%~dp0"

echo Menjalankan mode test dari source folder...
py -3.14 main_launcher.py
if errorlevel 1 python main_launcher.py
pause
