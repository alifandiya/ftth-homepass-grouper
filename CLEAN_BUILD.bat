@echo off
setlocal
cd /d "%~dp0"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist HomePass_error_log.txt del /q HomePass_error_log.txt
echo Folder build/dist/cache sudah dibersihkan.
pause
