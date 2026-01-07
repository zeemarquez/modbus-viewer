"""
Bits panel for displaying and controlling individual register bits.
"""

from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QColor, QBrush

from src.models.bit import Bit
from src.models.register import Register, AccessMode
from src.ui.bit_editor import BitEditorDialog
from src.ui.styles import COLORS


class BitsPanel(QFrame):
    """Panel for displaying and controlling individual register bits."""
    
    bits_changed = Signal()  # Emitted when bits are added/edited/removed
    bit_value_changed = Signal(int, int)  # register_address, new_register_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        self.bits: List[Bit] = []
        self.registers: List[Register] = []
        self._register_map: Dict[int, Register] = {}
        self._pending_bit_values: Dict[str, bool] = {}  # bit_name -> new_value
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        add_btn = QPushButton("+ New Bit")
        add_btn.clicked.connect(self._add_bit)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_bit)
        toolbar.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_bit)
        toolbar.addWidget(remove_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Label", "Register", "Bit", "Value", "New Value"
        ])
        
        # Table settings
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Label stretches
        header.setStretchLastSection(False)
        header.resizeSection(1, 80)   # Register
        header.resizeSection(2, 40)   # Bit
        header.resizeSection(3, 80)   # Value
        header.resizeSection(4, 80)   # New Value
        
        # Connect double-click for toggling
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        layout.addWidget(self.table, stretch=1)

    def _load_settings(self) -> None:
        """Load table settings."""
        settings = QSettings()
        header_state = settings.value("bits_panel/header_state")
        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

    def save_settings(self) -> None:
        """Save table settings."""
        settings = QSettings()
        settings.setValue("bits_panel/header_state", self.table.horizontalHeader().saveState())
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the list of available registers."""
        self.registers = registers
        self._register_map = {reg.address: reg for reg in registers}
        self.table.blockSignals(True)
        try:
            self._update_table()
        finally:
            self.table.blockSignals(False)
    
    def set_bits(self, bits: List[Bit]) -> None:
        """Set the list of bits."""
        self.bits = bits
        self._pending_bit_values.clear()
        self.table.blockSignals(True)
        try:
            self._update_table()
        finally:
            self.table.blockSignals(False)
    
    def get_bits(self) -> List[Bit]:
        """Get the current list of bits."""
        return self.bits
    
    def _update_table(self) -> None:
        """Update the table with current bits."""
        self.table.setRowCount(len(self.bits))
        
        for row, bit in enumerate(self.bits):
            # Label
            label_item = QTableWidgetItem(bit.label)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, label_item)
            
            # Register
            reg = self._register_map.get(bit.register_address)
            reg_text = f"R{bit.register_address}"
            if reg and reg.label:
                reg_text = reg.label
            reg_item = QTableWidgetItem(reg_text)
            reg_item.setFlags(reg_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, reg_item)
            
            # Bit index
            bit_idx_item = QTableWidgetItem(str(bit.bit_index))
            bit_idx_item.setFlags(bit_idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            bit_idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, bit_idx_item)
            
            # Value (current) - Use QLabel for robust styling
            value_label = QLabel("---")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.table.setCellWidget(row, 3, value_label)
            
            # New Value - Use QLabel for robust styling
            new_value_label = QLabel("")
            new_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            new_value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            new_value_label.setProperty("row", row)  # Store row index
            
            # Check if register is writable
            is_writable = reg and reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
            if not is_writable:
                new_value_label.setStyleSheet(f"background-color: #eeeeee; border: none;")
            else:
                new_value_label.setStyleSheet("background-color: transparent; border: none;")
            
            self.table.setCellWidget(row, 4, new_value_label)
        
        self._update_display()
    
    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        """Handle double-click - toggle bit on New Value column."""
        if row >= len(self.bits):
            return
        
        # Only respond to clicks on New Value column (4 now)
        if column != 4:
            return
        
        bit = self.bits[row]
        reg = self._register_map.get(bit.register_address)
        
        # Check if register is writable
        if not reg or reg.access_mode not in (AccessMode.READ_WRITE, AccessMode.WRITE):
            QMessageBox.information(
                self, "Read Only",
                f"Register '{reg.label if reg else 'Unknown'}' is read-only."
            )
            return
        
        # Get current value (either pending or from register)
        if bit.name in self._pending_bit_values:
            current_new_value = self._pending_bit_values[bit.name]
        else:
            current_new_value = bit.value if bit.value is not None else False
        
        # Toggle the value
        new_value = not current_new_value
        
        # If the new value matches the actual current value, remove from pending
        actual_value = bit.value if bit.value is not None else False
        if new_value == actual_value:
            self._pending_bit_values.pop(bit.name, None)
        else:
            self._pending_bit_values[bit.name] = new_value
        
        # Calculate new register value based on ALL bits for this register
        # Start with the last known value from the device
        current_reg_value = reg.raw_value if reg.raw_value is not None else 0
        new_reg_value = int(current_reg_value)
        
        # Apply all bits for this register that have pending values
        for b in self.bits:
            if b.register_address == reg.address:
                if b.name in self._pending_bit_values:
                    new_reg_value = b.apply_to_value(new_reg_value, self._pending_bit_values[b.name])
        
        self.bit_value_changed.emit(reg.address, new_reg_value)
        
        # Update display
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display of values."""
        for row, bit in enumerate(self.bits):
            if row >= self.table.rowCount():
                break
            
            reg = self._register_map.get(bit.register_address)
            
            # Value (current)
            value_label = self.table.cellWidget(row, 3)
            if isinstance(value_label, QLabel):
                if bit.value is not None:
                    if bit.value:
                        value_label.setText("TRUE")
                        value_label.setStyleSheet(
                            "background-color: #1976d2; color: #ffffff; font-weight: bold; border: none;"
                        )
                    else:
                        value_label.setText("FALSE")
                        value_label.setStyleSheet(
                            "background-color: #000000; color: #ffffff; font-weight: bold; border: none;"
                        )
                else:
                    value_label.setText("---")
                    value_label.setStyleSheet("background-color: transparent; color: #757575; border: none;")
            
            # New Value
            new_value_label = self.table.cellWidget(row, 4)
            if isinstance(new_value_label, QLabel):
                is_writable = reg and reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
                
                if is_writable:
                    if bit.name in self._pending_bit_values:
                        pending_value = self._pending_bit_values[bit.name]
                        if pending_value:
                            new_value_label.setText("TRUE")
                            new_value_label.setStyleSheet(
                                "background-color: #1976d2; color: #ffffff; font-weight: bold; border: none;"
                            )
                        else:
                            new_value_label.setText("FALSE")
                            new_value_label.setStyleSheet(
                                "background-color: #000000; color: #ffffff; font-weight: bold; border: none;"
                            )
                    else:
                        new_value_label.setText("")
                        new_value_label.setStyleSheet("background-color: transparent; border: none;")
                else:
                    new_value_label.setText("")
                    new_value_label.setStyleSheet("background-color: #eeeeee; border: none;")
    
    def update_values(self) -> None:
        """Update bit values from registers."""
        self.table.blockSignals(True)
        try:
            for bit in self.bits:
                reg = self._register_map.get(bit.register_address)
                if reg and reg.raw_value is not None:
                    bit.value = bit.extract_from_value(int(reg.raw_value))
                else:
                    bit.value = None
            
            self._update_display()
        finally:
            self.table.blockSignals(False)
    
    def clear_pending(self, register_address: Optional[int] = None) -> None:
        """Clear pending bit values."""
        if register_address is None:
            self._pending_bit_values.clear()
        else:
            # Only clear bits for this register
            for bit in self.bits:
                if bit.register_address == register_address:
                    self._pending_bit_values.pop(bit.name, None)
        self._update_display()
    
    def _add_bit(self) -> None:
        """Add a new bit."""
        if not self.registers:
            QMessageBox.information(
                self, "No Registers",
                "Please add registers before defining bits."
            )
            return
        
        dialog = BitEditorDialog(registers=self.registers, parent=self)
        if dialog.exec():
            bit = dialog.get_bit()
            self.bits.append(bit)
            self._update_table()
            self.bits_changed.emit()
    
    def _edit_bit(self) -> None:
        """Edit selected bit."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a bit to edit.")
            return
        
        bit = self.bits[row]
        dialog = BitEditorDialog(bit=bit, registers=self.registers, parent=self)
        if dialog.exec():
            self.bits[row] = dialog.get_bit()
            self._update_table()
            self.bits_changed.emit()
    
    def _remove_bit(self) -> None:
        """Remove selected bit."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a bit to remove.")
            return
        
        bit = self.bits[row]
        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove bit '{bit.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.bits[row]
            self._pending_bit_values.pop(bit.name, None)
            self._update_table()
            self.bits_changed.emit()
