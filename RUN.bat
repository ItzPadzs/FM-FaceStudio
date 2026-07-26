@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Run INSTALL_AND_OPEN.bat first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" launcher.py
