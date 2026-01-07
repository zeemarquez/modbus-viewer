"""
Real-time table view for register values.
"""

from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QPushButton
)
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtGui import QColor, QBrush

from src.models.register import Register, AccessMode, DisplayFormat
from src.ui.styles import COLORS


class TableView(QFrame):
    """Table widget for displaying register values."""
    
    write_requested = Signal(object, float)  # register, value
    write_all_requested = Signal()  # Request to write all pending values
    edit_registers_requested = Signal()  # Request to open register editor
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.registers: List[Register] = []
        self._pending_writes: Dict[int, float] = {}  # address -> new value
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
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Label", "Address", "Size", "Value", "New Value", "Status"
        ])
        
        # Configure table
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Allow editing only on double-click
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Connect cell changed signal
        self.table.cellChanged.connect(self._on_cell_changed)
        
        # Column sizing - allow interactive resizing
        header = self.table.horizontalHeader()
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
        self.table.verticalHeader().setDefaultSectionSize(36)
        
        layout.addWidget(self.table)

    def _load_settings(self) -> None:
        """Load table settings."""
        settings = QSettings()
        header_state = settings.value("table_view/header_state")
        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

    def save_settings(self) -> None:
        """Save table settings."""
        settings = QSettings()
        settings.setValue("table_view/header_state", self.table.horizontalHeader().saveState())
    
    def _edit_registers(self) -> None:
        """Request to open register editor."""
        self.edit_registers_requested.emit()
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the list of registers to display."""
        self.registers = registers
        # Block signals during rebuild to prevent accidental writes/updates
        self.table.blockSignals(True)
        try:
            self._rebuild_table()
        finally:
            self.table.blockSignals(False)
    
    def _rebuild_table(self) -> None:
        """Rebuild the table with current registers."""
        self.table.setRowCount(len(self.registers))
        self._pending_writes.clear()
        self._update_write_button()
        
        for row, reg in enumerate(self.registers):
            # Label
            label_item = QTableWidgetItem(reg.label)
            label_item.setData(Qt.ItemDataRole.UserRole, reg)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, label_item)
            
            # Address
            addr_item = QTableWidgetItem(str(reg.address))
            addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, addr_item)
            
            # Size
            size_item = QTableWidgetItem(str(reg.size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, size_item)
            
            # Value (placeholder)
            value_item = QTableWidgetItem("---")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, value_item)
            
            # New Value (editable for writable registers)
            new_value_item = QTableWidgetItem("")
            new_value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            is_writable = reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
            if not is_writable:
                new_value_item.setFlags(new_value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                new_value_item.setForeground(QBrush(QColor(COLORS['text_disabled'])))
            self.table.setItem(row, 4, new_value_item)
            
            # Status
            status_item = QTableWidgetItem("")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, status_item)
    
    def _on_cell_changed(self, row: int, column: int) -> None:
        """Handle cell value change."""
        # Only process New Value column (4)
        if column != 4 or row >= len(self.registers):
            return
        
        # Block signals to prevent recursion if we modify the text
        self.table.blockSignals(True)
        try:
            reg = self.registers[row]
            item = self.table.item(row, column)
            if not item:
                return
            
            text = item.text().strip()
            if text:
                value = self._parse_value(text)
                if value is not None:
                    self._pending_writes[reg.address] = value
                    # Standardize the text format in the cell
                    formatted = self._format_for_input(reg, int(value))
                    if text.lower() != formatted.lower():
                        item.setText(formatted)
                else:
                    self._pending_writes.pop(reg.address, None)
            else:
                self._pending_writes.pop(reg.address, None)
            
            self._update_write_button()
        finally:
            self.table.blockSignals(False)
    
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
        for address, value in self._pending_writes.items():
            # Find register
            for reg in self.registers:
                if reg.address == address:
                    self.write_requested.emit(reg, value)
                    break
        
        # Clear pending writes and new value fields
        self._pending_writes.clear()
        self._clear_new_value_fields()
        self._update_write_button()
    
    def _clear_new_value_fields(self) -> None:
        """Clear all new value input fields."""
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)
            if item:
                item.setText("")
        self.table.blockSignals(False)
    
    def set_register_new_value(self, address: int, value: int) -> None:
        """Set a new value for a register (called from bits panel)."""
        for row, reg in enumerate(self.registers):
            if reg.address == address:
                item = self.table.item(row, 4)
                if item:
                    # Update pending writes: only if different from current value
                    self.table.blockSignals(True)
                    if reg.raw_value is not None and value == int(reg.raw_value):
                        self._pending_writes.pop(address, None)
                        item.setText("")
                    else:
                        self._pending_writes[address] = float(value)
                        # Format the value using the register's display format
                        formatted = self._format_for_input(reg, value)
                        item.setText(formatted)
                    self.table.blockSignals(False)
                    
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
        self.table.blockSignals(True)
        try:
            for row, reg in enumerate(self.registers):
                if row >= self.table.rowCount():
                    break
                
                # Value (showing scaled value)
                value_item = self.table.item(row, 3)
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
                
                # Status (column 5 now)
                status_item = self.table.item(row, 5)
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
            self.table.blockSignals(False)
    
    
    def get_selected_register(self) -> Optional[Register]:
        """Get the currently selected register."""
        rows = self.table.selectedIndexes()
        if rows:
            row = rows[0].row()
            if row < len(self.registers):
                return self.registers[row]
        return None
