import os
from PySide6.QtWidgets import (
    QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMenu, QCheckBox, QWidget, QAbstractItemView, QLabel,
    QDialog, QProgressBar, QPushButton, QLineEdit, QHBoxLayout,
    QSizePolicy, QFileDialog, QFontDialog, QColorDialog,
    QFontComboBox, QSpinBox, QComboBox, QToolButton,
    QSlider
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QBrush, QPixmap, QAction
import pyqtgraph as pg
from src.ui.table_view import TableView
from src.ui.plot_view import PlotView
from src.ui.variables_panel import VariablesPanel
from src.ui.bits_panel import BitsPanel
from src.ui.scan_dialog import ScanWorker
from src.models.register import AccessMode
from src.ui.styles import COLORS

class ViewerTableView(TableView):
    """Modified TableView for the viewer with visibility controls."""
    
    visibility_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_admin = False
        self.config = None
    
    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin
        self.config = config
        self.update_style()
        self._rebuild_tabs()
        self._update_column_visibility()

    def update_style(self):
        self.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_widget']};")
        # Trigger re-populate to update text colors if needed
        if hasattr(self, 'project') and self.project:
            self.set_registers(self.project.registers)

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the table UI without the toolbar."""
        # Initial style setup - will be updated by set_admin_mode/update_theme
        self.update_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Tab widget for devices
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Placeholder for write_btn
        from PySide6.QtWidgets import QPushButton
        self.write_btn = QPushButton()
        self.write_btn.setVisible(False)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        cols = ["Visible", "Label", "Address", "Size", "Value", "New Value", "Status"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        
        # Configure table
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        # Header context menu for column visibility
        header = table.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_menu)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        return table

    def _show_header_menu(self, pos):
        if not self.is_admin: return
        
        table = self.sender().parentWidget()
        menu = QMenu(self)
        
        for i in range(table.columnCount()):
            col_name = table.horizontalHeaderItem(i).text()
            if col_name == "Visible": continue
            
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not table.isColumnHidden(i))
            action.toggled.connect(lambda checked, idx=i, name=col_name: self._toggle_column(idx, name, checked))
            
        menu.exec(self.sender().mapToGlobal(pos))

    def _toggle_column(self, index, name, checked):
        if not self.config: return
        
        if checked:
            if name in self.config.hidden_columns:
                self.config.hidden_columns.remove(name)
        else:
            if name not in self.config.hidden_columns:
                self.config.hidden_columns.append(name)
        
        self.config.save()
        self._update_column_visibility()

    def _update_column_visibility(self):
        for slave_id, table in self._device_tables.items():
            # Always hide "Visible" column if not admin
            table.setColumnHidden(0, not self.is_admin)
            
            if self.config:
                for i in range(1, table.columnCount()):
                    col_name = table.horizontalHeaderItem(i).text()
                    is_hidden = col_name in self.config.hidden_columns
                    table.setColumnHidden(i, is_hidden)

    def _populate_table(self, table: QTableWidget, registers: list) -> None:
        # Filter registers for normal users
        filtered_regs = registers
        if not self.is_admin and self.config:
            filtered_regs = [r for r in registers if f"R{r.address}" not in self.config.hidden_registers]
        
        offset = 1 if self.is_admin else 0
        table.setRowCount(len(filtered_regs) + offset)
        
        if self.is_admin:
            # Toggle All Row
            vis_check = QCheckBox()
            all_visible = all(f"R{r.address}" not in self.config.hidden_registers for r in (self.project.registers if self.project else []))
            vis_check.setChecked(all_visible)
            vis_check.toggled.connect(self._on_toggle_all_visibility)
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(0, 0, container)
            
            label_item = QTableWidgetItem("Toggle All")
            label_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(0, 1, label_item)

        for i, reg in enumerate(filtered_regs):
            row = i + offset
            # Visibility Item (Checkbox)
            vis_check = QCheckBox()
            vis_id = f"R{reg.address}"
            vis_check.setChecked(vis_id not in self.config.hidden_registers if self.config else True)
            vis_check.toggled.connect(lambda checked, r=reg: self._on_row_visibility_changed(r, checked))
            
            # Center the checkbox
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(row, 0, container)
            
            # Label
            label_item = QTableWidgetItem(reg.label)
            label_item.setData(Qt.ItemDataRole.UserRole, reg)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, label_item)
            
            # Address
            addr_item = QTableWidgetItem(f"R{reg.address}")
            addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, addr_item)
            
            # Size
            size_item = QTableWidgetItem(str(reg.size))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, size_item)
            
            # Value
            value_item = QTableWidgetItem("---")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row, 4, value_item)
            
            # New Value
            new_val_item = QTableWidgetItem("")
            new_val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row, 5, new_val_item)
            
            # Status
            status_item = QTableWidgetItem("")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 6, status_item)

    def _on_toggle_all_visibility(self, checked):
        if not self.config or not self.project: return
        if checked:
            self.config.hidden_registers.clear()
        else:
            for r in self.project.registers:
                rid = f"R{r.address}"
                if rid not in self.config.hidden_registers:
                    self.config.hidden_registers.append(rid)
        self.config.save()
        self.visibility_changed.emit()

    def _on_row_visibility_changed(self, reg, checked):
        if not self.config: return
        
        vis_id = f"R{reg.address}"
        if checked:
            if vis_id in self.config.hidden_registers:
                self.config.hidden_registers.remove(vis_id)
        else:
            if vis_id not in self.config.hidden_registers:
                self.config.hidden_registers.append(vis_id)
        
        self.config.save()
        self.visibility_changed.emit()

    def _get_register_from_table(self, table: QTableWidget, row: int):
        item = table.item(row, 1) # Label is at 1
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def update_values(self) -> None:
        """Update displayed values from registers."""
        for slave_id, table in self._device_tables.items():
            table.blockSignals(True)
            try:
                for row in range(table.rowCount()):
                    # Skip toggle row if in admin mode
                    reg = self._get_register_from_table(table, row)
                    if not reg: continue
                    
                    # Value is at column 4
                    value_item = table.item(row, 4)
                    if value_item and reg.scaled_value is not None:
                        value_item.setText(reg.format_value(reg.scaled_value))
                    
                    # Status is at column 6
                    status_item = table.item(row, 6)
                    if status_item:
                        status_item.setText("⚠" if reg.error else "✓")
            finally:
                table.blockSignals(False)

class ViewerPlotView(PlotView):
    """Modified PlotView for the viewer."""
    
    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin
        self.config = config
        self.update_style()
        
        if self.config:
            # Load visual settings
            self._line_width = self.config.plot_line_width
            self._grid_alpha = self.config.plot_grid_alpha
            self._show_legend = self.config.plot_show_legend
            self._y_auto_scale = self.config.plot_y_auto_scale
            self._y_min = self.config.plot_y_min
            self._y_max = self.config.plot_y_max
            
            # Apply to UI
            self.plot_widget.showGrid(x=True, y=True, alpha=self._grid_alpha)
            if self._y_auto_scale:
                self.plot_widget.enableAutoRange(axis='y')
            else:
                self.plot_widget.disableAutoRange(axis='y')
                self.plot_widget.setYRange(self._y_min, self._y_max, padding=0)
            
            self.set_time_window_index(self.config.plot_time_window_index)
            
            # Force legend sync
            if self._show_legend:
                if not getattr(self, 'legend', None):
                    self.legend = self.plot_widget.addLegend(offset=(-10, 10))
            else:
                if getattr(self, 'legend', None):
                    self.plot_widget.removeItem(self.legend)
                    self.legend = None

    def update_style(self):
        self.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_widget']};")
        if hasattr(self.plot_widget, 'setBackground'):
             self.plot_widget.setBackground(COLORS['bg_widget'])

        # Update pyqtgraph configuration for future items
        pg.setConfigOptions(foreground=COLORS['text_primary'], background=COLORS['bg_widget'])

        # Update Axes
        text_color = COLORS['text_primary']
        axis_pen = pg.mkPen(color=COLORS['text_secondary'], width=1)
        for axis_name in ['left', 'bottom']:
            ax = self.plot_widget.getAxis(axis_name)
            ax.setPen(axis_pen)
            ax.setTextPen(text_color)

        # Update Legend
        if getattr(self, 'legend', None):
            for sample, label in self.legend.items:
                 # Force text update with color
                 label.setText(label.text, color=text_color)
                 label.setAttr('color', text_color)

    def _show_options(self) -> None:
        """Override to filter visible registers and variables in the dialog."""
        if not self.config:
            return super()._show_options()
            
        # Filter registers: exclude if R<addr> is in hidden_registers
        # (Viewer logic uses designator fragment "R<addr>" for register visibility)
        visible_regs = [r for r in self.registers if f"R{r.address}" not in self.config.hidden_registers]
        
        # Filter variables: exclude if name is in hidden_variables
        visible_vars = [v for v in self.variables if v.name not in self.config.hidden_variables]
        
        # Use filtered lists for the dialog
        from src.ui.plot_options_dialog import PlotOptionsDialog
        dialog = PlotOptionsDialog(
            line_width=self._line_width,
            grid_alpha=self._grid_alpha,
            show_legend=self._show_legend,
            time_window_index=self.time_combo.currentIndex(),
            y_auto_scale=self._y_auto_scale,
            y_min=self._y_min,
            y_max=self._y_max,
            registers=visible_regs,
            variables=visible_vars,
            selected_registers=self.get_selected_registers(),
            selected_variables=self.get_selected_variables(),
            parent=self
        )
        
        if dialog.exec():
            options = dialog.get_options()
            self._line_width = options['line_width']
            self._grid_alpha = options['grid_alpha']
            self._show_legend = options['show_legend']
            self._y_auto_scale = options['y_auto_scale']
            self._y_min = options['y_min']
            self._y_max = options['y_max']
            
            # Update time window
            time_window_index = options['time_window_index']
            if 0 <= time_window_index < self.time_combo.count():
                self.time_combo.setCurrentIndex(time_window_index)
                self._on_time_window_changed(time_window_index)
            
            # Update selected registers and variables
            self.set_selected_registers(options['selected_registers'])
            self.set_selected_variables(options['selected_variables'])
            
            # Save to config
            self.config.plot_line_width = self._line_width
            self.config.plot_grid_alpha = self._grid_alpha
            self.config.plot_show_legend = self._show_legend
            self.config.plot_y_auto_scale = self._y_auto_scale
            self.config.plot_y_min = self._y_min
            self.config.plot_y_max = self._y_max
            self.config.plot_time_window_index = self.time_combo.currentIndex()
            self.config.plot_registers = options['selected_registers']
            self.config.plot_variables = options['selected_variables']
            self.config.save()
            
            # Apply options
            self.plot_widget.showGrid(x=True, y=True, alpha=self._grid_alpha)
            
            # Apply Y axis scaling
            if self._y_auto_scale:
                self.plot_widget.enableAutoRange(axis='y')
            else:
                self.plot_widget.disableAutoRange(axis='y')
                self.plot_widget.setYRange(self._y_min, self._y_max, padding=0)
            
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

    def set_registers(self, registers: list) -> None:
        """Override to restore selection from config."""
        super().set_registers(registers)
        if hasattr(self, 'config') and self.config:
            # Restore selection for visible registers
            self.set_selected_registers(self.config.plot_registers)

    def set_variables(self, variables: list) -> None:
        """Override to restore selection from config."""
        super().set_variables(variables)
        if hasattr(self, 'config') and self.config:
            # Restore selection for visible variables
            self.set_selected_variables(self.config.plot_variables)

class ViewerVariablesPanel(VariablesPanel):
    """Modified VariablesPanel for the viewer with visibility controls."""
    
    visibility_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_admin = False
        self.config = None
        
    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin
        self.config = config
        self.update_style()
        self._rebuild_tabs()
        self._update_column_visibility()

    def update_style(self):
        self.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_widget']};")
        # Re-populate to update text colors
        if hasattr(self, 'project') and self.project:
            # force refresh of live registers/vars? 
            # Usually handled by `set_registers` call from main window
            pass

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the panel UI without the toolbar."""
        self.update_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        cols = ["Visible", "Label", "Value", "Expression"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        header = table.horizontalHeader()
        header.customContextMenuRequested.connect(self._show_header_menu)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        return table

    def _show_header_menu(self, pos):
        if not self.is_admin: return
        
        table = self.sender().parentWidget()
        menu = QMenu(self)
        
        for i in range(table.columnCount()):
            col_name = table.horizontalHeaderItem(i).text()
            if col_name == "Visible": continue
            
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not table.isColumnHidden(i))
            action.toggled.connect(lambda checked, idx=i, name=col_name: self._toggle_column(idx, name, checked))
            
        menu.exec(self.sender().mapToGlobal(pos))

    def _toggle_column(self, index, name, checked):
        if not self.config: return
        
        if checked:
            if name in self.config.hidden_variables_columns:
                self.config.hidden_variables_columns.remove(name)
        else:
            if name not in self.config.hidden_variables_columns:
                self.config.hidden_variables_columns.append(name)
        
        self.config.save()
        self._update_column_visibility()

    def _update_column_visibility(self):
        for sid, table in self._device_tables.items():
            table.setColumnHidden(0, not self.is_admin)
            if self.config:
                for i in range(1, table.columnCount()):
                    col_name = table.horizontalHeaderItem(i).text()
                    is_hidden = col_name in self.config.hidden_variables_columns
                    table.setColumnHidden(i, is_hidden)

    def _populate_table(self, table: QTableWidget, variables: list) -> None:
        filtered_vars = variables
        if not self.is_admin and self.config:
            filtered_vars = [v for v in variables if v.name not in self.config.hidden_variables]
            
        offset = 1 if self.is_admin else 0
        table.setRowCount(len(filtered_vars) + offset)
        
        if self.is_admin:
            vis_check = QCheckBox()
            all_visible = all(v.name not in self.config.hidden_variables for v in (self.project.variables if self.project else []))
            vis_check.setChecked(all_visible)
            vis_check.toggled.connect(self._on_toggle_all_visibility)
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(0, 0, container)
            
            label_item = QTableWidgetItem("Toggle All")
            label_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(0, 1, label_item)

        for i, var in enumerate(filtered_vars):
            row = i + offset
            # Visibility
            vis_check = QCheckBox()
            vis_check.setChecked(var.name not in self.config.hidden_variables if self.config else True)
            vis_check.toggled.connect(lambda checked, v=var: self._on_row_visibility_changed(v, checked))
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(row, 0, container)
            
            # Label
            label_item = QTableWidgetItem(var.label if var.label else var.name)
            label_item.setData(Qt.ItemDataRole.UserRole, var)
            table.setItem(row, 1, label_item)
            
            # Value
            value_item = QTableWidgetItem("---")
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            table.setItem(row, 2, value_item)
            
            # Expression
            expr_item = QTableWidgetItem(var.expression)
            expr_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
            table.setItem(row, 3, expr_item)

    def _on_toggle_all_visibility(self, checked):
        if not self.config or not self.project: return
        if checked:
            self.config.hidden_variables.clear()
        else:
            for v in self.project.variables:
                if v.name not in self.config.hidden_variables:
                    self.config.hidden_variables.append(v.name)
        self.config.save()
        self.visibility_changed.emit()

    def _on_row_visibility_changed(self, var, checked):
        if not self.config: return
        
        if checked:
            if var.name in self.config.hidden_variables:
                self.config.hidden_variables.remove(var.name)
        else:
            if var.name not in self.config.hidden_variables:
                self.config.hidden_variables.append(var.name)
        
        self.config.save()
        self.visibility_changed.emit()

    def update_values(self) -> None:
        for sid, table in self._device_tables.items():
            for row in range(table.rowCount()):
                item = table.item(row, 1) # Label at 1
                if not item: continue
                var = item.data(Qt.ItemDataRole.UserRole)
                if not var: continue
                
                value_item = table.item(row, 2) # Value at 2
                if value_item:
                    try:
                        value = self.evaluator.evaluate(var.expression)
                        var.value = value
                        value_item.setText(var.format_value(value))
                        value_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
                    except Exception as e:
                        value_item.setText("Error")
                        value_item.setForeground(QBrush(QColor(COLORS['error'])))

class ViewerBitsPanel(BitsPanel):
    """Modified BitsPanel for the viewer with visibility controls."""
    
    visibility_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_admin = False
        self.config = None
        
    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin
        self.config = config
        self.update_style()
        self._rebuild_tabs()
        self._update_column_visibility()

    def update_style(self):
        self.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_widget']};")

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the panel UI without the toolbar."""
        self.update_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget, stretch=1)

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        cols = ["Visible", "Label", "Register", "Bit", "Value", "New Value"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        header = table.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_menu)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        return table

    def _show_header_menu(self, pos):
        if not self.is_admin: return
        
        table = self.sender().parentWidget()
        menu = QMenu(self)
        
        for i in range(table.columnCount()):
            col_name = table.horizontalHeaderItem(i).text()
            if col_name == "Visible": continue
            
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not table.isColumnHidden(i))
            action.toggled.connect(lambda checked, idx=i, name=col_name: self._toggle_column(idx, name, checked))
            
        menu.exec(self.sender().mapToGlobal(pos))

    def _toggle_column(self, index, name, checked):
        if not self.config: return
        
        if checked:
            if name in self.config.hidden_bits_columns:
                self.config.hidden_bits_columns.remove(name)
        else:
            if name not in self.config.hidden_bits_columns:
                self.config.hidden_bits_columns.append(name)
        
        self.config.save()
        self._update_column_visibility()

    def _update_column_visibility(self):
        for sid, table in self._device_tables.items():
            table.setColumnHidden(0, not self.is_admin)
            
            if self.config:
                for i in range(1, table.columnCount()):
                    col_name = table.horizontalHeaderItem(i).text()
                    is_hidden = col_name in self.config.hidden_bits_columns
                    table.setColumnHidden(i, is_hidden)

    def _populate_table(self, table: QTableWidget, bits: list, slave_id: int) -> None:
        filtered_bits = bits
        if not self.is_admin and self.config:
            filtered_bits = [b for b in bits if f"R{b.register_address}.B{b.bit_index}" not in self.config.hidden_bits]
            
        offset = 1 if self.is_admin else 0
        table.setRowCount(len(filtered_bits) + offset)
        
        if self.is_admin:
            vis_check = QCheckBox()
            all_visible = all(f"R{b.register_address}.B{b.bit_index}" not in self.config.hidden_bits for b in (self.project.bits if self.project else []))
            vis_check.setChecked(all_visible)
            vis_check.toggled.connect(self._on_toggle_all_visibility)
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(0, 0, container)
            
            label_item = QTableWidgetItem("Toggle All")
            label_item.setForeground(QBrush(QColor(COLORS['text_secondary'])))
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(0, 1, label_item)

        for i, bit in enumerate(filtered_bits):
            row = i + offset
            # Visibility
            vis_check = QCheckBox()
            vis_id = f"R{bit.register_address}.B{bit.bit_index}"
            vis_check.setChecked(vis_id not in self.config.hidden_bits if self.config else True)
            vis_check.toggled.connect(lambda checked, b=bit: self._on_row_visibility_changed(b, checked))
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(vis_check)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            table.setCellWidget(row, 0, container)
            
            # Label
            label_item = QTableWidgetItem(bit.label)
            label_item.setData(Qt.ItemDataRole.UserRole, bit)
            table.setItem(row, 1, label_item)
            
            # Register
            from src.models.register import AccessMode
            reg = self._register_map.get((bit.slave_id, bit.register_address))
            reg_text = f"R{bit.register_address}"
            if reg and reg.label:
                reg_text = reg.label
            reg_item = QTableWidgetItem(reg_text)
            table.setItem(row, 2, reg_item)
            
            # Bit index
            bit_idx_item = QTableWidgetItem(str(bit.bit_index))
            bit_idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, bit_idx_item)
            
            # Value (current)
            value_label = QLabel("---")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            table.setCellWidget(row, 4, value_label)
            
            # New Value
            new_value_label = QLabel("")
            new_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            new_value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            is_writable = reg and reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
            if not is_writable:
                new_value_label.setStyleSheet("background-color: #eeeeee; border: none;")
            
            table.setCellWidget(row, 5, new_value_label)

    def _on_toggle_all_visibility(self, checked):
        if not self.config or not self.project: return
        if checked:
            self.config.hidden_bits.clear()
        else:
            for b in self.project.bits:
                bid = f"R{b.register_address}.B{b.bit_index}"
                if bid not in self.config.hidden_bits:
                    self.config.hidden_bits.append(bid)
        self.config.save()
        self.visibility_changed.emit()

    def _on_row_visibility_changed(self, bit, checked):
        if not self.config: return
        
        vis_id = f"R{bit.register_address}.B{bit.bit_index}"
        if checked:
            if vis_id in self.config.hidden_bits:
                self.config.hidden_bits.remove(vis_id)
        else:
            if vis_id not in self.config.hidden_bits:
                self.config.hidden_bits.append(vis_id)
        
        self.config.save()
        self.visibility_changed.emit()

    def _get_bit_from_table(self, table: QTableWidget, row: int):
        item = table.item(row, 1) # Label is at 1
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def update_values(self) -> None:
        """Update bit values from registers."""
        for bit in self._live_bits:
            reg = self._register_map.get((bit.slave_id, bit.register_address))
            if reg and reg.raw_value is not None:
                bit.value = bit.extract_from_value(int(reg.raw_value))
            else:
                bit.value = None
        
        self._update_display()

    def _update_display(self) -> None:
        """Update the display of values with shifted indices."""
        from src.models.register import AccessMode
        for slave_id, table in self._device_tables.items():
            for row in range(table.rowCount()):
                bit = self._get_bit_from_table(table, row)
                if not bit: continue
                
                reg = self._register_map.get((bit.slave_id, bit.register_address))
                
                # Value (current) is at 4
                value_label = table.cellWidget(row, 4)
                if isinstance(value_label, QLabel):
                    if bit.value is not None:
                        if bit.value:
                            value_label.setText("TRUE")
                            value_label.setStyleSheet("background-color: #1976d2; color: #ffffff; font-weight: bold; border: none;")
                        else:
                            value_label.setText("FALSE")
                            value_label.setStyleSheet("background-color: #000000; color: #ffffff; font-weight: bold; border: none;")
                    else:
                        value_label.setText("---")
                        value_label.setStyleSheet("background-color: transparent; color: #757575; border: none;")
                
                # New Value is at 5
                new_value_label = table.cellWidget(row, 5)
                if isinstance(new_value_label, QLabel):
                    is_writable = reg and reg.access_mode in (AccessMode.READ_WRITE, AccessMode.WRITE)
                    if is_writable:
                        key = (bit.slave_id, bit.name)
                        if key in self._pending_bit_values:
                            pending_value = self._pending_bit_values[key]
                            if pending_value:
                                new_value_label.setText("TRUE")
                                new_value_label.setStyleSheet("background-color: #1976d2; color: #ffffff; font-weight: bold; border: none;")
                            else:
                                new_value_label.setText("FALSE")
                                new_value_label.setStyleSheet("background-color: #000000; color: #ffffff; font-weight: bold; border: none;")
                        else:
                            new_value_label.setText("")
                            new_value_label.setStyleSheet("background-color: transparent; border: none;")
                    else:
                        new_value_label.setText("")
                        new_value_label.setStyleSheet("background-color: #eeeeee; border: none;")

class TextEditDialog(QDialog):
    """Integrated dialog for editing text properties in real-time."""
    def __init__(self, target_label, parent=None):
        super().__init__(parent)
        self.target_label = target_label
        self.setWindowTitle("Edit Text")
        self.setMinimumWidth(450)
        
        # Store original state for cancel
        self.original_text = target_label.text()
        self.original_font = target_label.font()
        self.original_color = target_label.palette().color(target_label.foregroundRole())
        self.original_align = target_label.alignment()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Text Input
        layout.addWidget(QLabel("Text Content:"))
        self.text_input = QLineEdit(self.original_text)
        self.text_input.textChanged.connect(self._update_style)
        layout.addWidget(self.text_input)
        
        # Font Options
        font_box = QHBoxLayout()
        
        v_font = QVBoxLayout()
        v_font.addWidget(QLabel("Font Family:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self.original_font)
        self.font_combo.currentFontChanged.connect(self._update_style)
        v_font.addWidget(self.font_combo)
        font_box.addLayout(v_font, 3)
        
        v_size = QVBoxLayout()
        v_size.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 200)
        # Use a reasonable default if pointSize is invalid (-1)
        curr_size = self.original_font.pointSize()
        self.size_spin.setValue(curr_size if curr_size > 0 else 14)
        self.size_spin.valueChanged.connect(self._update_style)
        v_size.addWidget(self.size_spin)
        font_box.addLayout(v_size, 1)
        
        # Bold/Italic
        v_style = QVBoxLayout()
        v_style.addWidget(QLabel("Style:"))
        self.bold_check = QCheckBox("Bold")
        self.bold_check.setChecked(self.original_font.bold())
        self.bold_check.stateChanged.connect(self._update_style)
        self.italic_check = QCheckBox("Italic")
        self.italic_check.setChecked(self.original_font.italic())
        self.italic_check.stateChanged.connect(self._update_style)
        v_style.addWidget(self.bold_check)
        v_style.addWidget(self.italic_check)
        font_box.addLayout(v_style)
        
        # Alignment Option
        v_align = QVBoxLayout()
        v_align.addWidget(QLabel("Alignment:"))
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Left", "Center", "Right"])
        
        # Map current alignment to index
        if self.original_align & Qt.AlignmentFlag.AlignLeft:
            self.align_combo.setCurrentIndex(0)
        elif self.original_align & Qt.AlignmentFlag.AlignRight:
            self.align_combo.setCurrentIndex(2)
        else: # Default to center
            self.align_combo.setCurrentIndex(1)
            
        self.align_combo.currentIndexChanged.connect(self._update_style)
        v_align.addWidget(self.align_combo)
        font_box.addLayout(v_align)
        
        layout.addLayout(font_box)
        
        # Color Picker (Embedded)
        layout.addWidget(QLabel("Color:"))
        self.color_picker = QColorDialog()
        self.color_picker.setOptions(QColorDialog.ColorDialogOption.DontUseNativeDialog | QColorDialog.ColorDialogOption.NoButtons)
        self.color_picker.setCurrentColor(self.original_color)
        self.color_picker.currentColorChanged.connect(self._update_style)
        layout.addWidget(self.color_picker)
        
        # Actions
        actions = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        actions.addStretch()
        actions.addWidget(ok_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

    def _update_style(self):
        """Apply all style properties via a single stylesheet for maximum reliability."""
        text = self.text_input.text() if self.text_input.text() else "Text"
        font_family = self.font_combo.currentFont().family()
        font_size = self.size_spin.value()
        is_bold = self.bold_check.isChecked()
        is_italic = self.italic_check.isChecked()
        color = self.color_picker.currentColor().name()
        
        style = f"""
            QLabel {{
                font-family: "{font_family}";
                font-size: {font_size}pt;
                font-weight: {"bold" if is_bold else "normal"};
                font-style: {"italic" if is_italic else "normal"};
                color: {color};
                padding: 10px;
                background: transparent;
            }}
        """
        self.target_label.setStyleSheet(style)
        self.target_label.setText(text)
        
        # Apply alignment
        align_text = self.align_combo.currentText()
        if align_text == "Left":
            self.target_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        elif align_text == "Right":
            self.target_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def reject(self):
        """Restore original settings."""
        # Calculate original values for the stylesheet
        font = self.original_font
        font_family = font.family()
        # Handle cases where pointSize is -1
        font_size = font.pointSize()
        if font_size <= 0:
            font_size = font.pixelSize() // 1.33 # Rough conversion if needed
            if font_size <= 0: font_size = 14
            
        style = f"""
            QLabel {{
                font-family: "{font_family}";
                font-size: {font_size}pt;
                font-weight: {"bold" if font.bold() else "normal"};
                font-style: {"italic" if font.italic() else "normal"};
                color: {self.original_color.name()};
                padding: 10px;
                background: transparent;
            }}
        """
        self.target_label.setStyleSheet(style)
        self.target_label.setText(self.original_text)
        self.target_label.setAlignment(self.original_align)
        super().reject()

class ViewerTextPanel(QWidget):
    """Simple panel for displaying text."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_admin = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.display_label = QLabel("Text")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setWordWrap(True)
        # Default starting style
        self.display_label.setStyleSheet("font-size: 14pt; padding: 10px; background: transparent;")
        self.layout.addWidget(self.display_label, 1)

    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin

    def get_settings(self):
        """Get current text and style as a dictionary."""
        color = self.display_label.palette().color(self.display_label.foregroundRole())
        if "color:" in self.display_label.styleSheet():
            import re
            match = re.search(r"color:\s*(#[0-9a-fA-F]+)", self.display_label.styleSheet())
            if match:
                color = QColor(match.group(1))

        return {
            "text": self.display_label.text(),
            "font_family": self.display_label.font().family(),
            "font_size": self.display_label.font().pointSize(),
            "bold": self.display_label.font().bold(),
            "italic": self.display_label.font().italic(),
            "color": color.name(),
            "alignment": int(self.display_label.alignment())
        }

    def set_settings(self, settings):
        """Apply settings from a dictionary."""
        text = settings.get("text", "Text")
        font_family = settings.get("font_family", "Segoe UI")
        font_size = settings.get("font_size", 14)
        is_bold = settings.get("bold", False)
        is_italic = settings.get("italic", False)
        color = settings.get("color", "#000000")
        alignment = settings.get("alignment", int(Qt.AlignmentFlag.AlignCenter))

        style = f"""
            QLabel {{
                font-family: "{font_family}";
                font-size: {font_size}pt;
                font-weight: {"bold" if is_bold else "normal"};
                font-style: {"italic" if is_italic else "normal"};
                color: {color};
                padding: 10px;
                background: transparent;
            }}
        """
        self.display_label.setStyleSheet(style)
        self.display_label.setText(text)
        self.display_label.setAlignment(Qt.Alignment(alignment))

    def mouseDoubleClickEvent(self, event):
        if not self.is_admin:
            return super().mouseDoubleClickEvent(event)
            
        dialog = TextEditDialog(self.display_label, self)
        if not dialog.exec():
            # Restoration is handled by dialog.reject()
            pass

class ImageSettingsDialog(QDialog):
    """Dialog for image panel settings (image, margin, alignment)."""
    settings_changed = Signal(dict)

    def __init__(self, current_path, current_margin, current_align, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Image Selection
        img_group = QVBoxLayout()
        img_group.setSpacing(5)
        img_group.addWidget(QLabel("Image Source:"))
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(current_path)
        self.path_edit.setPlaceholderText("No image selected")
        self.path_edit.setReadOnly(True)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_image)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        img_group.addLayout(path_layout)
        layout.addLayout(img_group)
        
        # Margin
        margin_group = QVBoxLayout()
        margin_group.setSpacing(5)
        
        margin_header = QHBoxLayout()
        margin_header.addWidget(QLabel("Margin:"))
        self.margin_val_label = QLabel(f"{current_margin}px")
        margin_header.addWidget(self.margin_val_label)
        margin_header.addStretch()
        margin_group.addLayout(margin_header)
        
        self.margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.margin_slider.setRange(0, 100)
        self.margin_slider.setValue(current_margin)
        self.margin_slider.valueChanged.connect(self._on_margin_changed)
        margin_group.addWidget(self.margin_slider)
        
        layout.addLayout(margin_group)

        # Alignment
        align_group = QVBoxLayout()
        align_group.setSpacing(5)
        align_group.addWidget(QLabel("Alignment:"))
        
        self.align_combo = QComboBox()
        self.align_options = [
            ("Center", Qt.AlignmentFlag.AlignCenter),
            ("Top", Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter),
            ("Bottom", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter),
            ("Left", Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            ("Right", Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ]
        
        for name, flag in self.align_options:
            self.align_combo.addItem(name, flag)
            
        # Set current selection
        current_found = False
        for i in range(self.align_combo.count()):
            if self.align_combo.itemData(i) == current_align:
                self.align_combo.setCurrentIndex(i)
                current_found = True
                break
        
        if not current_found:
            self.align_combo.setCurrentIndex(0)
        
        self.align_combo.currentIndexChanged.connect(self._emit_settings)
        align_group.addWidget(self.align_combo)
        layout.addLayout(align_group)
        
        # Action Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self.path_edit.setText(path)
            self._emit_settings()
            
    def _on_margin_changed(self, value):
        self.margin_val_label.setText(f"{value}px")
        self._emit_settings()
    
    def _emit_settings(self):
        self.settings_changed.emit(self.get_settings())

    def get_settings(self):
        return {
            "path": self.path_edit.text(),
            "margin": self.margin_slider.value(),
            "alignment": self.align_combo.currentData()
        }

class ViewerImagePanel(QWidget):
    """Simple panel for displaying an image with adjustable margin."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_admin = False
        self._pixmap = None
        self._image_path = ""
        self._margin = 0
        self._alignment = Qt.AlignmentFlag.AlignCenter
        self._setup_ui()
        
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.image_label = QLabel("Double-click to edit (Admin)")
        self.image_label.setAlignment(self._alignment)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(10, 10) # Allow shrinking
        self.layout.addWidget(self.image_label, 1)

    def set_admin_mode(self, is_admin: bool, config=None):
        self.is_admin = is_admin
        if not self._image_path:
            text = "Double-click to edit (Admin)" if is_admin else "No Image"
            self.image_label.setText(text)

    def mouseDoubleClickEvent(self, event):
        if not self.is_admin:
            return super().mouseDoubleClickEvent(event)
        
        # Save current settings for restoration if cancelled
        original_settings = self.get_settings()
        
        dialog = ImageSettingsDialog(self._image_path, self._margin, self._alignment, self)
        # Connect real-time update
        dialog.settings_changed.connect(self._apply_settings)
        
        if dialog.exec():
            # Apply confirmed settings (already applied via signal, but safe to set again or ensure robustness)
            self._apply_settings(dialog.get_settings())
        else:
            # Cancelled, revert to original settings
            self._apply_settings(original_settings)

    def _apply_settings(self, settings):
        path = settings.get("path")
        margin = settings.get("margin", 0)
        alignment = settings.get("alignment", Qt.AlignmentFlag.AlignCenter)
        
        self._margin = margin
        self.layout.setContentsMargins(margin, margin, margin, margin)
        
        self._alignment = alignment
        self.image_label.setAlignment(alignment)
        
        if path != self._image_path:
            self.load_image(path)
        else:
            # Just re-render if only margin/alignment changed
            self._update_image_display()

    def load_image(self, path):
        """Public method to load image from path."""
        if path and os.path.exists(path):
            self._image_path = path
            self._pixmap = QPixmap(path)
            self.image_label.setText("")
            self._update_image_display()
        else:
            self._image_path = ""
            self._pixmap = None
            text = "Double-click to edit (Admin)" if self.is_admin else "No Image"
            self.image_label.setText(text)
            self.image_label.setPixmap(QPixmap())

    def _update_image_display(self):
        if self._pixmap and not self._pixmap.isNull():
            label_size = self.image_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled = self._pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
        else:
             if hasattr(self, 'image_label'): # Guard against init issues
                 if not self.image_label.pixmap() or self.image_label.pixmap().isNull():
                     if not self.image_label.text():
                         text = "Double-click to edit (Admin)" if self.is_admin else "No Image"
                         self.image_label.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image_display()

    def get_settings(self):
        return {
            "path": self._image_path,
            "margin": self._margin,
            "alignment": int(self._alignment)
        }

    def set_settings(self, settings):
        path = settings.get("path", "")
        margin = settings.get("margin", 0)
        align_int = settings.get("alignment", int(Qt.AlignmentFlag.AlignCenter))
        
        try:
            alignment = Qt.AlignmentFlag(align_int)
        except:
            alignment = Qt.AlignmentFlag.AlignCenter

        self._apply_settings({
            "path": path,
            "margin": margin,
            "alignment": alignment
        })


class MinimalScanDialog(QDialog):
    """A minimal dialog with just a progress bar for scanning."""
    devices_found = Signal(list)
    
    def __init__(self, parent=None, port="", baud=9600, parity="N", stop_bits=1, timeout=0.1, limit=100):
        super().__init__(parent)
        self.setWindowTitle("Scanning Devices...")
        self.setFixedSize(300, 130)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Initializing scan on {port}...")
        layout.addWidget(self.label)
        
        self.progress = QProgressBar()
        self.progress.setRange(1, limit)
        layout.addWidget(self.progress)
        
        self.found_label = QLabel("Devices found: 0")
        layout.addWidget(self.found_label)
        
        self.cancel_btn = QPushButton("Cancel")
        layout.addWidget(self.cancel_btn)
        
        self.found_ids = []
        
        self.worker = ScanWorker(
            port=port,
            baud_rate=baud,
            register_address=0,
            parity=parity,
            stop_bits=stop_bits,
            timeout=timeout
        )
        # Override the 247 range by connecting to progress and stopping early if needed?
        # Actually ScanWorker loop is hardcoded to range(1, 248).
        # We can just stop it manually if it exceeds limit or if finished.
        
        self.worker.progress.connect(self._on_progress)
        self.worker.found.connect(self._on_found)
        self.worker.finished.connect(self._on_finished)
        self.cancel_btn.clicked.connect(self._on_cancel)
        
        self.limit = limit
        self.worker.start()

    def _on_progress(self, slave_id):
        if slave_id > self.limit:
            self.worker.cancel()
            return
        self.progress.setValue(slave_id)
        self.label.setText(f"Probing Slave ID: {slave_id}")

    def _on_found(self, slave_id):
        if slave_id <= self.limit:
            self.found_ids.append(slave_id)
            self.found_label.setText(f"Devices found: {len(self.found_ids)}")

    def _on_finished(self, all_found):
        # Already stopped, just cleanup and leave
        self.devices_found.emit(self.found_ids)
        if self.isVisible():
            self.accept()

    def _on_cancel(self):
        self.worker.cancel()
        self.worker.wait() # Block until stopped
        self.devices_found.emit(self.found_ids)
        self.reject()

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        super().closeEvent(event)
class ConnectionPanel(QWidget):
    """Integrated panel for connection controls."""
    refresh_ports = Signal()
    perform_scan = Signal()
    toggle_connection = Signal(bool)
    device_menu_hide = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.update_style()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(10)
        
        # Port Selection Area
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.port_combo.setFixedHeight(32)
        self.layout.addWidget(self.port_combo)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("Refresh Serial Ports")
        self.refresh_btn.clicked.connect(self.refresh_ports.emit)
        self.layout.addWidget(self.refresh_btn)
        
        self.layout.addSpacing(10)
        
        # Scan Button
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setFixedHeight(32)
        self.scan_btn.setToolTip("Scan for Modbus devices")
        self.scan_btn.clicked.connect(self.perform_scan.emit)
        self.layout.addWidget(self.scan_btn)
        
        self.layout.addSpacing(10)
        
        # Device Selection Button
        self.device_btn = QToolButton()
        self.device_btn.setText("Select Devices")
        self.device_btn.setMinimumWidth(150)
        self.device_btn.setFixedHeight(32)
        self.device_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.device_btn.setToolTip("Select devices to connect to")
        self.device_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        self.device_menu = QMenu(self)
        self.device_btn.setMenu(self.device_menu)
        self.device_menu.aboutToHide.connect(self.device_menu_hide.emit)
        self.layout.addWidget(self.device_btn)
        
        self.layout.addSpacing(10)
        
        # Connect Button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.setFixedHeight(32)
        self.connect_btn.setMinimumWidth(100)
        self.connect_btn.toggled.connect(self._on_connect_toggled)
        self.layout.addWidget(self.connect_btn)
        
        self.layout.addStretch()
    
    def _on_connect_toggled(self, checked: bool):
        """Handle connect button toggle and update appearance."""
        if checked:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: 1px solid #1976d2;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
            """)
        else:
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("")
        
        # Emit the signal with the checked state
        self.toggle_connection.emit(checked)

    def set_admin_mode(self, is_admin: bool, config=None):
        # Update style on admin mode change (or theme change)
        self.update_style()
        
    def update_style(self):
         self.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['bg_widget']};")
         # Re-apply connect button style if needed
         if hasattr(self, 'connect_btn') and self.connect_btn.isChecked():
             self._on_connect_toggled(True)
