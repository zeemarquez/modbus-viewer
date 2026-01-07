"""
Register editor dialog for configuring register maps.
Supports multi-device with slave_id column.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QHeaderView,
    QAbstractItemView, QMessageBox, QDialogButtonBox, QLabel,
    QFileDialog, QWidget, QCheckBox
)
from PySide6.QtCore import Qt, QSettings
import json

from src.models.register import (
    Register, ByteOrder, DisplayFormat, AccessMode
)


class RegisterEditorDialog(QDialog):
    """Dialog for editing common register definitions."""
    
    def __init__(self, registers: List[Register], parent=None):
        super().__init__(parent)
        self.registers = [r.copy() for r in registers]  # Work on copies
        
        self.setWindowTitle("Register Editor")
        self.setMinimumSize(800, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_table()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_register)
        toolbar.addWidget(add_btn)
        
        remove_btn = QPushButton("- Remove")
        remove_btn.clicked.connect(self._remove_register)
        toolbar.addWidget(remove_btn)
        
        toolbar.addWidget(self._separator())
        
        move_up_btn = QPushButton("↑ Up")
        move_up_btn.clicked.connect(self._move_up)
        toolbar.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("↓ Down")
        move_down_btn.clicked.connect(self._move_down)
        toolbar.addWidget(move_down_btn)
        
        toolbar.addStretch()
        
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._import_registers)
        toolbar.addWidget(import_btn)
        
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._export_registers)
        toolbar.addWidget(export_btn)
        
        layout.addLayout(toolbar)
        
        # Table - 7 columns: Label, Address, Size, Byte Order, Access, Format, Fast
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Label", "Address", "Size", "Byte Order", "Access", "Format", "Fast"
        ])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        
        # Column sizing - allow interactive resizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Label stretches
        header.resizeSection(1, 70)   # Address
        header.resizeSection(2, 50)   # Size
        header.resizeSection(3, 100)  # Byte Order
        header.resizeSection(4, 80)   # Access
        header.resizeSection(5, 80)   # Format
        header.resizeSection(6, 50)   # Fast
        
        layout.addWidget(self.table)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self) -> None:
        """Load dialog settings."""
        settings = QSettings()
        
        # Restore window geometry
        geometry = settings.value("register_editor/geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # Restore header state
        header_state = settings.value("register_editor/header_state_v2")
        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

    def _save_settings(self) -> None:
        """Save dialog settings."""
        settings = QSettings()
        settings.setValue("register_editor/geometry", self.saveGeometry())
        settings.setValue("register_editor/header_state_v2", self.table.horizontalHeader().saveState())

    def done(self, result: int) -> None:
        """Override done to save settings."""
        self._save_settings()
        super().done(result)
    
    def _separator(self) -> QWidget:
        """Create a visual separator."""
        sep = QWidget()
        sep.setFixedWidth(20)
        return sep
    
    def _populate_table(self) -> None:
        """Populate table with current registers."""
        self.table.setRowCount(len(self.registers))
        
        for row, reg in enumerate(self.registers):
            self._set_row(row, reg)
    
    def _set_row(self, row: int, reg: Register) -> None:
        """Set a single row in the table."""
        # 0: Label
        label_edit = QLineEdit(reg.label)
        self.table.setCellWidget(row, 0, label_edit)
        
        # 1: Address
        addr_spin = QSpinBox()
        addr_spin.setRange(0, 65535)
        addr_spin.setValue(reg.address)
        self.table.setCellWidget(row, 1, addr_spin)
        
        # 2: Size
        size_spin = QSpinBox()
        size_spin.setRange(1, 4)
        size_spin.setValue(reg.size)
        self.table.setCellWidget(row, 2, size_spin)
        
        # 3: Byte Order
        order_combo = QComboBox()
        for bo in ByteOrder:
            order_combo.addItem(bo.value, bo)
        order_combo.setCurrentText(reg.byte_order.value)
        self.table.setCellWidget(row, 3, order_combo)
        
        # 4: Access Mode
        access_combo = QComboBox()
        for am in AccessMode:
            access_combo.addItem(am.value, am)
        access_combo.setCurrentText(reg.access_mode.value)
        self.table.setCellWidget(row, 4, access_combo)
        
        # 5: Display Format
        format_combo = QComboBox()
        for df in DisplayFormat:
            format_combo.addItem(df.value, df)
        format_combo.setCurrentText(reg.display_format.value)
        self.table.setCellWidget(row, 5, format_combo)
        
        # 6: Fast Poll checkbox
        fast_widget = QWidget()
        fast_layout = QHBoxLayout(fast_widget)
        fast_layout.setContentsMargins(0, 0, 0, 0)
        fast_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fast_check = QCheckBox()
        fast_check.setChecked(reg.fast_poll)
        fast_layout.addWidget(fast_check)
        self.table.setCellWidget(row, 6, fast_widget)
    
    def _get_row(self, row: int) -> Register:
        """Get register from a table row."""
        label_edit = self.table.cellWidget(row, 0)
        addr_spin = self.table.cellWidget(row, 1)
        size_spin = self.table.cellWidget(row, 2)
        order_combo = self.table.cellWidget(row, 3)
        access_combo = self.table.cellWidget(row, 4)
        format_combo = self.table.cellWidget(row, 5)
        fast_widget = self.table.cellWidget(row, 6)
        
        # Extract checkbox from the wrapper widget
        fast_poll = False
        if fast_widget:
            fast_check = fast_widget.findChild(QCheckBox)
            if fast_check:
                fast_poll = fast_check.isChecked()
        
        return Register(
            label=label_edit.text(),
            address=addr_spin.value(),
            size=size_spin.value(),
            byte_order=order_combo.currentData(),
            scale=1.0,  # Default scale, not editable
            access_mode=access_combo.currentData(),
            display_format=format_combo.currentData(),
            fast_poll=fast_poll,
        )
    
    def _add_register(self) -> None:
        """Add a new register definition."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Create default register
        reg = Register(
            address=row,
            label=f"Register {row + 1}"
        )
        self._set_row(row, reg)
        
        # Select new row
        self.table.selectRow(row)
    
    def _remove_register(self) -> None:
        """Remove selected register."""
        rows = self.table.selectedIndexes()
        if rows:
            row = rows[0].row()
            self.table.removeRow(row)
    
    def _move_up(self) -> None:
        """Move selected register up."""
        rows = self.table.selectedIndexes()
        if not rows:
            return
        
        row = rows[0].row()
        if row <= 0:
            return
        
        # Get both rows
        reg_current = self._get_row(row)
        reg_above = self._get_row(row - 1)
        
        # Swap
        self._set_row(row - 1, reg_current)
        self._set_row(row, reg_above)
        
        # Update selection
        self.table.selectRow(row - 1)
    
    def _move_down(self) -> None:
        """Move selected register down."""
        rows = self.table.selectedIndexes()
        if not rows:
            return
        
        row = rows[0].row()
        if row >= self.table.rowCount() - 1:
            return
        
        # Get both rows
        reg_current = self._get_row(row)
        reg_below = self._get_row(row + 1)
        
        # Swap
        self._set_row(row + 1, reg_current)
        self._set_row(row, reg_below)
        
        # Update selection
        self.table.selectRow(row + 1)
    
    def _import_registers(self) -> None:
        """Import registers from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Registers",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both project files and register-only files
            if 'registers' in data:
                reg_data = data['registers']
            elif isinstance(data, list):
                reg_data = data
            else:
                raise ValueError("Invalid register file format")
            
            # Clear and populate
            self.table.setRowCount(0)
            self.table.setRowCount(len(reg_data))
            
            for row, rd in enumerate(reg_data):
                reg = Register.from_dict(rd)
                self._set_row(row, reg)
            
            QMessageBox.information(
                self, 
                "Import Complete", 
                f"Imported {len(reg_data)} registers."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))
    
    def _export_registers(self) -> None:
        """Export registers to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Registers",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        try:
            registers = self.get_registers()
            data = [r.to_dict() for r in registers]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(registers)} registers."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def _validate(self) -> Optional[str]:
        """Validate all registers. Returns error message or None."""
        seen_addresses = set()
        
        for row in range(self.table.rowCount()):
            reg = self._get_row(row)
            
            # Check for duplicate addresses
            if reg.address in seen_addresses:
                return f"Duplicate address R{reg.address} at row {row + 1}"
            seen_addresses.add(reg.address)
        
        return None
    
    def _on_accept(self) -> None:
        """Handle OK button."""
        error = self._validate()
        if error:
            QMessageBox.warning(self, "Validation Error", error)
            return
        
        self.accept()
    
    def get_registers(self) -> List[Register]:
        """Get the configured registers."""
        registers = []
        for row in range(self.table.rowCount()):
            registers.append(self._get_row(row))
        return registers
