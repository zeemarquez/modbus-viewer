@echo off
setlocal
cd /d %~dp0

echo ========================================
echo Creating Modbus Viewer Installer
echo ========================================
echo.

REM Check if Inno Setup is installed
set INNO_SETUP="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_SETUP% (
    set INNO_SETUP="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist %INNO_SETUP% (
    echo ERROR: Inno Setup not found!
    echo.
    echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
    echo Or update the path in this script if installed elsewhere.
    echo.
    pause
    exit /b 1
)

REM Check if dist folder exists
if not exist "dist\ModbusViewer\ModbusViewer.exe" (
    echo ERROR: Executable not found!
    echo.
    echo Please build the executable first by running: build_viewer.bat
    echo.
    pause
    exit /b 1
)

echo Building installer...
%INNO_SETUP% installer_setup.iss

if errorlevel 1 (
    echo.
    echo ERROR: Installer creation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installer created successfully!
echo ========================================
echo.
echo Installer location: installer\ModbusViewer_Setup.exe
echo.
pause
