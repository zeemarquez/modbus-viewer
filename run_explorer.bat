@echo off
setlocal
cd /d %~dp0

REM Check if virtual environment exists
if not exist "venv\Scripts\pythonw.exe" (
    echo Virtual environment not found in 'venv' folder.
    echo Please ensure the project is set up correctly.
    pause
    exit /b
)

REM Launch Modbus Explorer
start "" "venv\Scripts\pythonw.exe" explorer_main.py

exit
