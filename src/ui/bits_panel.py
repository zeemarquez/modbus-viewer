"""
Bits panel for displaying and controlling individual register bits.
Supports multi-device with tabs.
"""

from typing import List, Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QLabel, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QColor, QBrush

from src.models.bit import Bit
from src.models.register import Register, AccessMode
from src.ui.bit_editor import BitEditorDialog
from src.ui.styles import COLORS


class BitsPanel(QFrame):
    """Panel for displaying and controlling individual register bits with device tabs."""
    
    bits_changed = Signal()  # Emitted when bits are added/edited/removed
    bit_value_changed = Signal(int, int, int)  # slave_id, register_address, new_register_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        self.bit_definitions: List[Bit] = []
        self.register_definitions: List[Register] = []
        self.slave_ids: List[int] = [1]
        self._live_bits: List[Bit] = []
        self._register_map: Dict[Tuple[int, int], Register] = {}  # (slave_id, addr) -> register
        self._pending_bit_values: Dict[Tuple[int, str], bool] = {}  # (slave_id, bit_name) -> new_value
        self._device_tables: Dict[int, QTableWidget] = {}  # slave_id -> table
        
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
        
        # Tab widget for devices
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget, stretch=1)

    def _create_table(self) -> QTableWidget:
        """Create a new table widget for a device."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Label", "Register", "Bit", "Value", "New Value"
        ])
        
        # Table settings
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(36)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Column sizing
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Label stretches
        header.setStretchLastSection(False)
        header.resizeSection(1, 80)   # Register
        header.resizeSection(2, 40)   # Bit
        header.resizeSection(3, 80)   # Value
        header.resizeSection(4, 80)   # New Value
        
        # Connect double-click for toggling
        table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        return table

    def _load_settings(self) -> None:
        """Load table settings."""
        settings = QSettings()
        header_state = settings.value("bits_panel/header_state")
        # Applied when tables are created

    def save_settings(self) -> None:
        """Save table settings."""
        settings = QSettings()
        if self._device_tables:
            first_table = next(iter(self._device_tables.values()))
            settings.setValue("bits_panel/header_state", first_table.horizontalHeader().saveState())
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the common register definitions."""
        self.register_definitions = registers
        # We also need live registers for the register map to show labels correctly
        # This will be updated when rebuild_tabs is called with live instances
        self._rebuild_tabs()
    
    def set_bits(self, bits: List[Bit]) -> None:
        """Set the common bit definitions."""
        self.bit_definitions = bits
        self._pending_bit_values.clear()
        self._rebuild_tabs()
    
    def set_slave_ids(self, slave_ids: List[int], live_registers: List[Register]) -> None:
        """Set connected slave IDs and live registers for value lookup."""
        self.slave_ids = slave_ids
        self._register_map = {(reg.slave_id, reg.address): reg for reg in live_registers}
        self._rebuild_tabs()
    
    def get_bits(self) -> List[Bit]:
        """Get the common bit definitions."""
        return self.bit_definitions
    
    def _rebuild_tabs(self) -> None:
        """Rebuild tabs for each device using common definitions."""
        # Clear existing tabs
        self.tab_widget.clear()
        self._device_tables.clear()
        self._live_bits = []
        
        # Create tab for each device
        for slave_id in sorted(self.slave_ids):
            # Create live bits for this device
            device_bits = []
            for bit_def in self.bit_definitions:
                live_bit = bit_def.copy()
                live_bit.slave_id = slave_id
                device_bits.append(live_bit)
                self._live_bits.append(live_bit)
            
            table = self._create_table()
            self._device_tables[slave_id] = table
            
            table.blockSignals(True)
            try:
                self._populate_table(table, device_bits, slave_id)
            finally:
                table.blockSignals(False)
            
            self.tab_widget.addTab(table, f"Device {slave_id}")
        
        # If no devices, add empty tab
        if not self.slave_ids:
            table = self._create_table()
            self._device_tables[0] = table
            self.tab_widget.addTab(table, "No Devices")
    
    def get_live_bits(self) -> List[Bit]:
        """Get all live bit instances across all devices."""
        return self._live_bits
    
    def _populate_table(self, table: QTableWidget, bits: List[Bit], slave_id: int) -> None:
        """Populate a table with bits."""
        table.setRowCount(len(bits))
        
        for row, bit in enumerate(bits):
            # Label
            label_item = QTableWidgetItem(bit.label)
            label_item.setData(Qt.ItemDataRole.UserRole, bit)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, label_item)
            
            # Register
            reg = self._register_map.get((bit.slave_id, bit.register_address))
            reg_text = f"R{bit.register_address}"
            if reg and reg.label:
                reg_text = reg.label
            reg_item = QTableWidgetItem(reg_text)
            reg_item.setFlags(reg_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            reg_item.setToolTip(bit.designator)
            table.setItem(row, 1, reg_item)
            
            # Bit index
            bit_idx_item = QTableWidgetItem(str(bit.bit_index))
            bit_idx_item.setFlags(bit_idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            bit_idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, bit_idx_item)
            
            # Value (current) - Use QLabel for robust styling
            value_label = QLabel("---")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            table.setCellWidget(row, 3, value_label)
            
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
            
            table.setCellWidget(row, 4, new_value_label)
        
        self._update_display()
    
    def _get_bit_from_table(self, table: QTableWidget, row: int) -> Optional[Bit]:
        """Get bit object from table row."""
        item = table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        """Handle double-click - toggle bit on New Value column."""
        # Only respond to clicks on New Value column (4)
        if column != 4:
            return
        
        # Find which table triggered this
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        
        bit = self._get_bit_from_table(table, row)
        if not bit:
            return
        
        reg = self._register_map.get((bit.slave_id, bit.register_address))
        
        # Check if register is writable
        if not reg or reg.access_mode not in (AccessMode.READ_WRITE, AccessMode.WRITE):
            QMessageBox.information(
                self, "Read Only",
                f"Register '{reg.label if reg else 'Unknown'}' is read-only."
            )
            return
        
        # Get current value (either pending or from register)
        key = (bit.slave_id, bit.name)
        if key in self._pending_bit_values:
            current_new_value = self._pending_bit_values[key]
        else:
            current_new_value = bit.value if bit.value is not None else False
        
        # Toggle the value
        new_value = not current_new_value
        
        # If the new value matches the actual current value, remove from pending
        actual_value = bit.value if bit.value is not None else False
        if new_value == actual_value:
            self._pending_bit_values.pop(key, None)
        else:
            self._pending_bit_values[key] = new_value
        
        # Calculate new register value based on ALL bits for this register on this device
        # Start with the last known value from the device
        current_reg_value = reg.raw_value if reg.raw_value is not None else 0
        new_reg_value = int(current_reg_value)
        
        # Apply all bits for this register that have pending values
        for b in self._live_bits:
            if b.slave_id == reg.slave_id and b.register_address == reg.address:
                b_key = (b.slave_id, b.name)
                if b_key in self._pending_bit_values:
                    new_reg_value = b.apply_to_value(new_reg_value, self._pending_bit_values[b_key])
        
        self.bit_value_changed.emit(reg.slave_id, reg.address, new_reg_value)
        
        # Update display
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display of values."""
        for slave_id, table in self._device_tables.items():
            for row in range(table.rowCount()):
                bit = self._get_bit_from_table(table, row)
                if not bit:
                    continue
                
                reg = self._register_map.get((bit.slave_id, bit.register_address))
                
                # Value (current)
                value_label = table.cellWidget(row, 3)
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
                new_value_label = table.cellWidget(row, 4)
                if isinstance(new_value_label, QLabel):
                    is_writable = reg and reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
                    
                    if is_writable:
                        key = (bit.slave_id, bit.name)
                        if key in self._pending_bit_values:
                            pending_value = self._pending_bit_values[key]
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
        for bit in self._live_bits:
            reg = self._register_map.get((bit.slave_id, bit.register_address))
            if reg and reg.raw_value is not None:
                bit.value = bit.extract_from_value(int(reg.raw_value))
            else:
                bit.value = None
        
        self._update_display()
    
    def clear_pending(self, slave_id: Optional[int] = None, register_address: Optional[int] = None) -> None:
        """Clear pending bit values."""
        if slave_id is None and register_address is None:
            self._pending_bit_values.clear()
        else:
            # Only clear bits for this register
            for bit in self._live_bits:
                if bit.slave_id == slave_id and bit.register_address == register_address:
                    self._pending_bit_values.pop((bit.slave_id, bit.name), None)
        self._update_display()
    
    def _add_bit(self) -> None:
        """Add a new bit definition."""
        if not self.register_definitions:
            QMessageBox.information(
                self, "No Registers",
                "Please add registers before defining bits."
            )
            return
        
        dialog = BitEditorDialog(registers=self.register_definitions, parent=self)
        if dialog.exec():
            bit = dialog.get_bit()
            self.bit_definitions.append(bit)
            self._rebuild_tabs()
            self.bits_changed.emit()
    
    def _edit_bit(self) -> None:
        """Edit selected bit definition."""
        current_table = self.tab_widget.currentWidget()
        if not isinstance(current_table, QTableWidget):
            return
        
        row = current_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a bit to edit.")
            return
        
        live_bit = self._get_bit_from_table(current_table, row)
        if not live_bit:
            return
        
        # Find original definition
        bit_def = None
        bit_idx = -1
        for i, bd in enumerate(self.bit_definitions):
            if bd.name == live_bit.name and bd.register_address == live_bit.register_address and bd.bit_index == live_bit.bit_index:
                bit_def = bd
                bit_idx = i
                break
        
        if bit_idx < 0:
            return
        
        dialog = BitEditorDialog(bit=bit_def, registers=self.register_definitions, parent=self)
        if dialog.exec():
            self.bit_definitions[bit_idx] = dialog.get_bit()
            self._rebuild_tabs()
            self.bits_changed.emit()
    
    def _remove_bit(self) -> None:
        """Remove selected bit definition."""
        current_table = self.tab_widget.currentWidget()
        if not isinstance(current_table, QTableWidget):
            return
        
        row = current_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a bit to remove.")
            return
        
        live_bit = self._get_bit_from_table(current_table, row)
        if not live_bit:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove bit definition '{live_bit.name}' for ALL devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from definitions
            self.bit_definitions = [bd for bd in self.bit_definitions 
                                   if not (bd.name == live_bit.name and 
                                          bd.register_address == live_bit.register_address and 
                                          bd.bit_index == live_bit.bit_index)]
            
            # Remove all pending values for this bit across all devices
            for sid in self.slave_ids:
                self._pending_bit_values.pop((sid, live_bit.name), None)
                
            self._rebuild_tabs()
            self.bits_changed.emit()
