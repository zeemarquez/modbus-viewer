"""
Variable editor dialog for creating/editing computed variables.
Supports multi-device with D<id>.R<addr> syntax.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPlainTextEdit, QPushButton,
    QDialogButtonBox, QLabel, QGroupBox, QMessageBox, QCheckBox,
    QListWidget
)
from PySide6.QtCore import Qt

from src.models.variable import Variable, VariableFormat
from src.models.register import Register
from src.core.variable_engine import VariableEvaluator
from src.ui.expression_highlighter import ExpressionHighlighter


class RegisterInsertDialog(QDialog):
    """Dialog to select device + register for expression insertion."""

    def __init__(self, registers: List[Register], parent=None):
        super().__init__(parent)

        self.setWindowTitle("Insert Register")
        self.setMinimumSize(420, 180)
        self.setModal(True)

        self.registers = registers or []

        self.selected_slave_id: Optional[int] = None
        self.selected_register: Optional[Register] = None

        self._setup_ui()
        self._populate_device_combo()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel("Select a device and register:")
        info.setStyleSheet("color: #757575; font-size: 11px;")
        layout.addWidget(info)

        combos_layout = QFormLayout()
        combos_layout.setSpacing(8)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(140)
        self.device_combo.currentIndexChanged.connect(self._populate_register_combo)
        combos_layout.addRow("Device:", self.device_combo)

        self.register_combo = QComboBox()
        self.register_combo.setMinimumWidth(250)
        combos_layout.addRow("Register:", self.register_combo)

        layout.addLayout(combos_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_device_combo(self) -> None:
        self.device_combo.clear()
        slave_ids = sorted(set(r.slave_id for r in self.registers))

        for sid in slave_ids:
            count = sum(1 for r in self.registers if r.slave_id == sid)
            self.device_combo.addItem(f"D{sid} ({count} regs)", sid)

        if self.device_combo.count() > 0:
            self.device_combo.setCurrentIndex(0)
            self._populate_register_combo()

    def _populate_register_combo(self) -> None:
        self.register_combo.clear()

        current_device = self.device_combo.currentData()
        if current_device is None:
            return

        device_regs = [r for r in self.registers if r.slave_id == current_device]
        for reg in device_regs:
            label = reg.label if reg.label else f"Address {reg.address}"
            self.register_combo.addItem(f"R{reg.address}: {label}", reg)

        if self.register_combo.count() > 0:
            self.register_combo.setCurrentIndex(0)

    def _on_accept(self) -> None:
        self.selected_slave_id = self.device_combo.currentData()
        self.selected_register = self.register_combo.currentData()
        self.accept()

    def get_selection(self) -> tuple[Optional[int], Optional[Register]]:
        return self.selected_slave_id, self.selected_register


class FunctionInsertDialog(QDialog):
    """Dialog to select a supported function to insert into an expression."""

    def __init__(self, functions: List[str], parent=None):
        super().__init__(parent)

        self.setWindowTitle("Insert Function")
        self.setMinimumSize(320, 280)
        self.setModal(True)

        self._functions = functions or []
        self._selected_function_upper: Optional[str] = None

        self._setup_ui()
        self._populate()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        info = QLabel("Select a function:")
        info.setStyleSheet("color: #757575; font-size: 11px;")
        root_layout.addWidget(info)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(12)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setMinimumWidth(150)
        self.list_widget.currentItemChanged.connect(self._on_function_selected)
        main_layout.addWidget(self.list_widget, stretch=1)

        # Right-side details panel (simple and “spreadsheet-like”).
        self.details_panel = QGroupBox("Details")
        self.details_panel.setStyleSheet(
            "QGroupBox { border: 1px solid #e0e0e0; border-radius: 6px; background: #fafafa; margin-top: 8px; }"
        )
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setSpacing(8)
        details_layout.setContentsMargins(10, 12, 10, 10)

        self.func_name_label = QLabel("—")
        self.func_name_label.setStyleSheet("font-weight: 800; font-size: 12px;")
        details_layout.addWidget(self.func_name_label)

        self.func_desc_label = QLabel("")
        self.func_desc_label.setWordWrap(True)
        self.func_desc_label.setStyleSheet("color: #444; font-size: 11px;")
        details_layout.addWidget(self.func_desc_label)

        self.example_header_label = QLabel("Usage:")
        self.example_header_label.setStyleSheet("color: #666; font-size: 11px; font-weight: 600;")
        details_layout.addWidget(self.example_header_label)

        self.func_example_label = QLabel("")
        self.func_example_label.setWordWrap(True)
        self.func_example_label.setStyleSheet(
            "background: #ffffff; border: 1px solid #e6e6e6; border-radius: 4px; padding: 6px;"
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        details_layout.addWidget(self.func_example_label)

        main_layout.addWidget(self.details_panel, stretch=2)
        root_layout.addLayout(main_layout, stretch=1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)

    def _populate(self) -> None:
        self.list_widget.clear()

        for fn in self._functions:
            self.list_widget.addItem(fn.upper())

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _on_accept(self) -> None:
        item = self.list_widget.currentItem()
        self._selected_function_upper = item.text() if item else None
        self.accept()

    def get_selected_function(self) -> Optional[str]:
        return self._selected_function_upper

    def _on_function_selected(self, current, _previous) -> None:
        fn_upper = current.text() if current else None
        self._set_details(fn_upper)

    def _set_details(self, fn_upper: Optional[str]) -> None:
        # Function docs keyed by uppercase names (inserted by the dialog).
        function_docs: dict[str, tuple[str, str]] = {
            "ABS": ("Absolute value.", "ABS(D1.R0)"),
            "MIN": ("Minimum of two values.", "MIN(D1.R0, D1.R1)"),
            "MAX": ("Maximum of two values.", "MAX(D1.R0, D1.R1)"),
            "SQRT": ("Square root. Argument must be non-negative.", "SQRT(D1.R0)"),
            "ROUND": ("Round a number (optional decimals).", "ROUND(D1.R0)"),
            "INT": ("Convert to integer.", "INT(D1.R0)"),
            "FLOAT": ("Convert to float.", "FLOAT(D1.R0)"),
            "POW": ("Raise to a power.", "POW(D1.R0, 2)"),
            "SIN": ("Sine (argument is in radians).", "SIN(D1.R0)"),
            "COS": ("Cosine (argument is in radians).", "COS(D1.R0)"),
            "TAN": ("Tangent (argument is in radians).", "TAN(D1.R0)"),
            "LOG": ("Natural log (base e). Argument must be > 0.", "LOG(D1.R0)"),
            "LOG10": ("Base-10 log. Argument must be > 0.", "LOG10(D1.R0)"),
            "EXP": ("Exponential e^x.", "EXP(D1.R0)"),
            "AVG": ("Average of a register over the last N samples (buffered over time).", "AVG(D1.R0, 10)"),
            "STD": ("Standard deviation of a register over the last N samples (buffered over time).", "STD(D1.R0, 10)"),
        }

        if not fn_upper:
            self.func_name_label.setText("—")
            self.func_desc_label.setText("")
            self.example_header_label.setText("Usage:")
            self.func_example_label.setText("")
            return

        desc, example = function_docs.get(fn_upper, ("", f"{fn_upper}(...)"))
        self.func_name_label.setText(fn_upper)
        self.func_desc_label.setText(desc)
        self.func_example_label.setText(example)


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
            "e.g., D1.R0 + D1.R1, D1.R0 * 0.5, SQRT(D1.R0**2 + D2.R0**2)"
        )
        self.expression_edit.textChanged.connect(self._on_expression_changed)
        
        # Add syntax highlighter
        self.highlighter = ExpressionHighlighter(self.expression_edit.document())
        
        expr_layout.addWidget(self.expression_edit)
        
        # Buttons to insert helpful snippets into the expression.
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        insert_register_btn = QPushButton("Insert register")
        insert_register_btn.clicked.connect(self._open_insert_register_dialog)
        buttons_layout.addWidget(insert_register_btn)

        insert_function_btn = QPushButton("Insert function")
        insert_function_btn.clicked.connect(self._open_insert_function_dialog)
        buttons_layout.addWidget(insert_function_btn)

        buttons_layout.addStretch()
        expr_layout.addLayout(buttons_layout)

        # Help text
        help_label = QLabel(
            "Use D<id>.R<addr> for registers (e.g., D1.R0, D2.R100). "
            "Legacy R<addr> syntax defaults to Device 1.\n"
            "Functions: ABS, MIN, MAX, SQRT, ROUND, INT, FLOAT, POW, "
            "SIN, COS, TAN, LOG, LOG10, EXP, AVG, STD\n"
            "Buffering: AVG(D1.R0, N), STD(D1.R0, N)"
        )
        help_label.setStyleSheet("color: #757575; font-size: 11px;")
        help_label.setWordWrap(True)
        expr_layout.addWidget(help_label)
        
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
        self._update_preview()
    
    def _populate_fields(self) -> None:
        """Populate fields from variable."""
        self.label_edit.setText(self.variable.label if self.variable.label else self.variable.name)
        self.is_global_check.setChecked(self.variable.is_global)
        self.expression_edit.setPlainText(self.variable.expression)
        
        # Set format
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == self.variable.format:
                self.format_combo.setCurrentIndex(i)
                break
        
        self._update_preview()
    
    def _open_insert_register_dialog(self) -> None:
        """Open a dialog to insert a register reference into the expression."""
        if not self.registers:
            QMessageBox.information(
                self,
                "No Registers",
                "Add registers before inserting them into an expression.",
            )
            return

        dialog = RegisterInsertDialog(registers=self.registers, parent=self)
        if not dialog.exec():
            return

        slave_id, reg = dialog.get_selection()
        if slave_id is None or reg is None:
            return

        cursor = self.expression_edit.textCursor()
        if self.is_global_check.isChecked():
            cursor.insertText(f"D{slave_id}.R{reg.address}")
        else:
            cursor.insertText(f"R{reg.address}")

        self.expression_edit.setFocus()
        self._update_preview()

    def _open_insert_function_dialog(self) -> None:
        """Open a dialog to insert a supported function call snippet."""
        functions = sorted(getattr(self.evaluator, "FUNCTIONS", {}).keys())
        if not functions:
            return

        dialog = FunctionInsertDialog(functions=functions, parent=self)
        if not dialog.exec():
            return

        fn_upper = dialog.get_selected_function()
        if not fn_upper:
            return

        cursor = self.expression_edit.textCursor()
        cursor.insertText(f"{fn_upper}(")
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
