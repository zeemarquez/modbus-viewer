#!/usr/bin/env python3
"""
Modbus Explorer - A modern GUI for Modbus RTU communication
"""

import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.ui.styles import apply_light_theme


def get_last_project_path() -> str:
    """Get the last opened project path from settings."""
    settings = QSettings()
    path = settings.value("lastProjectPath", "")
    # Verify the file still exists
    if path and os.path.isfile(path):
        return path
    return None


def main():
    # Fix for Windows taskbar icon
    if sys.platform == 'win32':
        myappid = u'modbusviewer.app.1.0' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Modbus Explorer")
    app.setOrganizationName("ModbusExplorer")
    
    # Set window icon if it exists
    icon_paths = [
        os.path.join(os.path.dirname(__file__), "assets", "icon.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "icon.png"),
        os.path.join(os.path.dirname(__file__), "icon.ico"),
        os.path.join(os.path.dirname(__file__), "icon.png"),
    ]
    for path in icon_paths:
        if os.path.exists(path):
            app.setWindowIcon(QIcon(path))
            break
    
    # Apply light theme
    apply_light_theme(app)
    
    # Get last opened project path
    last_project = get_last_project_path()
    
    # Create and show main window
    window = MainWindow(initial_project_path=last_project)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


