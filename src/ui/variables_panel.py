"""
Variables panel for displaying computed variables.
"""

from typing import List

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QColor, QBrush

from src.models.variable import Variable
from src.models.register import Register
from src.core.variable_engine import VariableEvaluator
from src.ui.variable_editor import VariableEditorDialog
from src.ui.styles import COLORS


class VariablesPanel(QFrame):
    """Panel for displaying and managing computed variables."""
    
    variables_changed = Signal()  # Emitted when variables are added/edited/removed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        self.variable_definitions: List[Variable] = []
        self.register_definitions: List[Register] = []
        self.slave_ids: List[int] = [1]
        self._live_variables: List[Variable] = []
        self.evaluator = VariableEvaluator()
        self._device_tables: Dict[int, QTableWidget] = {}  # slave_id -> table (0 for Global)
        
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
        
        add_btn = QPushButton("+ New Variable")
        add_btn.clicked.connect(self._add_variable)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_variable)
        toolbar.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_variable)
        toolbar.addWidget(remove_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Tab widget for devices + global
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

    def _create_table(self) -> QTableWidget:
        """Create a standard variable table."""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Label", "Value", "Expression"])
        
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Column sizing
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        header.resizeSection(1, 100)
        header.resizeSection(2, 200)
        
        table.cellDoubleClicked.connect(self._on_double_click)
        return table

    def set_registers(self, registers: List[Register]) -> None:
        """Set the available registers for expressions."""
        self.register_definitions = registers
        self.evaluator.set_registers(registers)
    
    def set_variables(self, variables: List[Variable]) -> None:
        """Set the list of variable definitions."""
        self.variable_definitions = [v.copy() for v in variables]
        self._rebuild_tabs()
    
    def set_slave_ids(self, slave_ids: List[int]) -> None:
        """Set the connected slave IDs and rebuild tabs."""
        self.slave_ids = slave_ids
        self._rebuild_tabs()

    def get_variables(self) -> List[Variable]:
        """Get the current variable definitions."""
        return [v.copy() for v in self.variable_definitions]

    def get_live_variables(self) -> List[Variable]:
        """Get all live variable instances across all devices."""
        return self._live_variables
    
    def _rebuild_tabs(self) -> None:
        """Rebuild tabs for Global and Per-Device variables."""
        self.tab_widget.clear()
        self._device_tables.clear()
        self._live_variables = []
        
        # 1. Global Tab
        global_table = self._create_table()
        self._device_tables[0] = global_table
        global_vars = [v for v in self.variable_definitions if v.is_global]
        
        for v in global_vars:
            live_v = v.copy()
            self._live_variables.append(live_v)
            
        self._populate_table(global_table, global_vars)
        self.tab_widget.addTab(global_table, "Global")
        
        # 2. Per-Device Tabs
        device_vars = [v for v in self.variable_definitions if not v.is_global]
        for sid in sorted(self.slave_ids):
            table = self._create_table()
            self._device_tables[sid] = table
            
            # Create live instances for this device
            current_device_live = []
            for v_def in device_vars:
                live_v = v_def.copy()
                live_v.slave_id = sid
                # Contextualize expression for this device: R<addr> -> D<sid>.R<addr>
                import re
                live_v.expression = re.sub(r'(?<!\.)\bR(\d+)\b', f'D{sid}.R\\1', v_def.expression)
                current_device_live.append(live_v)
                self._live_variables.append(live_v)
                
            self._populate_table(table, current_device_live)
            self.tab_widget.addTab(table, f"Device {sid}")

    def _populate_table(self, table: QTableWidget, variables: List[Variable]) -> None:
        """Populate a table with variables."""
        table.setRowCount(len(variables))
        for row, var in enumerate(variables):
            self._set_row(table, row, var)

    def _set_row(self, table: QTableWidget, row: int, var: Variable) -> None:
        """Set a row in a specific table."""
        # Label
        display_text = var.label if var.label else var.name
        label_item = QTableWidgetItem(display_text)
        label_item.setData(Qt.ItemDataRole.UserRole, var)
        table.setItem(row, 0, label_item)
        
        # Value
        value_item = QTableWidgetItem("---")
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        table.setItem(row, 1, value_item)
        
        # Expression
        expr_item = QTableWidgetItem(var.expression)
        expr_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
        table.setItem(row, 2, expr_item)
    
    def update_values(self) -> None:
        """Update all live variable values."""
        # Map live variables to their table positions
        for sid, table in self._device_tables.items():
            for row in range(table.rowCount()):
                var = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if not var:
                    continue
                
                value_item = table.item(row, 1)
                if value_item is None:
                    continue
                
                try:
                    value = self.evaluator.evaluate(var.expression)
                    var.value = value
                    var.error = None
                    formatted = var.format_value(value)
                    value_item.setText(formatted)
                    value_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
                except Exception as e:
                    var.value = None
                    var.error = str(e)
                    value_item.setText("Error")
                    value_item.setForeground(QBrush(QColor(COLORS['error'])))
                    value_item.setToolTip(str(e))
    
    def _add_variable(self) -> None:
        """Add a new variable definition."""
        dialog = VariableEditorDialog(
            variable=None,
            registers=self.register_definitions,
            evaluator=self.evaluator,
            parent=self
        )
        
        if dialog.exec():
            var = dialog.get_variable()
            
            # Check for duplicate name in definitions
            for existing in self.variable_definitions:
                if existing.name == var.name:
                    QMessageBox.warning(
                        self, 
                        "Duplicate Name",
                        f"A variable named '{var.name}' already exists."
                    )
                    return
            
            self.variable_definitions.append(var)
            self._rebuild_tabs()
            self.update_values()
            self.variables_changed.emit()
    
    def _edit_variable(self) -> None:
        """Edit selected variable definition."""
        current_table = self.tab_widget.currentWidget()
        if not isinstance(current_table, QTableWidget):
            return
            
        row = current_table.currentRow()
        if row < 0:
            return
            
        # Get the variable (might be a live instance)
        selected_var = current_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not selected_var:
            return
            
        # Find original definition
        var_def = next((v for v in self.variable_definitions if v.name == selected_var.name), None)
        if not var_def:
            return
            
        dialog = VariableEditorDialog(
            variable=var_def,
            registers=self.register_definitions,
            evaluator=self.evaluator,
            parent=self
        )
        
        if dialog.exec():
            new_var = dialog.get_variable()
            
            # Check for duplicate name (excluding self)
            for existing in self.variable_definitions:
                if existing != var_def and existing.name == new_var.name:
                    QMessageBox.warning(
                        self,
                        "Duplicate Name",
                        f"A variable named '{new_var.name}' already exists."
                    )
                    return
            
            # Update definition
            idx = self.variable_definitions.index(var_def)
            self.variable_definitions[idx] = new_var
            
            self._rebuild_tabs()
            self.update_values()
            self.variables_changed.emit()
    
    def _remove_variable(self) -> None:
        """Remove selected variable definition."""
        current_table = self.tab_widget.currentWidget()
        if not isinstance(current_table, QTableWidget):
            return
            
        row = current_table.currentRow()
        if row < 0:
            return
            
        selected_var = current_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not selected_var:
            return
            
        var_def = next((v for v in self.variable_definitions if v.name == selected_var.name), None)
        if not var_def:
            return
        
        reply = QMessageBox.question(
            self,
            "Remove Variable",
            f"Remove variable definition '{var_def.name}' for ALL devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.variable_definitions.remove(var_def)
            self._rebuild_tabs()
            self.variables_changed.emit()
    
    def _on_double_click(self, row: int, column: int) -> None:
        """Handle double-click on a cell."""
        self._edit_variable()

    def _load_settings(self) -> None:
        """Load table settings."""
        pass

    def save_settings(self) -> None:
        """Save table settings."""
        pass

