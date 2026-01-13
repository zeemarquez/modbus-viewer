"""
Window Properties dialog for customizing window title and icon.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.utils.resources_manager import copy_image_to_resources, resolve_resource_path


class WindowPropertiesDialog(QDialog):
    """Dialog for setting window title and icon."""
    
    def __init__(self, current_title: str, current_icon_path: str, parent=None):
        super().__init__(parent)
        self.current_title = current_title
        self.current_icon_path = current_icon_path
        self.selected_icon_path = current_icon_path  # Store the selected icon path (relative)
        
        self.setWindowTitle("Window Properties")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # Window Title
        self.title_input = QLineEdit()
        self.title_input.setText(self.current_title)
        self.title_input.setPlaceholderText("Enter window title...")
        form.addRow("Window Title:", self.title_input)
        
        # Icon selection
        icon_layout = QHBoxLayout()
        self.icon_label = QLabel("No icon selected")
        self.icon_label.setStyleSheet("border: 1px solid #ccc; padding: 5px; background-color: #f5f5f5;")
        self.icon_label.setMinimumHeight(30)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_icon)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_icon)
        
        icon_layout.addWidget(self.icon_label, stretch=1)
        icon_layout.addWidget(browse_btn)
        icon_layout.addWidget(clear_btn)
        
        form.addRow("Icon:", icon_layout)
        
        layout.addLayout(form)
        
        # Update icon label with current icon if exists
        self._update_icon_label()
        
        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
    
    def _browse_icon(self):
        """Browse for an icon file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Icon File",
            "",
            "Image Files (*.png *.jpg *.jpeg *.ico *.bmp *.svg);;All Files (*)"
        )
        
        if file_path:
            # Copy icon to resources folder
            relative_path = copy_image_to_resources(file_path)
            if relative_path:
                self.selected_icon_path = relative_path
                self._update_icon_label()
            else:
                QMessageBox.warning(self, "Error", "Failed to copy icon to resources folder.")
    
    def _clear_icon(self):
        """Clear the selected icon."""
        self.selected_icon_path = ""
        self._update_icon_label()
    
    def _update_icon_label(self):
        """Update the icon label to show current selection."""
        if self.selected_icon_path:
            # Resolve the path to show the actual filename
            resolved_path = resolve_resource_path(self.selected_icon_path)
            if resolved_path and os.path.exists(resolved_path):
                # Show just the filename
                filename = os.path.basename(resolved_path)
                self.icon_label.setText(f"Icon: {filename}")
                self.icon_label.setToolTip(resolved_path)
            else:
                self.icon_label.setText("Icon: (file not found)")
                self.icon_label.setToolTip("")
        else:
            self.icon_label.setText("No icon selected")
            self.icon_label.setToolTip("")
    
    def get_title(self) -> str:
        """Get the entered window title."""
        return self.title_input.text().strip() or "Modbus Viewer"
    
    def get_icon_path(self) -> str:
        """Get the selected icon path (relative from resources folder)."""
        return self.selected_icon_path
