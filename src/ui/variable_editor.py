"""
Variable editor dialog for creating/editing computed variables.
Supports multi-device with D<id>.R<addr> syntax.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPlainTextEdit, QPushButton,
    QDialogButtonBox, QLabel, QGroupBox, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt

from src.models.variable import Variable, VariableFormat
from src.models.register import Register
from src.core.variable_engine import VariableEvaluator
from src.ui.expression_highlighter import ExpressionHighlighter


class VariableEditorDialog(QDialog):
    """Dialog for creating or editing a variable with multi-device support."""
    
    def __init__(self, variable: Optional[Variable] = None, 
                 registers: List[Register] = None,
                 evaluator: VariableEvaluator = None,
                 parent=None):
        super().__init__(parent)
        
        self.variable = variable.copy() if variable else Variable(name="")
        self.registers = registers or []
        self.evaluator = evaluator or VariableEvaluator()
        
        self.setWindowTitle("Edit Variable" if variable else "New Variable")
        self.setMinimumSize(550, 450)
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
        
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g., Average Temperature")
        info_layout.addRow("Label:", self.label_edit)
        
        self.is_global_check = QCheckBox("Global Variable")
        self.is_global_check.setToolTip("Global variables can use registers from any device (D1.R0). \nNon-global variables are replicated for every device and use its own registers (R0).")
        self.is_global_check.toggled.connect(self._on_global_toggled)
        info_layout.addRow(self.is_global_check)
        
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
            "e.g., D1.R0 + D1.R1, D1.R0 * 0.5, sqrt(D1.R0**2 + D2.R0**2)"
        )
        self.expression_edit.textChanged.connect(self._on_expression_changed)
        
        # Add syntax highlighter
        self.highlighter = ExpressionHighlighter(self.expression_edit.document())
        
        expr_layout.addWidget(self.expression_edit)
        
        # Help text
        help_label = QLabel(
            "Use D<id>.R<addr> for registers (e.g., D1.R0, D2.R100). "
            "Legacy R<addr> syntax defaults to Device 1.\n"
            "Functions: abs, min, max, sqrt, round, sin, cos, tan, log, exp"
        )
        help_label.setStyleSheet("color: #757575; font-size: 11px;")
        help_label.setWordWrap(True)
        expr_layout.addWidget(help_label)
        
        # Insert register - device selector
        insert_layout = QHBoxLayout()
        
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(100)
        self._populate_device_combo()
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        insert_layout.addWidget(self.device_combo)
        
        self.register_combo = QComboBox()
        self.register_combo.setMinimumWidth(200)
        self._populate_register_combo()
        insert_layout.addWidget(self.register_combo)
        
        insert_btn = QPushButton("Insert")
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
    
    def _on_global_toggled(self, checked: bool) -> None:
        """Handle global checkbox toggle."""
        # Show/hide device selector based on global status
        self.device_combo.setVisible(checked)
        self._update_preview()
    
    def _populate_device_combo(self) -> None:
        """Populate the device selection combo."""
        self.device_combo.clear()
        
        # Get unique slave IDs from registers
        slave_ids = sorted(set(reg.slave_id for reg in self.registers))
        
        for slave_id in slave_ids:
            count = sum(1 for r in self.registers if r.slave_id == slave_id)
            self.device_combo.addItem(f"D{slave_id} ({count} regs)", slave_id)
    
    def _populate_register_combo(self) -> None:
        """Populate the register selection combo for current device."""
        self.register_combo.clear()
        
        current_device = self.device_combo.currentData()
        if current_device is None:
            return
        
        # Filter registers for selected device
        device_regs = [r for r in self.registers if r.slave_id == current_device]
        
        for reg in device_regs:
            label = reg.label if reg.label else f"Address {reg.address}"
            self.register_combo.addItem(f"R{reg.address}: {label}", reg)
    
    def _on_device_changed(self) -> None:
        """Handle device selection change."""
        self._populate_register_combo()
    
    def _populate_fields(self) -> None:
        """Populate fields from variable."""
        self.label_edit.setText(self.variable.label if self.variable.label else self.variable.name)
        self.is_global_check.setChecked(self.variable.is_global)
        self.expression_edit.setPlainText(self.variable.expression)
        
        # Set visibility
        self.device_combo.setVisible(self.variable.is_global)
        
        # Set format
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == self.variable.format:
                self.format_combo.setCurrentIndex(i)
                break
        
        self._update_preview()
    
    def _insert_register(self) -> None:
        """Insert selected register with device prefix if global."""
        reg = self.register_combo.currentData()
        
        if reg:
            cursor = self.expression_edit.textCursor()
            if self.is_global_check.isChecked():
                slave_id = self.device_combo.currentData()
                if slave_id is not None:
                    cursor.insertText(f"D{slave_id}.R{reg.address}")
            else:
                cursor.insertText(f"R{reg.address}")
            
            self.expression_edit.setFocus()
            self._update_preview()
    
    def _on_expression_changed(self) -> None:
        """Handle expression text change."""
        self._update_preview()
    
    def _update_preview(self) -> None:
        """Update the result preview."""
        expression = self.expression_edit.toPlainText().strip()
        is_global = self.is_global_check.isChecked()
        
        if not expression:
            self.result_label.setText("---")
            self.error_label.setText("")
            return
        
        # For non-global variables, we use Device 1 for preview if available
        preview_expr = expression
        if not is_global:
            # Check if there are registers to use
            if not self.registers:
                self.result_label.setText("---")
                self.error_label.setText("Add registers to preview")
                return
            
            # Map R<addr> to D<sid>.R<addr> for preview using first sid
            first_sid = sorted(set(r.slave_id for r in self.registers))[0]
            import re
            preview_expr = re.sub(r'(?<!\.)\bR(\d+)\b', f'D{first_sid}.R\\1', expression)
        
        # Validate
        error = self.evaluator.validate(preview_expr)
        if error:
            self.result_label.setText("---")
            self.error_label.setText(f"Error: {error}")
            return
        
        # Try to evaluate
        try:
            value = self.evaluator.evaluate(preview_expr)
            
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
        label = self.label_edit.text().strip()
        if not label:
            return "Label is required"
        
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
        label = self.label_edit.text().strip()
        self.variable.label = label
        # Generate name from label: lowercase, replace non-alphanumeric with underscores
        import re
        name = re.sub(r'[^a-zA-Z0-9]', '_', label).lower()
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = "v_" + name
        if not name:
            name = "var_" + str(hash(label) & 0xffff)
            
        self.variable.name = name
        self.variable.expression = self.expression_edit.toPlainText().strip()
        self.variable.format = self.format_combo.currentData()
        self.variable.is_global = self.is_global_check.isChecked()
        
        self.accept()
    
    def get_variable(self) -> Variable:
        """Get the configured variable."""
        return self.variable
