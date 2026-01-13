@echo off
setlocal
cd /d %~dp0

echo ========================================
echo Building Modbus Viewer Executable
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found in 'venv' folder.
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo   pip install pyinstaller
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Checking PyInstaller installation...
venv\Scripts\python.exe -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    venv\Scripts\pip.exe install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo Building executable...
venv\Scripts\pyinstaller.exe viewer.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\ModbusViewer\ModbusViewer.exe
echo.
echo You can now:
echo   1. Test the executable: dist\ModbusViewer\ModbusViewer.exe
echo   2. Distribute the entire 'dist\ModbusViewer' folder
echo   3. Create an installer: run create_installer.bat (requires Inno Setup)
echo.
pause
