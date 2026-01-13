# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Modbus Viewer
"""

import sys
import os
from pathlib import Path

block_cipher = None

# Get the directory where this spec file is located
# When PyInstaller runs, it sets SPECPATH
spec_dir = Path(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    ['viewer_main.py'],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        (str(spec_dir / 'assets'), 'assets'),  # Include assets folder
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtOpenGL',
        'minimalmodbus',
        'serial',
        'serial.tools.list_ports',
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.graphicsItems.PlotItem',
        'pyqtgraph.graphicsItems.ViewBox',
        'numpy',
        'numpy.core._methods',
        'numpy.lib.format',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Determine icon path
icon_path = spec_dir / 'assets' / 'icon_viewer.ico'
if not icon_path.exists():
    icon_path = spec_dir / 'assets' / 'icon_viewer.png'
if not icon_path.exists():
    icon_path = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ModbusViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ModbusViewer',
)
