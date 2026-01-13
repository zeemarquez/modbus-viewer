# Building Modbus Viewer Executable

This guide explains how to build a standalone Windows executable for Modbus Viewer.

## Prerequisites

1. Python 3.8 or higher installed
2. Virtual environment (recommended)

## Setup

1. **Create and activate virtual environment** (if not already done):
   ```batch
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```batch
   pip install -r requirements.txt
   ```

## Building the Executable

### Option 1: Using the Build Script (Recommended)

Simply run:
```batch
build_viewer.bat
```

This script will:
- Check for virtual environment
- Install PyInstaller if needed
- Clean previous builds
- Build the executable
- Output to `dist\ModbusViewer\ModbusViewer.exe`

### Option 2: Manual Build

1. **Activate virtual environment**:
   ```batch
   venv\Scripts\activate
   ```

2. **Install PyInstaller** (if not already installed):
   ```batch
   pip install pyinstaller
   ```

3. **Build using the spec file**:
   ```batch
   pyinstaller viewer.spec --clean --noconfirm
   ```

## Output

After building, you'll find:
- **Executable**: `dist\ModbusViewer\ModbusViewer.exe`
- **Support files**: All required DLLs and data files in the `dist\ModbusViewer\` folder

## Distribution

To distribute the application:

1. **Copy the entire `dist\ModbusViewer\` folder** to the target machine
2. The folder contains everything needed to run the application
3. Users can run `ModbusViewer.exe` directly

## Creating an Installer (Optional)

For a more professional distribution, you can create an installer using:

- **Inno Setup** (free, recommended for Windows)
- **NSIS** (Nullsoft Scriptable Install System)
- **WiX Toolset** (Microsoft's installer tool)

### Example Inno Setup Script

```inno
[Setup]
AppName=Modbus Viewer
AppVersion=1.0
DefaultDirName={pf}\ModbusViewer
DefaultGroupName=Modbus Viewer
OutputDir=installer

[Files]
Source: "dist\ModbusViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Modbus Viewer"; Filename: "{app}\ModbusViewer.exe"
Name: "{commondesktop}\Modbus Viewer"; Filename: "{app}\ModbusViewer.exe"
```

## Troubleshooting

### Build Fails

1. **Check Python version**: Ensure Python 3.8+ is installed
2. **Reinstall dependencies**: `pip install --upgrade -r requirements.txt`
3. **Clean build**: Delete `build` and `dist` folders, then rebuild

### Executable Doesn't Run

1. **Check Windows Defender**: May block unsigned executables
2. **Check dependencies**: Ensure all DLLs are included
3. **Run from command line**: Check for error messages

### Missing Modules

If you get "ModuleNotFoundError", add the module to `hiddenimports` in `viewer.spec`:
```python
hiddenimports=[
    ...
    'your_missing_module',
]
```

## Notes

- The executable is built as a **one-folder** distribution (not single-file) for better compatibility
- All resources (images, configs) are stored relative to the executable
- The `resources` folder will be created automatically when the app runs
- First run may be slower as PyInstaller extracts files to a temp directory
