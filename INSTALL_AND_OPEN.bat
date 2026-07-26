@echo off
setlocal
title FM FaceStudio Alpha 0.1 Setup
cd /d "%~dp0"

echo ============================================================
echo               FM FaceStudio Alpha 0.1
echo ============================================================
echo.
pause

where py >nul 2>nul
if errorlevel 1 (
    where winget >nul 2>nul
    if errorlevel 1 (
        echo Python and Windows Package Manager were not found.
        echo Install Python 3.11 and run this file again.
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :failed
)

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
pip install -r requirements.txt
if errorlevel 1 goto :failed

start "" ".venv\Scripts\pythonw.exe" launcher.py
exit /b 0

:failed
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1
