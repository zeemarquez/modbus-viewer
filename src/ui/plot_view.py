"""
Real-time plot view for register values using pyqtgraph.
"""

from typing import List, Dict, Optional
import numpy as np

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel
)
from PySide6.QtCore import Qt

import pyqtgraph as pg

from src.models.register import Register
from src.models.variable import Variable
from src.models.project import PlotOptions
from src.core.data_engine import DataEngine
from src.ui.plot_options_dialog import PlotOptionsDialog


# Configure pyqtgraph for light theme
pg.setConfigOptions(
    background='#ffffff',
    foreground='#212121',
    antialias=True
)

# Color palette for plot lines
PLOT_COLORS = [
    '#1976d2',  # Blue
    '#c62828',  # Red
    '#2e7d32',  # Green
    '#7b1fa2',  # Purple
    '#ef6c00',  # Orange
    '#00838f',  # Cyan
    '#c2185b',  # Pink
    '#558b2f',  # Light green
]


class PlotView(QFrame):
    """Widget for real-time plotting of register and variable values."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.registers: List[Register] = []
        self.variables: List[Variable] = []
        self._plot_items: Dict[str, pg.PlotDataItem] = {}  # Key: "R0" or "var_name"
        self._time_window = 60.0  # seconds
        self._is_paused = False
        
        # Plot options
        self._line_width = 2.0
        self._grid_alpha = 0.1
        self._show_legend = True
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(4, 4, 4, 4)
        
        # Time window selector (left side)
        toolbar.addWidget(QLabel("Time:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems(["1s", "5s", "10s", "30s", "1min", "2min", "5min"])
        self.time_combo.setCurrentIndex(4)  # 1min default
        self.time_combo.setFixedWidth(70)
        self.time_combo.currentIndexChanged.connect(self._on_time_window_changed)
        toolbar.addWidget(self.time_combo)
        
        toolbar.addStretch()
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFixedWidth(60)
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_pause_toggled)
        toolbar.addWidget(self.pause_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(50)
        self.clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_btn)
        
        self.options_btn = QPushButton("Options")
        self.options_btn.setFixedWidth(60)
        self.options_btn.clicked.connect(self._show_options)
        toolbar.addWidget(self.options_btn)
        
        layout.addLayout(toolbar)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.showGrid(x=True, y=True, alpha=self._grid_alpha)
        
        # Disable mouse interaction (no panning/zooming with mouse)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        
        # Enable auto-range for Y axis only (X is controlled by time window)
        self.plot_widget.enableAutoRange(axis='y')
        
        # Style axes
        axis_pen = pg.mkPen(color='#757575', width=1)
        text_color = '#757575'
        for axis in ['left', 'bottom']:
            self.plot_widget.getAxis(axis).setPen(axis_pen)
            self.plot_widget.getAxis(axis).setTextPen(text_color)
        
        # Add legend
        self.legend = self.plot_widget.addLegend(offset=(-10, 10))
        
        layout.addWidget(self.plot_widget, stretch=1)
    
    def _show_options(self) -> None:
        """Show plot options dialog."""
        dialog = PlotOptionsDialog(
            line_width=self._line_width,
            grid_alpha=self._grid_alpha,
            show_legend=self._show_legend,
            time_window_index=self.time_combo.currentIndex(),
            registers=self.registers,
            variables=self.variables,
            selected_registers=self.get_selected_registers(),
            selected_variables=self.get_selected_variables(),
            parent=self
        )
        
        if dialog.exec():
            options = dialog.get_options()
            self._line_width = options['line_width']
            self._grid_alpha = options['grid_alpha']
            self._show_legend = options['show_legend']
            
            # Update time window
            time_window_index = options['time_window_index']
            if 0 <= time_window_index < self.time_combo.count():
                self.time_combo.setCurrentIndex(time_window_index)
                self._on_time_window_changed(time_window_index)
            
            # Update selected registers and variables
            self.set_selected_registers(options['selected_registers'])
            self.set_selected_variables(options['selected_variables'])
            
            # Apply options
            self.plot_widget.showGrid(x=True, y=True, alpha=self._grid_alpha)
            
            if self._show_legend:
                if not self.legend:
                    self.legend = self.plot_widget.addLegend(offset=(-10, 10))
            else:
                if self.legend:
                    self.plot_widget.removeItem(self.legend)
                    self.legend = None
            
            # Update existing plot items with new line width
            for plot_item in self._plot_items.values():
                pen = plot_item.opts['pen']
                new_pen = pg.mkPen(
                    color=pen.color(),
                    width=self._line_width,
                    style=pen.style()
                )
                plot_item.setPen(new_pen)
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the list of registers available for plotting."""
        self.registers = registers
        # Remove plot items for registers that no longer exist
        current_addresses = {reg.address for reg in registers}
        keys_to_remove = [
            k for k in self._plot_items.keys() 
            if k.startswith('R') and int(k[1:]) not in current_addresses
        ]
        for key in keys_to_remove:
            self.plot_widget.removeItem(self._plot_items[key])
            del self._plot_items[key]
    
    def set_variables(self, variables: List[Variable]) -> None:
        """Set the list of variables available for plotting."""
        self.variables = variables
        # Remove plot items for variables that no longer exist
        current_names = {var.name for var in variables}
        keys_to_remove = [
            k for k in self._plot_items.keys() 
            if not k.startswith('R') and k not in current_names
        ]
        for key in keys_to_remove:
            self.plot_widget.removeItem(self._plot_items[key])
            del self._plot_items[key]
    
    
    def _on_time_window_changed(self, index: int) -> None:
        """Handle time window change."""
        windows = [1, 5, 10, 30, 60, 120, 300]
        if index < len(windows):
            self._time_window = windows[index]
    
    def _on_pause_toggled(self, checked: bool) -> None:
        """Handle pause button toggle."""
        self._is_paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")
    
    def update_plot(self, data_engine: DataEngine) -> None:
        """Update plot with data from engine."""
        if self._is_paused:
            return
        
        has_data = False
        for key, plot_item in self._plot_items.items():
            times, values = data_engine.get_history_arrays(key, self._time_window)
            
            if times and values:
                plot_item.setData(times, values)
                has_data = True
        
        # Update x-axis range
        self.plot_widget.setXRange(-self._time_window, 0, padding=0.02)
        
        # Auto-scale Y axis to fit data
        if has_data:
            self.plot_widget.enableAutoRange(axis='y')
    
    def clear(self) -> None:
        """Clear all plot data."""
        for plot_item in self._plot_items.values():
            plot_item.setData([], [])
    
    def get_selected_registers(self) -> List[int]:
        """Get list of selected register addresses."""
        selected = []
        for key in self._plot_items.keys():
            if key.startswith('R'):
                address = int(key[1:])
                selected.append(address)
        return selected
    
    def get_selected_variables(self) -> List[str]:
        """Get list of selected variable names."""
        selected = []
        for key in self._plot_items.keys():
            if not key.startswith('R'):
                selected.append(key)
        return selected
    
    def set_selected_registers(self, addresses: List[int]) -> None:
        """Set which registers are selected for plotting."""
        # Remove plots for unselected registers
        for key in list(self._plot_items.keys()):
            if key.startswith('R'):
                address = int(key[1:])
                if address not in addresses:
                    self.plot_widget.removeItem(self._plot_items[key])
                    del self._plot_items[key]
        
        # Add plots for newly selected registers
        for address in addresses:
            key = f"R{address}"
            if key not in self._plot_items:
                # Find register to get label and color index
                reg = None
                for r in self.registers:
                    if r.address == address:
                        reg = r
                        break
                
                if reg:
                    color_index = self.registers.index(reg) % len(PLOT_COLORS)
                    color = PLOT_COLORS[color_index]
                    pen = pg.mkPen(color=color, width=self._line_width)
                    label = reg.label or f"R{address}"
                    
                    plot_item = self.plot_widget.plot([], [], pen=pen, name=label)
                    self._plot_items[key] = plot_item
    
    def set_selected_variables(self, names: List[str]) -> None:
        """Set which variables are selected for plotting."""
        # Remove plots for unselected variables
        for key in list(self._plot_items.keys()):
            if not key.startswith('R') and key not in names:
                self.plot_widget.removeItem(self._plot_items[key])
                del self._plot_items[key]
        
        # Add plots for newly selected variables
        for name in names:
            if name not in self._plot_items:
                # Find variable to get label and color index
                var = None
                for v in self.variables:
                    if v.name == name:
                        var = v
                        break
                
                if var:
                    color_index = (self.variables.index(var) + len(self.registers)) % len(PLOT_COLORS)
                    color = PLOT_COLORS[color_index]
                    pen = pg.mkPen(color=color, width=self._line_width)
                    label = var.label or var.name
                    
                    plot_item = self.plot_widget.plot([], [], pen=pen, name=label)
                    self._plot_items[name] = plot_item
    
    def get_plot_options(self) -> PlotOptions:
        """Get current plot options."""
        return PlotOptions(
            line_width=self._line_width,
            grid_alpha=self._grid_alpha,
            show_legend=self._show_legend,
            time_window_index=self.time_combo.currentIndex(),
        )
    
    def set_plot_options(self, options: PlotOptions) -> None:
        """Set plot options."""
        self._line_width = options.line_width
        self._grid_alpha = options.grid_alpha
        self._show_legend = options.show_legend
        
        # Apply grid alpha
        self.plot_widget.showGrid(x=True, y=True, alpha=self._grid_alpha)
        
        # Apply legend visibility
        if self._show_legend:
            if not self.legend:
                self.legend = self.plot_widget.addLegend(offset=(-10, 10))
        else:
            if self.legend:
                self.plot_widget.removeItem(self.legend)
                self.legend = None
        
        # Apply line width to existing plot items
        for plot_item in self._plot_items.values():
            pen = plot_item.opts['pen']
            new_pen = pg.mkPen(
                color=pen.color(),
                width=self._line_width,
                style=pen.style()
            )
            plot_item.setPen(new_pen)
        
        # Set time window
        if 0 <= options.time_window_index < self.time_combo.count():
            self.time_combo.setCurrentIndex(options.time_window_index)
    
    def get_time_window_index(self) -> int:
        """Get current time window combo index."""
        return self.time_combo.currentIndex()
    
    def set_time_window_index(self, index: int) -> None:
        """Set time window by combo index."""
        if 0 <= index < self.time_combo.count():
            self.time_combo.setCurrentIndex(index)
