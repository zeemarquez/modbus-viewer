#!/usr/bin/env python3
"""
Modbus Viewer - Simplified front end for basic users.
"""

import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.ui.viewer.viewer_window import ViewerWindow
from src.ui.styles import apply_dark_theme

def main():
    # Fix for Windows taskbar icon
    if sys.platform == 'win32':
        myappid = u'modbusviewer.app.viewer.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Modbus Viewer")
    app.setOrganizationName("ModbusViewer")
    
    # Apply theme
    apply_dark_theme(app)
    
    # Create and show main window
    window = ViewerWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
