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

REM Use pythonw.exe to run the GUI without a console window
start "" "venv\Scripts\pythonw.exe" main.py

REM The console window will close immediately after launching the app
exit

