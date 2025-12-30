"""
Bit editor dialog for creating/editing bit definitions.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox,
    QDialogButtonBox, QGroupBox, QMessageBox
)

from src.models.bit import Bit
from src.models.register import Register


class BitEditorDialog(QDialog):
    """Dialog for creating or editing a bit definition."""
    
    def __init__(self, bit: Optional[Bit] = None, 
                 registers: List[Register] = None,
                 parent=None):
        super().__init__(parent)
        
        self.bit = bit.copy() if bit else Bit(name="", register_address=0, bit_index=0)
        self.registers = registers or []
        
        self.setWindowTitle("Edit Bit" if bit else "New Bit")
        self.setMinimumSize(400, 250)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_fields()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Basic info group
        info_group = QGroupBox("Bit Definition")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., motor_running, alarm_active")
        info_layout.addRow("Name:", self.name_edit)
        
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g., Motor Running")
        info_layout.addRow("Label:", self.label_edit)
        
        # Register selection
        self.register_combo = QComboBox()
        self._populate_register_combo()
        info_layout.addRow("Register:", self.register_combo)
        
        # Bit index
        self.bit_spin = QSpinBox()
        self.bit_spin.setRange(0, 15)
        self.bit_spin.setValue(0)
        info_layout.addRow("Bit Index:", self.bit_spin)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _populate_register_combo(self) -> None:
        """Populate the register selection combo."""
        self.register_combo.clear()
        for reg in self.registers:
            label = reg.label if reg.label else f"Address {reg.address}"
            self.register_combo.addItem(f"R{reg.address}: {label}", reg.address)
    
    def _populate_fields(self) -> None:
        """Populate fields from bit."""
        self.name_edit.setText(self.bit.name)
        self.label_edit.setText(self.bit.label)
        self.bit_spin.setValue(self.bit.bit_index)
        
        # Set register selection
        for i in range(self.register_combo.count()):
            if self.register_combo.itemData(i) == self.bit.register_address:
                self.register_combo.setCurrentIndex(i)
                break
    
    def _validate(self) -> Optional[str]:
        """Validate the bit configuration."""
        name = self.name_edit.text().strip()
        if not name:
            return "Name is required"
        
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Name must contain only letters, numbers, underscores, or hyphens"
        
        if self.register_combo.currentIndex() < 0:
            return "Please select a register"
        
        return None
    
    def _on_accept(self) -> None:
        """Handle OK button."""
        error = self._validate()
        if error:
            QMessageBox.warning(self, "Validation Error", error)
            return
        
        # Update bit
        self.bit.name = self.name_edit.text().strip()
        self.bit.label = self.label_edit.text().strip()
        self.bit.register_address = self.register_combo.currentData()
        self.bit.bit_index = self.bit_spin.value()
        
        self.accept()
    
    def get_bit(self) -> Bit:
        """Get the configured bit."""
        return self.bit

