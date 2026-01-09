"""
Plot options dialog for customizing plot appearance.
Supports multi-device with designator format.
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QLabel, QGroupBox, QDialogButtonBox, QCheckBox,
    QScrollArea, QWidget, QFrame, QTabWidget
)
from PySide6.QtCore import Qt

from src.models.register import Register
from src.models.variable import Variable
from src.ui.styles import COLORS


class PlotOptionsDialog(QDialog):
    """Dialog for customizing plot options with multi-device support."""
    
    def __init__(self, line_width: float = 2.0, grid_alpha: float = 0.1, 
                 show_legend: bool = True, time_window_index: int = 2,
                 y_auto_scale: bool = True, y_min: float = 0.0, y_max: float = 100.0,
                 registers: List[Register] = None, variables: List[Variable] = None,
                 selected_registers: List[str] = None, selected_variables: List[str] = None,
                 parent=None):
        super().__init__(parent)
        
        self.line_width = line_width
        self.grid_alpha = grid_alpha
        self.show_legend = show_legend
        self.time_window_index = time_window_index
        self.y_auto_scale = y_auto_scale
        self.y_min = y_min
        self.y_max = y_max
        self.registers = registers or []
        self.variables = variables or []
        self.selected_registers = selected_registers or []  # Now list of designators
        self.selected_variables = selected_variables or []
        
        self._register_checkbox_map: Dict[tuple, QCheckBox] = {}  # (address, label) -> checkbox
        self._variable_checkbox_map: Dict[str, QCheckBox] = {}   # name -> checkbox
        
        self.setWindowTitle("Plot Options")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Create two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)
        
        # Left column - Options
        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        
        # Time window options
        time_group = QGroupBox("Time Window")
        time_layout = QFormLayout(time_group)
        time_layout.setSpacing(8)
        
        self.time_combo = QComboBox()
        self.time_combo.addItems(["1s", "5s", "10s", "30s", "1min", "2min", "5min"])
        self.time_combo.setCurrentIndex(self.time_window_index)
        time_layout.addRow("Window:", self.time_combo)
        
        left_column.addWidget(time_group)
        
        # Line options
        line_group = QGroupBox("Line Options")
        line_layout = QFormLayout(line_group)
        line_layout.setSpacing(8)
        
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 10.0)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setDecimals(1)
        self.line_width_spin.setValue(self.line_width)
        line_layout.addRow("Line Width:", self.line_width_spin)
        
        left_column.addWidget(line_group)
        
        # Grid options
        grid_group = QGroupBox("Grid Options")
        grid_layout = QFormLayout(grid_group)
        grid_layout.setSpacing(8)
        
        self.grid_alpha_spin = QDoubleSpinBox()
        self.grid_alpha_spin.setRange(0.0, 1.0)
        self.grid_alpha_spin.setSingleStep(0.1)
        self.grid_alpha_spin.setDecimals(1)
        self.grid_alpha_spin.setValue(self.grid_alpha)
        grid_layout.addRow("Grid Opacity:", self.grid_alpha_spin)
        
        left_column.addWidget(grid_group)

        # Y Axis options
        y_axis_group = QGroupBox("Y Axis Options")
        y_axis_layout = QFormLayout(y_axis_group)
        y_axis_layout.setSpacing(8)

        self.y_auto_scale_check = QCheckBox("Auto Scale")
        self.y_auto_scale_check.setChecked(self.y_auto_scale)
        self.y_auto_scale_check.toggled.connect(self._on_auto_scale_toggled)
        y_axis_layout.addRow(self.y_auto_scale_check)

        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1e9, 1e9)
        self.y_min_spin.setValue(self.y_min)
        y_axis_layout.addRow("Min Y:", self.y_min_spin)

        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1e9, 1e9)
        self.y_max_spin.setValue(self.y_max)
        y_axis_layout.addRow("Max Y:", self.y_max_spin)

        # Initial state for Y spin boxes
        self._on_auto_scale_toggled(self.y_auto_scale)

        left_column.addWidget(y_axis_group)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.show_legend_check = QCheckBox("Show Legend")
        self.show_legend_check.setChecked(self.show_legend)
        display_layout.addWidget(self.show_legend_check)
        
        left_column.addWidget(display_group)
        
        left_column.addStretch()
        
        # Right column - Plot Selection
        right_column = QVBoxLayout()
        right_column.setSpacing(12)
        
        selection_group = QGroupBox("Plot Selection")
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setSpacing(12)
        
        # Registers section
        reg_section = QVBoxLayout()
        reg_section.setSpacing(4)
        
        reg_title = QLabel("Registers:")
        reg_title.setStyleSheet("font-size: 11px; font-weight: 500;")
        reg_section.addWidget(reg_title)
        
        self.reg_scroll = QScrollArea()
        self.reg_scroll.setWidgetResizable(True)
        self.reg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.reg_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reg_scroll.setStyleSheet(f"border: 1px solid {COLORS['border']}; border-radius: 4px; background: {COLORS['bg_widget']};")
        self.reg_scroll.setMinimumHeight(200)
        
        self.reg_container = QWidget()
        self.reg_container.setStyleSheet("background: transparent;")
        self.reg_layout = QVBoxLayout(self.reg_container)
        self.reg_layout.setContentsMargins(8, 8, 8, 8)
        self.reg_layout.setSpacing(4)
        
        self.reg_scroll.setWidget(self.reg_container)
        reg_section.addWidget(self.reg_scroll, stretch=1)
        
        # Register buttons
        reg_btn_layout = QHBoxLayout()
        reg_btn_layout.setSpacing(4)
        select_all_reg_btn = QPushButton("All")
        select_all_reg_btn.setFixedWidth(50)
        select_all_reg_btn.clicked.connect(self._select_all_registers)
        reg_btn_layout.addWidget(select_all_reg_btn)
        
        select_none_reg_btn = QPushButton("None")
        select_none_reg_btn.setFixedWidth(50)
        select_none_reg_btn.clicked.connect(self._select_none_registers)
        reg_btn_layout.addWidget(select_none_reg_btn)
        reg_btn_layout.addStretch()
        reg_section.addLayout(reg_btn_layout)
        
        selection_layout.addLayout(reg_section, stretch=1)
        
        # Variables section
        var_section = QVBoxLayout()
        var_section.setSpacing(4)
        
        var_title = QLabel("Variables:")
        var_title.setStyleSheet("font-size: 11px; font-weight: 500;")
        var_section.addWidget(var_title)
        
        var_scroll = QScrollArea()
        var_scroll.setWidgetResizable(True)
        var_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        var_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        var_scroll.setStyleSheet(f"border: 1px solid {COLORS['border']}; border-radius: 4px; background: {COLORS['bg_widget']};")
        var_scroll.setMinimumHeight(200)
        
        self.variable_container = QWidget()
        self.variable_container.setStyleSheet("background: transparent;")
        self.variable_layout = QVBoxLayout(self.variable_container)
        self.variable_layout.setContentsMargins(8, 8, 8, 8)
        self.variable_layout.setSpacing(4)
        
        var_scroll.setWidget(self.variable_container)
        var_section.addWidget(var_scroll, stretch=1)
        
        # Variable buttons
        var_btn_layout = QHBoxLayout()
        var_btn_layout.setSpacing(4)
        select_all_var_btn = QPushButton("All")
        select_all_var_btn.setFixedWidth(50)
        select_all_var_btn.clicked.connect(self._select_all_variables)
        var_btn_layout.addWidget(select_all_var_btn)
        
        select_none_var_btn = QPushButton("None")
        select_none_var_btn.setFixedWidth(50)
        select_none_var_btn.clicked.connect(self._select_none_variables)
        var_btn_layout.addWidget(select_none_var_btn)
        var_btn_layout.addStretch()
        var_section.addLayout(var_btn_layout)
        
        selection_layout.addLayout(var_section, stretch=1)
        
        right_column.addWidget(selection_group)
        right_column.addStretch()
        
        # Add columns to main layout
        columns_layout.addLayout(left_column, stretch=1)
        columns_layout.addLayout(right_column, stretch=1)
        
        main_layout.addLayout(columns_layout, stretch=1)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Populate register and variable checkboxes
        self._populate_checkboxes()
    
    def _populate_checkboxes(self) -> None:
        """Populate register and variable checkboxes."""
        # Clear existing register checkboxes
        for i in reversed(range(self.reg_layout.count())):
            self.reg_layout.itemAt(i).widget().setParent(None)
        self._register_checkbox_map.clear()
        
        # Clear existing variable checkboxes
        for i in reversed(range(self.variable_layout.count())):
            self.variable_layout.itemAt(i).widget().setParent(None)
        self._variable_checkbox_map.clear()
        
        # Group registers by (address, label) to show them uniquely
        unique_regs = {}
        for reg in self.registers:
            key = (reg.address, reg.label)
            if key not in unique_regs:
                unique_regs[key] = []
            unique_regs[key].append(reg)
            
        for key in sorted(unique_regs.keys()):
            address, label = key
            display_label = label if label else f"R{address}"
            
            checkbox = QCheckBox(display_label)
            checkbox.setStyleSheet("font-size: 11px;")
            
            # Check if any instance of this register is currently selected
            is_selected = any(r.designator in self.selected_registers for r in unique_regs[key])
            checkbox.setChecked(is_selected)
            
            self.reg_layout.addWidget(checkbox)
            self._register_checkbox_map[key] = checkbox
            
        # Group variables by name
        unique_vars = {}
        for var in self.variables:
            if var.name not in unique_vars:
                unique_vars[var.name] = []
            unique_vars[var.name].append(var)
            
        for name in sorted(unique_vars.keys()):
            # Use label if available for display
            var_instance = unique_vars[name][0]
            display_label = var_instance.label if var_instance.label else name
            
            checkbox = QCheckBox(display_label)
            checkbox.setStyleSheet("font-size: 11px;")
            
            is_selected = any(v.designator in self.selected_variables for v in unique_vars[name])
            checkbox.setChecked(is_selected)
            
            self.variable_layout.addWidget(checkbox)
            self._variable_checkbox_map[name] = checkbox
        
    
    def _select_all_registers(self) -> None:
        """Select all register checkboxes."""
        for checkbox in self._register_checkbox_map.values():
            checkbox.setChecked(True)
    
    def _select_none_registers(self) -> None:
        """Deselect all register checkboxes."""
        for checkbox in self._register_checkbox_map.values():
            checkbox.setChecked(False)
    
    def _select_all_variables(self) -> None:
        """Select all variable checkboxes."""
        for checkbox in self._variable_checkbox_map.values():
            checkbox.setChecked(True)
    
    def _select_none_variables(self) -> None:
        """Deselect all variable checkboxes."""
        for checkbox in self._variable_checkbox_map.values():
            checkbox.setChecked(False)
    
    def _on_auto_scale_toggled(self, checked: bool) -> None:
        """Enable/disable Y min/max inputs based on auto scale."""
        self.y_min_spin.setEnabled(not checked)
        self.y_max_spin.setEnabled(not checked)
    
    def get_options(self) -> dict:
        """Get the selected options."""
        selected_registers = []
        for key, checkbox in self._register_checkbox_map.items():
            if checkbox.isChecked():
                address, label = key
                # Include all designators that match this address and label
                for reg in self.registers:
                    if reg.address == address and reg.label == label:
                        selected_registers.append(reg.designator)
                        
        selected_variables = []
        for name, checkbox in self._variable_checkbox_map.items():
            if checkbox.isChecked():
                # Include all designators that match this name
                for var in self.variables:
                    if var.name == name:
                        selected_variables.append(var.designator)
        
        return {
            'line_width': self.line_width_spin.value(),
            'grid_alpha': self.grid_alpha_spin.value(),
            'show_legend': self.show_legend_check.isChecked(),
            'time_window_index': self.time_combo.currentIndex(),
            'y_auto_scale': self.y_auto_scale_check.isChecked(),
            'y_min': self.y_min_spin.value(),
            'y_max': self.y_max_spin.value(),
            'selected_registers': list(set(selected_registers)),
            'selected_variables': list(set(selected_variables)),
        }
