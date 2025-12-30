"""
Variable editor dialog for creating/editing computed variables.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPlainTextEdit, QPushButton,
    QDialogButtonBox, QLabel, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from src.models.variable import Variable, VariableFormat
from src.models.register import Register
from src.core.variable_engine import VariableEvaluator
from src.ui.expression_highlighter import ExpressionHighlighter


class VariableEditorDialog(QDialog):
    """Dialog for creating or editing a variable."""
    
    def __init__(self, variable: Optional[Variable] = None, 
                 registers: List[Register] = None,
                 evaluator: VariableEvaluator = None,
                 parent=None):
        super().__init__(parent)
        
        self.variable = variable.copy() if variable else Variable(name="")
        self.registers = registers or []
        self.evaluator = evaluator or VariableEvaluator()
        
        self.setWindowTitle("Edit Variable" if variable else "New Variable")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_fields()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Basic info group
        info_group = QGroupBox("Variable Info")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., avg_temp, total_power")
        info_layout.addRow("Name:", self.name_edit)
        
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g., Average Temperature")
        info_layout.addRow("Label:", self.label_edit)
        
        self.format_combo = QComboBox()
        for fmt in VariableFormat:
            self.format_combo.addItem(self._format_display_name(fmt), fmt)
        info_layout.addRow("Format:", self.format_combo)
        
        layout.addWidget(info_group)
        
        # Expression group
        expr_group = QGroupBox("Expression")
        expr_layout = QVBoxLayout(expr_group)
        expr_layout.setSpacing(8)
        
        # Expression input with syntax highlighting
        self.expression_edit = QPlainTextEdit()
        self.expression_edit.setMaximumHeight(100)
        self.expression_edit.setPlaceholderText(
            "e.g., R0 + R1, R0 * 0.5, sqrt(R0**2 + R1**2)"
        )
        self.expression_edit.textChanged.connect(self._on_expression_changed)
        
        # Add syntax highlighter
        self.highlighter = ExpressionHighlighter(self.expression_edit.document())
        
        expr_layout.addWidget(self.expression_edit)
        
        # Help text
        help_label = QLabel(
            "Use R<address> for registers (e.g., R0, R100). "
            "Functions: abs, min, max, sqrt, round, sin, cos, tan, log, exp"
        )
        help_label.setStyleSheet("color: #757575; font-size: 11px;")
        expr_layout.addWidget(help_label)
        
        # Insert register
        insert_layout = QHBoxLayout()
        insert_layout.addWidget(QLabel("Register:"))
        
        self.register_combo = QComboBox()
        self.register_combo.setMinimumWidth(200)
        self._populate_register_combo()
        insert_layout.addWidget(self.register_combo)
        
        insert_btn = QPushButton("Insert Register")
        insert_btn.clicked.connect(self._insert_register)
        insert_layout.addWidget(insert_btn)
        
        insert_layout.addStretch()
        expr_layout.addLayout(insert_layout)
        
        layout.addWidget(expr_group)
        
        # Result preview
        result_group = QGroupBox("Preview")
        result_layout = QHBoxLayout(result_group)
        
        result_layout.addWidget(QLabel("Current value:"))
        self.result_label = QLabel("---")
        self.result_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        result_layout.addWidget(self.result_label)
        result_layout.addStretch()
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c62828; font-size: 11px;")
        result_layout.addWidget(self.error_label)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _format_display_name(self, fmt: VariableFormat) -> str:
        """Get display name for format."""
        names = {
            VariableFormat.DECIMAL: "Decimal (auto)",
            VariableFormat.FIXED_2: "Fixed 2 decimals",
            VariableFormat.FIXED_4: "Fixed 4 decimals",
            VariableFormat.SCIENTIFIC: "Scientific",
            VariableFormat.PERCENTAGE: "Percentage",
        }
        return names.get(fmt, fmt.value)
    
    def _populate_register_combo(self) -> None:
        """Populate the register selection combo."""
        self.register_combo.clear()
        for reg in self.registers:
            label = reg.label if reg.label else f"Address {reg.address}"
            self.register_combo.addItem(f"R{reg.address}: {label}", reg)
    
    def _populate_fields(self) -> None:
        """Populate fields from variable."""
        self.name_edit.setText(self.variable.name)
        self.label_edit.setText(self.variable.label)
        self.expression_edit.setPlainText(self.variable.expression)
        
        # Set format
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == self.variable.format:
                self.format_combo.setCurrentIndex(i)
                break
        
        self._update_preview()
    
    def _insert_register(self) -> None:
        """Insert selected register by address."""
        reg = self.register_combo.currentData()
        if reg:
            cursor = self.expression_edit.textCursor()
            cursor.insertText(f"R{reg.address}")
            self.expression_edit.setFocus()
            self._update_preview()
    
    def _on_expression_changed(self) -> None:
        """Handle expression text change."""
        self._update_preview()
    
    def _update_preview(self) -> None:
        """Update the result preview."""
        expression = self.expression_edit.toPlainText().strip()
        
        if not expression:
            self.result_label.setText("---")
            self.error_label.setText("")
            return
        
        # Validate
        error = self.evaluator.validate(expression)
        if error:
            self.result_label.setText("---")
            self.error_label.setText(f"Error: {error}")
            return
        
        # Try to evaluate
        try:
            value = self.evaluator.evaluate(expression)
            
            # Format with selected format
            fmt = self.format_combo.currentData()
            temp_var = Variable(name="", format=fmt)
            formatted = temp_var.format_value(value)
            
            self.result_label.setText(formatted)
            self.error_label.setText("")
        except Exception as e:
            self.result_label.setText("---")
            self.error_label.setText(f"Error: {e}")
    
    def _validate(self) -> Optional[str]:
        """Validate the variable configuration."""
        name = self.name_edit.text().strip()
        if not name:
            return "Name is required"
        
        # Check name is valid identifier
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Name must contain only letters, numbers, underscores, or hyphens"
        
        expression = self.expression_edit.toPlainText().strip()
        if not expression:
            return "Expression is required"
        
        error = self.evaluator.validate(expression)
        if error:
            return f"Invalid expression: {error}"
        
        return None
    
    def _on_accept(self) -> None:
        """Handle OK button."""
        error = self._validate()
        if error:
            QMessageBox.warning(self, "Validation Error", error)
            return
        
        # Update variable
        self.variable.name = self.name_edit.text().strip()
        self.variable.label = self.label_edit.text().strip()
        self.variable.expression = self.expression_edit.toPlainText().strip()
        self.variable.format = self.format_combo.currentData()
        
        self.accept()
    
    def get_variable(self) -> Variable:
        """Get the configured variable."""
        return self.variable
