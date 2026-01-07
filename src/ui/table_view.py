"""
Real-time table view for register values with multi-device tab support.
"""

from typing import List, Optional, Dict, Tuple

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QPushButton, QTabWidget, QWidget
)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QColor, QBrush

from src.models.register import Register, AccessMode, DisplayFormat
from src.ui.styles import COLORS


class TableView(QFrame):
    """Table widget for displaying register values with device tabs."""
    
    write_requested = Signal(object, float)  # register, value
    write_all_requested = Signal()  # Request to write all pending values
    edit_registers_requested = Signal()  # Request to open register editor
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.register_definitions: List[Register] = []
        self.slave_ids: List[int] = [1]
        self._live_registers: List[Register] = []  # All live instances across all devices
        self._pending_writes: Dict[Tuple[int, int], float] = {}  # (slave_id, address) -> new value
        self._device_tables: Dict[int, QTableWidget] = {}  # slave_id -> table
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Setup the table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        add_btn = QPushButton("+ New Register")
        add_btn.clicked.connect(self._edit_registers)
        toolbar.addWidget(add_btn)
        
        toolbar.addStretch()
        
        self.write_btn = QPushButton("Write")
        self.write_btn.clicked.connect(self._write_pending)
        self.write_btn.setEnabled(False)
        toolbar.addWidget(self.write_btn)
        
        layout.addLayout(toolbar)
        
        # Tab widget for devices
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

    def _create_table(self) -> QTableWidget:
        """Create a new table widget for a device."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Label", "Address", "Size", "Value", "New Value", "Status"
        ])
        
        # Configure table
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Allow editing only on double-click
        table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        table.verticalHeader().setVisible(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Connect cell changed signal
        table.cellChanged.connect(self._on_cell_changed)
        
        # Column sizing - allow interactive resizing
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Label stretches
        header.setStretchLastSection(False)
        header.resizeSection(1, 60)   # Address
        header.resizeSection(2, 40)   # Size
        header.resizeSection(3, 100)  # Value
        header.resizeSection(4, 120)  # New Value
        header.resizeSection(5, 50)   # Status
        
        # Set row height for better editing
        table.verticalHeader().setDefaultSectionSize(36)
        
        return table

    def _load_settings(self) -> None:
        """Load table settings."""
        settings = QSettings()
        # Settings are per-table, handled in rebuild

    def save_settings(self) -> None:
        """Save table settings."""
        settings = QSettings()
        # Save first table's header state as default
        if self._device_tables:
            first_table = next(iter(self._device_tables.values()))
            settings.setValue("table_view/header_state", first_table.horizontalHeader().saveState())
    
    def _edit_registers(self) -> None:
        """Request to open register editor."""
        self.edit_registers_requested.emit()
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the common register definitions."""
        self.register_definitions = registers
        self._rebuild_tabs()
    
    def set_slave_ids(self, slave_ids: List[int]) -> None:
        """Set the connected slave IDs."""
        self.slave_ids = slave_ids
        self._rebuild_tabs()
    
    def _rebuild_tabs(self) -> None:
        """Rebuild tabs for each device using common definitions."""
        # Clear existing tabs
        self.tab_widget.clear()
        self._device_tables.clear()
        self._pending_writes.clear()
        self._live_registers = []
        self._update_write_button()
        
        # Create tab for each connected device
        for slave_id in sorted(self.slave_ids):
            table = self._create_table()
            self._device_tables[slave_id] = table
            
            # Create live instances for this device
            device_regs = []
            for reg_def in self.register_definitions:
                live_reg = reg_def.copy()
                live_reg.slave_id = slave_id
                device_regs.append(live_reg)
                self._live_registers.append(live_reg)
            
            # Block signals during rebuild
            table.blockSignals(True)
            try:
                self._populate_table(table, device_regs)
            finally:
                table.blockSignals(False)
            
            self.tab_widget.addTab(table, f"Device {slave_id}")
        
        # If no devices, add empty tab
        if not self.slave_ids:
            table = self._create_table()
            self._device_tables[0] = table
            self.tab_widget.addTab(table, "No Devices")
    
    def get_live_registers(self) -> List[Register]:
        """Get all live register instances across all devices."""
        return self._live_registers
    
    def _populate_table(self, table: QTableWidget, registers: List[Register]) -> None:
        """Populate a table with registers."""
        table.setRowCount(len(registers))
        
        for row, reg in enumerate(registers):
            # Label
            label_item = QTableWidgetItem(reg.label)
            label_item.setData(Qt.ItemDataRole.UserRole, reg)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, label_item)
            
            # Address (show with designator)
            addr_item = QTableWidgetItem(f"R{reg.address}")
            addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            addr_item.setToolTip(reg.designator)
            table.setItem(row, 1, addr_item)
            
            # Size
            size_item = QTableWidgetItem(str(reg.size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, size_item)
            
            # Value (placeholder)
            value_item = QTableWidgetItem("---")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 3, value_item)
            
            # New Value (editable for writable registers)
            new_value_item = QTableWidgetItem("")
            new_value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            is_writable = reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
            if not is_writable:
                new_value_item.setFlags(new_value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                new_value_item.setForeground(QBrush(QColor(COLORS['text_disabled'])))
            table.setItem(row, 4, new_value_item)
            
            # Status
            status_item = QTableWidgetItem("")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 5, status_item)
    
    def _get_register_from_table(self, table: QTableWidget, row: int) -> Optional[Register]:
        """Get register object from table row."""
        item = table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def _on_cell_changed(self, row: int, column: int) -> None:
        """Handle cell value change."""
        # Only process New Value column (4)
        if column != 4:
            return
        
        # Find which table triggered this
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        
        reg = self._get_register_from_table(table, row)
        if not reg:
            return
        
        # Block signals to prevent recursion if we modify the text
        table.blockSignals(True)
        try:
            item = table.item(row, column)
            if not item:
                return
            
            text = item.text().strip()
            key = (reg.slave_id, reg.address)
            
            if text:
                value = self._parse_value(text)
                if value is not None:
                    self._pending_writes[key] = value
                    # Standardize the text format in the cell
                    formatted = self._format_for_input(reg, int(value))
                    if text.lower() != formatted.lower():
                        item.setText(formatted)
                else:
                    self._pending_writes.pop(key, None)
            else:
                self._pending_writes.pop(key, None)
            
            self._update_write_button()
        finally:
            table.blockSignals(False)
    
    def _parse_value(self, text: str) -> Optional[float]:
        """Parse a value from text (supports hex 0x, binary 0b, and decimal)."""
        text = text.strip().lower()
        try:
            if text.startswith('0x'):
                return float(int(text, 16))
            elif text.startswith('0b'):
                return float(int(text, 2))
            # Try parsing as binary if it contains only 0s and 1s and is long
            elif all(c in '01' for c in text) and len(text) >= 8:
                return float(int(text, 2))
            else:
                return float(text)
        except ValueError:
            return None
    
    def _update_write_button(self) -> None:
        """Update write button state."""
        has_pending = len(self._pending_writes) > 0
        self.write_btn.setEnabled(has_pending)
        if has_pending:
            self.write_btn.setText(f"Write ({len(self._pending_writes)})")
        else:
            self.write_btn.setText("Write")
    
    def _write_pending(self) -> None:
        """Write all pending values."""
        for (slave_id, address), value in self._pending_writes.items():
            # Find register in live instances
            for reg in self._live_registers:
                if reg.slave_id == slave_id and reg.address == address:
                    self.write_requested.emit(reg, value)
                    break
        
        # Clear pending writes and new value fields
        self._pending_writes.clear()
        self._clear_new_value_fields()
        self._update_write_button()
    
    def _clear_new_value_fields(self) -> None:
        """Clear all new value input fields."""
        for table in self._device_tables.values():
            table.blockSignals(True)
            for row in range(table.rowCount()):
                item = table.item(row, 4)
                if item:
                    item.setText("")
            table.blockSignals(False)
    
    def set_register_new_value(self, slave_id: int, address: int, value: int) -> None:
        """Set a new value for a register (called from bits panel)."""
        if slave_id not in self._device_tables:
            return
        
        table = self._device_tables[slave_id]
        
        for row in range(table.rowCount()):
            reg = self._get_register_from_table(table, row)
            if reg and reg.slave_id == slave_id and reg.address == address:
                item = table.item(row, 4)
                if item:
                    key = (slave_id, address)
                    table.blockSignals(True)
                    if reg.raw_value is not None and value == int(reg.raw_value):
                        self._pending_writes.pop(key, None)
                        item.setText("")
                    else:
                        self._pending_writes[key] = float(value)
                        formatted = self._format_for_input(reg, value)
                        item.setText(formatted)
                    table.blockSignals(False)
                    self._update_write_button()
                break
    
    def _format_for_input(self, reg: Register, value: int) -> str:
        """Format value for input field based on register's display format."""
        if reg.display_format == DisplayFormat.HEX:
            if reg.size == 1:
                return f"0x{value & 0xFFFF:04X}"
            else:
                return f"0x{value & 0xFFFFFFFF:08X}"
        elif reg.display_format == DisplayFormat.BINARY:
            if reg.size == 1:
                return f"{value & 0xFFFF:016b}"
            else:
                return f"{value & 0xFFFFFFFF:032b}"
        else:
            # Decimal
            return str(int(value))
    
    def update_values(self) -> None:
        """Update displayed values from registers."""
        for slave_id, table in self._device_tables.items():
            table.blockSignals(True)
            try:
                for row in range(table.rowCount()):
                    reg = self._get_register_from_table(table, row)
                    if not reg:
                        continue
                    
                    # Value (showing scaled value)
                    value_item = table.item(row, 3)
                    if value_item:
                        if reg.scaled_value is not None:
                            value_item.setText(reg.format_value(reg.scaled_value))
                            
                            # Highlight changed values
                            if reg.has_changed():
                                value_item.setForeground(QBrush(QColor(COLORS['accent'])))
                            else:
                                value_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
                        else:
                            value_item.setText("---")
                    
                    # Status (column 5)
                    status_item = table.item(row, 5)
                    if status_item:
                        if reg.error:
                            status_item.setText("⚠")
                            status_item.setToolTip(reg.error)
                            status_item.setForeground(QBrush(QColor(COLORS['error'])))
                        else:
                            status_item.setText("✓")
                            status_item.setToolTip("")
                            status_item.setForeground(QBrush(QColor(COLORS['success'])))
            finally:
                table.blockSignals(False)
    
    def get_selected_register(self) -> Optional[Register]:
        """Get the currently selected register."""
        current_table = self.tab_widget.currentWidget()
        if isinstance(current_table, QTableWidget):
            rows = current_table.selectedIndexes()
            if rows:
                row = rows[0].row()
                return self._get_register_from_table(current_table, row)
        return None
