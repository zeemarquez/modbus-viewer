from PySide6.QtWidgets import (
    QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMenu, QCheckBox, QWidget, QAbstractItemView, QLabel,
    QDialog, QProgressBar, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
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
        self._rebuild_tabs()
        self._update_column_visibility()

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the table UI without the toolbar."""
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
    
    def _setup_ui(self) -> None:
        """Setup the plot UI (can be further customized if needed)."""
        # For now, reuse parent but we could hide specific buttons here
        super()._setup_ui()
        # For example, we could hide the 'Options' or 'Maximize' button in user mode
        # For example, we could hide the 'Options' or 'Maximize' button in user mode
        # self.maximize_btn.setVisible(False)
        pass

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
        self._rebuild_tabs()
        self._update_column_visibility()

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the panel UI without the toolbar."""
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
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_menu)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
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
        self._rebuild_tabs()
        self._update_column_visibility()

    def _rebuild_tabs(self):
        """Recreate device tabs with current filtering."""
        super()._rebuild_tabs()
        self._update_column_visibility()

    def _setup_ui(self) -> None:
        """Setup the panel UI without the toolbar."""
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
