"""
Variables panel for displaying computed variables.
"""

from typing import List

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox
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
        
        self.variables: List[Variable] = []
        self.registers: List[Register] = []
        self.evaluator = VariableEvaluator()
        
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
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Label", "Value", "Expression"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Column sizing - allow interactive resizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Label stretches
        header.setStretchLastSection(False)
        header.resizeSection(0, 100)  # Name
        header.resizeSection(2, 80)   # Value
        header.resizeSection(3, 150)  # Expression
        
        # Double-click to edit
        self.table.cellDoubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table)

    def _load_settings(self) -> None:
        """Load table settings."""
        settings = QSettings()
        header_state = settings.value("variables_panel/header_state")
        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

    def save_settings(self) -> None:
        """Save table settings."""
        settings = QSettings()
        settings.setValue("variables_panel/header_state", self.table.horizontalHeader().saveState())
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the available registers for expressions."""
        self.registers = registers
        self.evaluator.set_registers(registers)
    
    def set_variables(self, variables: List[Variable]) -> None:
        """Set the list of variables to display."""
        self.variables = [v.copy() for v in variables]
        self._rebuild_table()
    
    def get_variables(self) -> List[Variable]:
        """Get the current list of variables."""
        return [v.copy() for v in self.variables]
    
    def _rebuild_table(self) -> None:
        """Rebuild the table with current variables."""
        self.table.setRowCount(len(self.variables))
        
        for row, var in enumerate(self.variables):
            self._set_row(row, var)
    
    def _set_row(self, row: int, var: Variable) -> None:
        """Set a row in the table."""
        # Name
        name_item = QTableWidgetItem(var.name)
        name_item.setData(Qt.ItemDataRole.UserRole, var)
        self.table.setItem(row, 0, name_item)
        
        # Label
        label_item = QTableWidgetItem(var.label)
        self.table.setItem(row, 1, label_item)
        
        # Value
        value_item = QTableWidgetItem("---")
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 2, value_item)
        
        # Expression
        expr_item = QTableWidgetItem(var.expression)
        expr_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
        self.table.setItem(row, 3, expr_item)
    
    def update_values(self) -> None:
        """Update all variable values."""
        for row, var in enumerate(self.variables):
            if row >= self.table.rowCount():
                break
            
            value_item = self.table.item(row, 2)
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
        """Add a new variable."""
        dialog = VariableEditorDialog(
            variable=None,
            registers=self.registers,
            evaluator=self.evaluator,
            parent=self
        )
        
        if dialog.exec():
            var = dialog.get_variable()
            
            # Check for duplicate name
            for existing in self.variables:
                if existing.name == var.name:
                    QMessageBox.warning(
                        self, 
                        "Duplicate Name",
                        f"A variable named '{var.name}' already exists."
                    )
                    return
            
            self.variables.append(var)
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row(row, var)
            self.update_values()
            self.variables_changed.emit()
    
    def _edit_variable(self) -> None:
        """Edit selected variable."""
        rows = self.table.selectedIndexes()
        if not rows:
            return
        
        row = rows[0].row()
        if row >= len(self.variables):
            return
        
        var = self.variables[row]
        old_name = var.name
        
        dialog = VariableEditorDialog(
            variable=var,
            registers=self.registers,
            evaluator=self.evaluator,
            parent=self
        )
        
        if dialog.exec():
            new_var = dialog.get_variable()
            
            # Check for duplicate name (excluding self)
            for i, existing in enumerate(self.variables):
                if i != row and existing.name == new_var.name:
                    QMessageBox.warning(
                        self,
                        "Duplicate Name",
                        f"A variable named '{new_var.name}' already exists."
                    )
                    return
            
            self.variables[row] = new_var
            self._set_row(row, new_var)
            self.update_values()
            self.variables_changed.emit()
    
    def _remove_variable(self) -> None:
        """Remove selected variable."""
        rows = self.table.selectedIndexes()
        if not rows:
            return
        
        row = rows[0].row()
        if row >= len(self.variables):
            return
        
        var = self.variables[row]
        
        reply = QMessageBox.question(
            self,
            "Remove Variable",
            f"Remove variable '{var.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.variables[row]
            self.table.removeRow(row)
            self.variables_changed.emit()
    
    def _on_double_click(self, row: int, column: int) -> None:
        """Handle double-click on a cell."""
        self._edit_variable()

