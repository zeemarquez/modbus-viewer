"""
Minimalist main window for Modbus Viewer.
"""

import os
import base64
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, 
    QLabel, QComboBox, QToolButton, QDialog, QLineEdit, QSpinBox,
    QPushButton, QFormLayout, QSizePolicy, QMenu, QDockWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, QByteArray
from PySide6.QtGui import QAction, QIcon

from src.models.project import Project, ConnectionSettings
from src.models.viewer_config import ViewerConfig
from src.core.modbus_manager import ModbusManager
from src.core.data_engine import DataEngine
from src.utils.serial_ports import get_available_ports
from src.ui.viewer.components import (
    ViewerTableView, ViewerPlotView, ViewerVariablesPanel, ViewerBitsPanel,
    MinimalScanDialog
)
from src.ui.scan_dialog import ScanWorker
from src.ui.styles import COLORS

class AdminLoginDialog(QDialog):
    """Password protection dialog for admin access."""
    def __init__(self, correct_password, parent=None):
        super().__init__(parent)
        self.correct_password = correct_password
        self.setWindowTitle("Admin Access")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.password_input)
        layout.addLayout(form)
        
        buttons = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.accept)
        login_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(login_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def is_authenticated(self):
        return self.password_input.text() == self.correct_password

class ViewerWindow(QMainWindow):
    """Simplified Modbus Viewer window."""
    
    def __init__(self):
        super().__init__()
        
        # Load Viewer Config
        self.config = ViewerConfig.load()
        
        # Initialize Core components
        self.project = Project()
        self.modbus = ModbusManager()
        self.data_engine = DataEngine()
        self.data_engine.modbus = self.modbus
        
        self.is_admin = False  # Start as user by default
        self._found_devices = []
        
        # Setup UI
        self.setWindowTitle("Modbus Viewer")
        self.setMinimumSize(1000, 600)
        self._set_window_icon()
        
        # UI Components
        self._setup_ui()
        self._setup_connections()
        
        # Load settings (geometry and layout)
        self._load_settings()
        
        # Initial load
        if self.config.project_path and os.path.exists(self.config.project_path):
            self._load_project(self.config.project_path)
        
        self._refresh_ports()
        if not self.config.project_path:
            self._update_device_menu()
        self._update_ui_state()
        
        # Status update timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(500)

    def _set_window_icon(self) -> None:
        """Set window icon from assets."""
        icon_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets", "icon.ico"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets", "icon.png"),
        ]
        for path in icon_paths:
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                break

    def _setup_ui(self):
        # Allow nested docks
        self.setDockNestingEnabled(True)
        
        # Central widget (must exist but can be minimal)
        central = QWidget()
        central.setMaximumSize(0, 0)
        self.setCentralWidget(central)
        
        # Table Dock
        self.table_dock = QDockWidget("Registers", self)
        self.table_dock.setObjectName("TableDock")
        self.table_view = ViewerTableView()
        self.table_view.project = self.project
        self.table_dock.setWidget(self.table_view)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.table_dock)
        
        # Plot Dock
        self.plot_dock = QDockWidget("Plot", self)
        self.plot_dock.setObjectName("PlotDock")
        self.plot_view = ViewerPlotView()
        self.plot_dock.setWidget(self.plot_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.plot_dock)
        
        # Variables Dock
        self.variables_dock = QDockWidget("Variables", self)
        self.variables_dock.setObjectName("VariablesDock")
        self.variables_panel = ViewerVariablesPanel()
        self.variables_panel.project = self.project
        self.variables_dock.setWidget(self.variables_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.variables_dock)
        
        # Bits Dock
        self.bits_dock = QDockWidget("Bits", self)
        self.bits_dock.setObjectName("BitsDock")
        self.bits_panel = ViewerBitsPanel()
        self.bits_panel.project = self.project
        self.bits_dock.setWidget(self.bits_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bits_dock)
        
        # Orientation
        self.splitDockWidget(self.table_dock, self.plot_dock, Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.plot_dock, self.variables_dock)
        self.tabifyDockWidget(self.variables_dock, self.bits_dock)
        
        # Toolbar
        self.toolbar = QToolBar("Viewer Toolbar")
        self.toolbar.setObjectName("ViewerToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        self.toolbar.addWidget(QLabel(" Port: "))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.toolbar.addWidget(self.port_combo)
        
        self.refresh_ports_action = QAction("↻", self)
        self.refresh_ports_action.triggered.connect(self._refresh_ports)
        self.toolbar.addAction(self.refresh_ports_action)
        
        self.toolbar.addSeparator()
        
        self.scan_action = QAction("Scan", self)
        self.scan_action.setToolTip("Scan for Modbus devices")
        self.scan_action.triggered.connect(self._perform_scan)
        self.toolbar.addAction(self.scan_action)
        
        self.toolbar.addSeparator()
        
        # Device Selection (multi-select dropdown)
        self.device_btn = QToolButton()
        self.device_btn.setText("Select Devices")
        self.device_btn.setMinimumWidth(150)
        self.device_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.device_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        self.device_btn.setToolTip("Select devices to connect to (multi-select)")
        
        self.device_menu = QMenu(self)
        self.device_btn.setMenu(self.device_menu)
        self.device_menu.aboutToHide.connect(self._on_device_menu_about_to_hide)
        self.toolbar.addWidget(self.device_btn)
        
        self.toolbar.addSeparator()
        
        # Connect Action
        self.connect_action = QAction("Connect", self)
        self.connect_action.setCheckable(True)
        self.connect_action.triggered.connect(self._toggle_connection)
        self.toolbar.addAction(self.connect_action)
        
        # Menu Bar
        self._setup_menu()
        
        # Status Bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.connection_label = QLabel("🔴 Disconnected")
        self.connection_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 500;")
        self.statusbar.addWidget(self.connection_label)
        
        self.poll_label = QLabel("Poll: --")
        self.statusbar.addPermanentWidget(self.poll_label)

    def _setup_menu(self):
        """Setup the top menu bar."""
        menubar = self.menuBar()
        menubar.clear()
        
        self.options_menu = menubar.addMenu("Options")
        self.view_menu = menubar.addMenu("View")
        self._update_options_menu()
        self._update_view_menu()

    def _update_view_menu(self):
        """Update View menu with dock toggle actions."""
        self.view_menu.clear()
        self.view_menu.setEnabled(self.is_admin)
        
        if self.is_admin:
            docks = [
                (self.table_dock, "Registers"),
                (self.plot_dock, "Plot"),
                (self.variables_dock, "Variables"),
                (self.bits_dock, "Bits")
            ]
            for dock, name in docks:
                action = dock.toggleViewAction()
                action.setText(name)
                self.view_menu.addAction(action)

    def _update_options_menu(self):
        """Update Options menu based on admin state."""
        self.options_menu.clear()
        
        if not self.is_admin:
            login_action = self.options_menu.addAction("Login as Admin...")
            login_action.triggered.connect(self._on_admin_clicked)
        else:
            import_action = self.options_menu.addAction("Import Registers (JSON)...")
            import_action.triggered.connect(self._import_project)
            
            settings_action = self.options_menu.addAction("Connection Settings...")
            settings_action.triggered.connect(self._show_admin_settings)
            
            scan_settings_action = self.options_menu.addAction("Scanning Options...")
            scan_settings_action.triggered.connect(self._show_scanning_options)
            
            self.options_menu.addSeparator()
            
            logout_action = self.options_menu.addAction("Logout Admin")
            logout_action.triggered.connect(self._logout_admin)

    def _setup_connections(self):
        self.data_engine.data_updated.connect(self._on_data_updated)
        self.data_engine.error_occurred.connect(self._on_error)
        self.data_engine.connection_lost.connect(self._on_connection_lost)
        self.table_view.visibility_changed.connect(self._on_visibility_changed)
        self.variables_panel.visibility_changed.connect(self._on_visibility_changed)
        self.bits_panel.visibility_changed.connect(self._on_visibility_changed)
        self.bits_panel.bit_value_changed.connect(self._on_bit_value_changed)

    def _on_visibility_changed(self):
        """Update live registers and sync tabs when visibility toggles."""
        self.table_view._rebuild_tabs()
        self.table_view._update_column_visibility()
        self.variables_panel._rebuild_tabs()
        self.variables_panel._update_column_visibility()
        self.bits_panel._rebuild_tabs()
        self.bits_panel._update_column_visibility()
        
        if not self.is_admin:
            self._sync_registers()

    def _on_bit_value_changed(self, slave_id, addr, value):
        """Handle bit changes and write to Modbus."""
        if self.modbus.is_connected:
            try:
                self.modbus.write_register(slave_id, addr, value)
                self.statusbar.showMessage(f"Bit updated in D{slave_id}.R{addr}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Write Error", str(e))
                self.bits_panel.clear_pending(slave_id, addr)

    def _refresh_ports(self):
        current = self.port_combo.currentData()
        self.port_combo.clear()
        ports = get_available_ports()
        for port, description in ports:
            self.port_combo.addItem(f"{port} - {description}", port)
        target_port = current if current else self.config.port
        if target_port:
            index = self.port_combo.findData(target_port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def _on_device_menu_about_to_hide(self):
        """Called when device menu is about to hide - sync selected devices."""
        selected = []
        for action in self.device_menu.actions():
            if action.isCheckable() and action.isChecked():
                slave_id = action.data()
                if slave_id is not None:
                    selected.append(slave_id)
        
        if selected != self.config.slave_ids:
            self._update_active_devices(sorted(selected))
            self._update_device_btn_text()

    def _update_device_btn_text(self):
        """Update the device button text based on selection."""
        selected = self.config.slave_ids
        if not selected:
            if self._found_devices:
                self.device_btn.setText("Select Devices")
            else:
                self.device_btn.setText("Run Scan")
        elif len(selected) == 1:
            self.device_btn.setText(f"Device {selected[0]}")
        else:
            self.device_btn.setText(f"{len(selected)} Devices")

    def _perform_scan(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "No Port", "Please select a COM port before scanning.")
            return
            
        dialog = MinimalScanDialog(
            parent=self,
            port=port,
            baud=self.config.baud_rate,
            parity=self.config.parity,
            stop_bits=self.config.stop_bits,
            timeout=self.config.scan_timeout,
            limit=self.config.scan_slave_limit
        )
        
        def on_devices_found(ids):
            if not ids:
                QMessageBox.information(self, "Scan Result", "No devices found.")
            else:
                self._found_devices = ids
                self.config.slave_ids = ids
                self.config.save()
                self._update_device_menu()
                if ids:
                    self._update_active_devices(ids)
        
        dialog.devices_found.connect(on_devices_found)
        dialog.exec()

    def _update_device_menu(self):
        """Update the device selection menu."""
        self.device_menu.clear()
        
        # Combine project devices and found devices
        project_ids = []
        if hasattr(self, 'project') and self.project:
            project_ids = [r.slave_id for r in self.project.registers]
        
        all_ids = sorted(list(set(project_ids + self._found_devices + self.config.slave_ids)))
        
        if not all_ids:
            no_devices_action = QAction("No devices found", self)
            no_devices_action.setEnabled(False)
            self.device_menu.addAction(no_devices_action)
            self.device_btn.setText("Select Devices")
            return

        # Add select all / deselect all actions
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self._select_all_devices)
        self.device_menu.addAction(select_all_action)
        
        deselect_all_action = QAction("Deselect All", self)
        deselect_all_action.triggered.connect(self._deselect_all_devices)
        self.device_menu.addAction(deselect_all_action)
        
        self.device_menu.addSeparator()
        
        # Add checkable action for each device
        for slave_id in all_ids:
            action = QAction(f"Device {slave_id}", self)
            action.setCheckable(True)
            action.setChecked(slave_id in self.config.slave_ids)
            action.setData(slave_id)
            self.device_menu.addAction(action)
        
        self._update_device_btn_text()

    def _select_all_devices(self):
        """Select all devices."""
        all_ids = []
        for action in self.device_menu.actions():
            if action.isCheckable():
                action.setChecked(True)
                all_ids.append(action.data())
        self._update_active_devices(sorted(all_ids))
        self._update_device_btn_text()

    def _deselect_all_devices(self):
        """Deselect all devices."""
        for action in self.device_menu.actions():
            if action.isCheckable():
                action.setChecked(False)
        self._update_active_devices([])
        self._update_device_btn_text()

    def _update_active_devices(self, slave_ids):
        self.config.slave_ids = slave_ids
        self._sync_registers()

    def _toggle_connection(self, checked):
        if checked:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        port = self.port_combo.currentData()
        if not port:
            self.connect_action.setChecked(False)
            return

        slave_ids = self.config.slave_ids if self.config.slave_ids else [1]
        
        try:
            self.modbus.connect(
                port=port,
                slave_ids=slave_ids,
                baud_rate=self.config.baud_rate,
                parity=self.config.parity,
                stop_bits=self.config.stop_bits,
                timeout=self.config.timeout
            )
            self.connection_label.setText(f"🟢 Connected: {port}")
            self.connection_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: 500;")
            self._sync_registers()
            self.data_engine.start()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connect_action.setChecked(False)

    def _disconnect(self):
        self.data_engine.stop()
        self.modbus.disconnect()
        self.connection_label.setText("🔴 Disconnected")
        self.connection_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 500;")

    def _sync_registers(self):
        slave_ids = self.config.slave_ids if self.config.slave_ids else [1]
        
        # Sync Table
        self.table_view.set_registers(self.project.registers)
        self.table_view.set_slave_ids(slave_ids)
        
        # Sync Variables
        self.variables_panel.set_registers(self.project.registers)
        self.variables_panel.set_variables(self.project.variables)
        self.variables_panel.set_slave_ids(slave_ids)
        
        # Sync Bits
        self.bits_panel.set_registers(self.project.registers)
        self.bits_panel.set_bits(self.project.bits)
        self.bits_panel.set_slave_ids(slave_ids, self.table_view.get_live_registers())
        
        live_registers = self.table_view.get_live_registers()
        live_variables = self.variables_panel.get_live_variables()
        live_bits = self.bits_panel.get_live_bits()
        
        self.data_engine.set_registers(live_registers)
        self.data_engine.set_variables(live_variables)
        
        self.plot_view.set_registers(live_registers)
        self.plot_view.set_variables(live_variables)

    def _on_admin_clicked(self):
        dialog = AdminLoginDialog(self.config.admin_password, self)
        if dialog.exec() and dialog.is_authenticated():
            self.is_admin = True
            self._update_ui_state()
        else:
            if dialog.password_input.text():
                QMessageBox.warning(self, "Access Denied", "Incorrect password")

    def _logout_admin(self):
        self.is_admin = False
        self._update_ui_state()

    def _update_ui_state(self):
        # Pass admin mode and config to components
        self.table_view.set_admin_mode(self.is_admin, self.config)
        
        # Refresh the menus
        self._update_options_menu()
        self._update_view_menu()
        
        # Enable dragging/floating only for admin
        if self.is_admin:
            features = (
                QDockWidget.DockWidgetFeature.DockWidgetMovable |
                QDockWidget.DockWidgetFeature.DockWidgetFloatable
            )
        else:
            features = QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
            
        self.table_dock.setFeatures(features)
        self.plot_dock.setFeatures(features)
        self.variables_dock.setFeatures(features)
        self.bits_dock.setFeatures(features)
        
        # In simple viewer, hide plot options and maximize buttons from regular users
        self.plot_view.options_btn.setVisible(self.is_admin)
        self.plot_view.maximize_btn.setVisible(self.is_admin)
        self.plot_view.clear_btn.setVisible(self.is_admin)
        
        self.table_view.set_admin_mode(self.is_admin, self.config)
        self.variables_panel.set_admin_mode(self.is_admin, self.config)
        self.bits_panel.set_admin_mode(self.is_admin, self.config)

    def _import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Registers", "", "JSON (*.json)")
        if path:
            self._load_project(path)
            self.config.project_path = path
            self.config.save()

    def _load_project(self, path):
        try:
            self.project = Project.load(path)
            self.table_view.project = self.project
            self.variables_panel.project = self.project
            self.bits_panel.project = self.project
            
            # Populate combo with project's devices
            slave_ids = sorted(list(set(r.slave_id for r in self.project.registers)))
            self._update_device_menu()
            
            # Default to first one or all if none selected
            if slave_ids and not self.config.slave_ids:
                self._update_active_devices([slave_ids[0]])
            
            self._sync_registers()
            self._update_ui_state()
            self.statusbar.showMessage(f"Imported {len(self.project.registers)} registers", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def _show_scanning_options(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Scanning Options")
        layout = QFormLayout(dialog)
        
        timeout_spin = QLineEdit(str(self.config.scan_timeout))
        layout.addRow("Probe Timeout (s):", timeout_spin)
        
        limit_spin = QSpinBox()
        limit_spin.setRange(1, 247)
        limit_spin.setValue(self.config.scan_slave_limit)
        layout.addRow("Slave ID Limit:", limit_spin)
        
        btns = QPushButton("Save")
        btns.clicked.connect(dialog.accept)
        layout.addRow(btns)
        
        if dialog.exec():
            try:
                self.config.scan_timeout = float(timeout_spin.text())
                self.config.scan_slave_limit = limit_spin.value()
                self.config.save()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Timeout must be a number.")

    def _show_admin_settings(self):
        # Full connection settings matching Explorer
        dialog = QDialog(self)
        dialog.setWindowTitle("Connection Settings")
        layout = QFormLayout(dialog)
        
        baud = QComboBox()
        baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        baud.setCurrentText(str(self.config.baud_rate))
        layout.addRow("Baud Rate:", baud)
        
        parity = QComboBox()
        parity.addItems(["None", "Even", "Odd"])
        parity_map_inv = {"N": "None", "E": "Even", "O": "Odd"}
        parity.setCurrentText(parity_map_inv.get(self.config.parity, "None"))
        layout.addRow("Parity:", parity)
        
        stopbits = QComboBox()
        stopbits.addItems(["1", "2"])
        stopbits.setCurrentText(str(self.config.stop_bits))
        layout.addRow("Stop Bits:", stopbits)
        
        timeout = QLineEdit(str(int(self.config.timeout * 1000)))
        layout.addRow("Timeout (ms):", timeout)
        
        btns = QPushButton("Save")
        btns.clicked.connect(dialog.accept)
        layout.addRow(btns)
        
        if dialog.exec():
            try:
                self.config.baud_rate = int(baud.currentText())
                p_map = {"None": "N", "Even": "E", "Odd": "O"}
                self.config.parity = p_map[parity.currentText()]
                self.config.stop_bits = int(stopbits.currentText())
                self.config.timeout = float(timeout.text()) / 1000.0
                self.config.save()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Timeout must be a number.")

    def _on_data_updated(self):
        self.table_view.update_values()
        self.variables_panel.update_values()
        self.bits_panel.update_values()
        self.plot_view.update_plot(self.data_engine)

    def _on_error(self, msg):
        self.statusbar.showMessage(f"Error: {msg}", 5000)

    def _on_connection_lost(self):
        self.connect_action.setChecked(False)
        self._disconnect()
        QMessageBox.warning(self, "Connection Lost", "Modbus connection lost.")

    def _update_status(self):
        if self.data_engine.is_running:
            stats = self.data_engine.statistics
            self.poll_label.setText(f"Poll: {stats['last_poll_duration']:.1f}ms")
        else:
            self.poll_label.setText("Poll: --")

    def _load_settings(self):
        """Load window geometry and dock layout."""
        if self.config.geometry:
            try:
                geom = base64.b64decode(self.config.geometry)
                self.restoreGeometry(QByteArray(geom))
            except Exception:
                pass
        
        if self.config.layout_state:
            try:
                state = base64.b64decode(self.config.layout_state)
                self.restoreState(QByteArray(state))
            except Exception:
                pass

    def _save_settings(self):
        """Save window geometry and dock layout."""
        geom = self.saveGeometry().data()
        self.config.geometry = base64.b64encode(geom).decode('utf-8')
        
        state = self.saveState().data()
        self.config.layout_state = base64.b64encode(state).decode('utf-8')
        
        # Also save port selection
        self.config.port = self.port_combo.currentData() or ""
        
        self.config.save()

    def closeEvent(self, event):
        self._save_settings()
        self._disconnect()
        event.accept()

