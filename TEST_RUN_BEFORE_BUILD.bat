@echo off
setlocal
cd /d "%~dp0"

echo Test running launcher dengan Python 3.14 64-bit...
py -3.14 launcher.py
pause
