@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
%PY% -m pip install --upgrade customtkinter
%PY% "AK47_HOME_PASS_GROUP_TOOL_EXE_READY.py"
pause
