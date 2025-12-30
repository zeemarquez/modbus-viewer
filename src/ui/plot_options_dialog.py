"""
Plot options dialog for customizing plot appearance.
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QLabel, QGroupBox, QDialogButtonBox, QCheckBox,
    QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt

from src.models.register import Register
from src.models.variable import Variable


class PlotOptionsDialog(QDialog):
    """Dialog for customizing plot options."""
    
    def __init__(self, line_width: float = 2.0, grid_alpha: float = 0.1, 
                 show_legend: bool = True, time_window_index: int = 2,
                 registers: List[Register] = None, variables: List[Variable] = None,
                 selected_registers: List[int] = None, selected_variables: List[str] = None,
                 parent=None):
        super().__init__(parent)
        
        self.line_width = line_width
        self.grid_alpha = grid_alpha
        self.show_legend = show_legend
        self.time_window_index = time_window_index
        self.registers = registers or []
        self.variables = variables or []
        self.selected_registers = selected_registers or []
        self.selected_variables = selected_variables or []
        
        self._register_checkboxes: Dict[int, QCheckBox] = {}
        self._variable_checkboxes: Dict[str, QCheckBox] = {}
        
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
        
        reg_scroll = QScrollArea()
        reg_scroll.setWidgetResizable(True)
        reg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        reg_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        reg_scroll.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px; background: #ffffff;")
        reg_scroll.setMinimumHeight(200)
        
        self.register_container = QWidget()
        self.register_container.setStyleSheet("background: transparent;")
        self.register_layout = QVBoxLayout(self.register_container)
        self.register_layout.setContentsMargins(8, 8, 8, 8)
        self.register_layout.setSpacing(4)
        
        reg_scroll.setWidget(self.register_container)
        reg_section.addWidget(reg_scroll, stretch=1)
        
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
        var_scroll.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px; background: #ffffff;")
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
        # Clear existing
        for checkbox in self._register_checkboxes.values():
            checkbox.deleteLater()
        self._register_checkboxes.clear()
        
        for checkbox in self._variable_checkboxes.values():
            checkbox.deleteLater()
        self._variable_checkboxes.clear()
        
        # Create register checkboxes
        for reg in self.registers:
            checkbox = QCheckBox(reg.label or f"R{reg.address}")
            checkbox.setStyleSheet("font-size: 11px;")
            checkbox.setChecked(reg.address in self.selected_registers)
            self.register_layout.addWidget(checkbox)
            self._register_checkboxes[reg.address] = checkbox
        
        # Create variable checkboxes
        for var in self.variables:
            checkbox = QCheckBox(var.label or var.name)
            checkbox.setStyleSheet("font-size: 11px;")
            checkbox.setChecked(var.name in self.selected_variables)
            self.variable_layout.addWidget(checkbox)
            self._variable_checkboxes[var.name] = checkbox
    
    def _select_all_registers(self) -> None:
        """Select all register checkboxes."""
        for checkbox in self._register_checkboxes.values():
            checkbox.setChecked(True)
    
    def _select_none_registers(self) -> None:
        """Deselect all register checkboxes."""
        for checkbox in self._register_checkboxes.values():
            checkbox.setChecked(False)
    
    def _select_all_variables(self) -> None:
        """Select all variable checkboxes."""
        for checkbox in self._variable_checkboxes.values():
            checkbox.setChecked(True)
    
    def _select_none_variables(self) -> None:
        """Deselect all variable checkboxes."""
        for checkbox in self._variable_checkboxes.values():
            checkbox.setChecked(False)
    
    def get_options(self) -> dict:
        """Get the selected options."""
        selected_registers = [
            address for address, checkbox in self._register_checkboxes.items()
            if checkbox.isChecked()
        ]
        selected_variables = [
            name for name, checkbox in self._variable_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        return {
            'line_width': self.line_width_spin.value(),
            'grid_alpha': self.grid_alpha_spin.value(),
            'show_legend': self.show_legend_check.isChecked(),
            'time_window_index': self.time_combo.currentIndex(),
            'selected_registers': selected_registers,
            'selected_variables': selected_variables,
        }

