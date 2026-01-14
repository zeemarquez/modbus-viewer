"""
Minimalist main window for Modbus Viewer.
"""

import os
import base64
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, 
    QLabel, QComboBox, QToolButton, QDialog, QLineEdit, QSpinBox,
    QPushButton, QFormLayout, QSizePolicy, QMenu, QDockWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QByteArray
from PySide6.QtGui import QAction, QIcon

from src.models.project import Project, ConnectionSettings
from src.models.viewer_config import ViewerConfig
from src.core.modbus_manager import ModbusManager
from src.core.data_engine import DataEngine
from src.utils.serial_ports import get_available_ports
from src.utils.resources_manager import (
    copy_project_to_resources, resolve_resource_path, 
    migrate_absolute_path_to_relative, ensure_resources_directories
)
from src.ui.viewer.components import (
    ViewerTableView, ViewerPlotView, ViewerVariablesPanel, ViewerBitsPanel,
    MinimalScanDialog, ViewerTextPanel, ViewerImagePanel, ConnectionPanel,
    RecordingPanel
)
from src.ui.viewer.calibration_dialog import CalibrationDialog
from src.ui.viewer.window_properties_dialog import WindowPropertiesDialog
from src.ui.scan_dialog import ScanWorker
from src.ui.styles import COLORS, apply_theme

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
        
        # Apply configured theme
        if self.config.app_theme != "light":
            apply_theme(QApplication.instance(), self.config.app_theme)
        
        # Initialize Core components
        self.project = Project()
        self.modbus = ModbusManager()
        self.data_engine = DataEngine()
        self.data_engine.modbus = self.modbus
        
        self.is_admin = False  # Start as user by default
        self._found_devices = []
        self._connection_lost_dialog_shown = False  # Flag to prevent multiple dialogs
        
        # Clean devices on startup - User must scan first
        self.config.slave_ids = []
        self.config.save()
        
        # Setup UI
        # Load window title and icon from config
        window_title = self.config.window_title or "Modbus Viewer"
        self.setWindowTitle(window_title)
        self.setMinimumSize(1000, 600)
        self._set_window_icon()
        
        # UI Components
        self._setup_ui()
        self._setup_connections()
        
        # Load settings (geometry and layout)
        self._load_settings()
        
        # Ensure resources directories exist
        ensure_resources_directories()
        
        # Initial load
        if self.config.project_path:
            resolved_path = resolve_resource_path(self.config.project_path)
            if resolved_path and os.path.exists(resolved_path):
                self._load_project(resolved_path)
            elif os.path.exists(self.config.project_path):
                # Old absolute path - migrate it
                relative_path = migrate_absolute_path_to_relative(self.config.project_path, "project")
                if relative_path:
                    self.config.project_path = relative_path
                    self.config.save()
                    resolved_path = resolve_resource_path(relative_path)
                    if resolved_path:
                        self._load_project(resolved_path)
        
        self._refresh_ports()
        if not self.config.project_path:
            self._update_device_menu()
        self._update_ui_state()
        
        # Status update timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(500)

    def _set_window_icon(self) -> None:
        """Set window icon from config or default assets."""
        # First try to load from config
        if self.config.window_icon_path:
            resolved_path = resolve_resource_path(self.config.window_icon_path)
            if resolved_path and os.path.exists(resolved_path):
                self.setWindowIcon(QIcon(resolved_path))
                return
        
        # Fallback to default assets
        icon_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets", "icon_viewer.png"),
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
        # Wrap plot view in container with margin for visual spacing
        plot_container = QWidget()
        plot_container_layout = QVBoxLayout(plot_container)
        plot_container_layout.setContentsMargins(10, 10, 10, 10)  # 10px margin
        plot_container_layout.setSpacing(0)
        self.plot_view = ViewerPlotView()
        plot_container_layout.addWidget(self.plot_view)
        self.plot_dock.setWidget(plot_container)
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
        
        # Recording Dock
        self.recording_dock = QDockWidget("Recording", self)
        self.recording_dock.setObjectName("RecordingDock")
        self.recording_panel = RecordingPanel()
        self.recording_panel.set_data_engine(self.data_engine)
        self.recording_dock.setWidget(self.recording_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.recording_dock)
        
        # Orientation
        self.splitDockWidget(self.table_dock, self.plot_dock, Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.plot_dock, self.variables_dock)
        self.tabifyDockWidget(self.variables_dock, self.bits_dock)
        self.tabifyDockWidget(self.bits_dock, self.recording_dock)
        
        # Connection Dock (Replacing Toolbar)
        self.connection_dock = QDockWidget("Connection", self)
        self.connection_dock.setObjectName("ConnectionDock")
        self.connection_panel = ConnectionPanel()
        self.connection_dock.setWidget(self.connection_panel)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.connection_dock)
        
        # Link references for backward compatibility with existing logic
        self.port_combo = self.connection_panel.port_combo
        self.device_btn = self.connection_panel.device_btn
        self.device_menu = self.connection_panel.device_menu
        
        # Connect signals from the panel
        self.connection_panel.refresh_ports.connect(self._refresh_ports)
        self.connection_panel.perform_scan.connect(self._perform_scan)
        self.connection_panel.toggle_connection.connect(self._toggle_connection)
        self.connection_panel.device_menu_hide.connect(self._on_device_menu_about_to_hide)
        
        # Need a reference to the connect button for status updates in code
        self.connect_action = self.connection_panel.connect_btn
        
        # Menu Bar
        self._setup_menu()
        
        # Global shortcut (Ctrl+T) for toggling connection panel
        self.toggle_connection_action = QAction("Toggle Connection Panel", self)
        self.toggle_connection_action.setShortcut("Ctrl+T")
        self.toggle_connection_action.triggered.connect(self._on_toggle_connection_dock)
        self.addAction(self.toggle_connection_action)
        
        # Status Bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.connection_label = QLabel(f'<span style="color: {COLORS["error"]};">●</span> Disconnected')
        self.connection_label.setStyleSheet("font-weight: 500;")
        self.statusbar.addWidget(self.connection_label)
        
        self.poll_label = QLabel("Poll: --")
        self.statusbar.addPermanentWidget(self.poll_label)
        
        # Initialize button states
        self._update_connection_button_state()

    def _setup_menu(self):
        """Setup the top menu bar."""
        menubar = self.menuBar()
        menubar.clear()
        
        self.options_menu = menubar.addMenu("Options")
        self.view_menu = menubar.addMenu("View")
        self.themes_menu = menubar.addMenu("Themes")
        self.insert_menu = menubar.addMenu("Insert")
        self._update_options_menu()
        self._update_view_menu()
        self._update_themes_menu()
        self._update_insert_menu()

    def _update_view_menu(self):
        """Update View menu with dock toggle actions for all current docks."""
        self.view_menu.clear()
        self.view_menu.setEnabled(self.is_admin)
        self.view_menu.menuAction().setVisible(self.is_admin)
        
        if not self.is_admin:
            return
            
        # Get all current docks
        all_docks = self.findChildren(QDockWidget)
        
        # Sort them: fixed docks first, then others
        fixed_names = ["ConnectionDock", "TableDock", "PlotDock", "VariablesDock", "BitsDock", "RecordingDock"]
        
        # Connection first
        conn_dock = next((d for d in all_docks if d.objectName() == "ConnectionDock"), None)
        if conn_dock:
            action = conn_dock.toggleViewAction()
            action.setText("Connection Panel")
            action.setShortcut("Ctrl+T")
            self.view_menu.addAction(action)
            self.view_menu.addSeparator()
            
        # Other fixed docks
        for name in fixed_names[1:]:
            dock = next((d for d in all_docks if d.objectName() == name), None)
            if dock:
                display_name = name.replace("Dock", "")
                action = dock.toggleViewAction()
                action.setText(display_name)
                self.view_menu.addAction(action)
                
        # Dynamic panels (Text, Image)
        dynamic_docks = [d for d in all_docks if d.objectName() not in fixed_names]
        if dynamic_docks:
            self.view_menu.addSeparator()
            for dock in dynamic_docks:
                action = dock.toggleViewAction()
                # Clean up the name for the menu (e.g., "TextPanel_abcd" -> "Text Panel (abcd)")
                raw_name = dock.objectName()
                if "_" in raw_name:
                    type_str, id_str = raw_name.split("_", 1)
                    # Insert space: TextPanel -> Text Panel
                    import re
                    type_str = re.sub(r"([a-z])([A-Z])", r"\1 \2", type_str)
                    action.setText(f"{type_str} ({id_str})")
                self.view_menu.addAction(action)

    def _update_insert_menu(self):
        """Update Insert menu based on admin state."""
        self.insert_menu.clear()
        self.insert_menu.setEnabled(self.is_admin)
        self.insert_menu.menuAction().setVisible(self.is_admin)
        
        if self.is_admin:
            text_action = self.insert_menu.addAction("Text Panel")
            text_action.triggered.connect(self._add_text_panel)
            
            image_action = self.insert_menu.addAction("Image Panel")
            image_action.triggered.connect(self._add_image_panel)

    def _update_themes_menu(self):
        """Update Themes menu based on admin state."""
        self.themes_menu.clear()
        self.themes_menu.setEnabled(self.is_admin)
        self.themes_menu.menuAction().setVisible(self.is_admin)
        
        if self.is_admin:
            light_action = self.themes_menu.addAction("Light theme")
            light_action.setCheckable(True)
            light_action.setChecked(self.config.app_theme == "light")
            light_action.triggered.connect(lambda: self._set_theme("light"))
            
            dark_action = self.themes_menu.addAction("Dark theme")
            dark_action.setCheckable(True)
            dark_action.setChecked(self.config.app_theme == "dark")
            dark_action.triggered.connect(lambda: self._set_theme("dark"))

    def _set_theme(self, theme_name):
        self.config.app_theme = theme_name
        self.config.save()
        apply_theme(QApplication.instance(), theme_name)
        self._update_themes_menu()
        self._update_ui_state()

    def _update_options_menu(self):
        """Update Options menu based on admin state."""
        self.options_menu.clear()
        
        # Calibration dialog - visible to both admin and basic users
        calibration_action = self.options_menu.addAction("Calibration...")
        calibration_action.triggered.connect(self._show_calibration_dialog)
        
        if not self.is_admin:
            self.options_menu.addSeparator()
            login_action = self.options_menu.addAction("Login as Admin...")
            login_action.triggered.connect(self._on_admin_clicked)
        else:
            self.options_menu.addSeparator()
            import_action = self.options_menu.addAction("Import Registers (JSON)...")
            import_action.triggered.connect(self._import_project)
            
            settings_action = self.options_menu.addAction("Connection Settings...")
            settings_action.triggered.connect(self._show_admin_settings)
            
            scan_settings_action = self.options_menu.addAction("Scanning Options...")
            scan_settings_action.triggered.connect(self._show_scanning_options)
            
            window_props_action = self.options_menu.addAction("Window Properties...")
            window_props_action.triggered.connect(self._show_window_properties)
            
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
            self._update_connection_button_state()

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
    
    def _update_connection_button_state(self):
        """Enable/disable connect button based on device selection."""
        has_devices = len(self.config.slave_ids) > 0
        self.connect_action.setEnabled(has_devices)

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
        
        # Show only found devices and current selection
        # (Exclude project_ids to force scan first as requested)
        all_ids = sorted(list(set(self._found_devices + self.config.slave_ids)))
        
        if not all_ids:
            no_devices_action = QAction("No devices found", self)
            no_devices_action.setEnabled(False)
            self.device_menu.addAction(no_devices_action)
            self.device_btn.setText("No devices")
            self.device_btn.setEnabled(False)
            self._update_connection_button_state()
            return
        
        # Enable device button when devices are found
        self.device_btn.setEnabled(True)

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
        self._update_connection_button_state()

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
            self.connection_label.setText(f'<span style="color: {COLORS["success"]};">●</span> Connected: {port}')
            self.connection_label.setStyleSheet("font-weight: 500;")
            self._connection_lost_dialog_shown = False  # Reset flag on successful connection
            self._sync_registers()
            self.data_engine.start()
            # Update recording panel connection state
            self.recording_panel.set_connection_state(True)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connect_action.setChecked(False)
            self.recording_panel.set_connection_state(False)

    def _disconnect(self):
        self.data_engine.stop()
        self.modbus.disconnect()
        self.connection_label.setText(f'<span style="color: {COLORS["error"]};">●</span> Disconnected')
        self.connection_label.setStyleSheet("font-weight: 500;")
        self._connection_lost_dialog_shown = False  # Reset flag on manual disconnect
        # Update recording panel connection state
        self.recording_panel.set_connection_state(False)

    def _sync_registers(self):
        slave_ids = self.config.slave_ids
        
        # Sync Table
        self.table_view.set_registers(self.project.registers)
        self.table_view.set_slave_ids(slave_ids)
        
        # Get live registers
        live_registers = self.table_view.get_live_registers()
        
        # Sync Variables
        # Pass live_registers (expanded with device IDs) so the evaluator can resolve references like D2.R100
        self.variables_panel.set_registers(live_registers)
        self.variables_panel.set_variables(self.project.variables)
        self.variables_panel.set_slave_ids(slave_ids)
        
        # Sync Bits
        self.bits_panel.set_registers(self.project.registers)
        self.bits_panel.set_bits(self.project.bits)
        self.bits_panel.set_slave_ids(slave_ids, live_registers)
        live_variables = self.variables_panel.get_live_variables()
        live_bits = self.bits_panel.get_live_bits()
        
        self.data_engine.set_registers(live_registers)
        self.data_engine.set_variables(live_variables)
        
        self.plot_view.set_registers(live_registers)
        self.plot_view.set_variables(live_variables)
        
        # Sync Recording panel
        self.recording_panel.set_registers(live_registers)
        self.recording_panel.set_variables(live_variables)

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
        self._update_themes_menu()
        self._update_insert_menu()
        
        # Enumerate all docks to set features and admin mode
        for dock in self.findChildren(QDockWidget):
            # Known fixed docks
            is_fixed = dock.objectName() in ("TableDock", "PlotDock", "VariablesDock", "BitsDock", "ConnectionDock", "RecordingDock")
            
            if self.is_admin:
                features = (
                    QDockWidget.DockWidgetFeature.DockWidgetMovable |
                    QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                    QDockWidget.DockWidgetFeature.DockWidgetClosable
                )
                dock.setFeatures(features)
                dock.setTitleBarWidget(None) # Show title for dragging and closing
            else:
                dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
                # Hide title for extra panels, connection, plot, and recording panels in user mode
                if not is_fixed or dock.objectName() in ("ConnectionDock", "PlotDock", "RecordingDock"):
                    dock.setTitleBarWidget(QWidget()) # Hide title
            
            # Propagate admin mode to widgets
            if hasattr(dock.widget(), 'set_admin_mode'):
                dock.widget().set_admin_mode(self.is_admin, self.config)
        
        # Show plot options and clear buttons to all users
        self.plot_view.options_btn.setVisible(True)
        self.plot_view.clear_btn.setVisible(True)
        # Remove maximize plot button
        self.plot_view.maximize_btn.setVisible(False)
        
        self.table_view.set_admin_mode(self.is_admin, self.config)
        self.variables_panel.set_admin_mode(self.is_admin, self.config)
        self.bits_panel.set_admin_mode(self.is_admin, self.config)
        self.plot_view.set_admin_mode(self.is_admin, self.config)
        self.recording_panel.set_admin_mode(self.is_admin, self.config)
        
        # Recording panel is visible to all users (same as other panels)
        # Set initial connection state
        self.recording_panel.set_connection_state(self.modbus.is_connected)

    def _import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Registers", "", "JSON (*.json)")
        if path:
            # Copy project to resources folder and use relative path
            relative_path = copy_project_to_resources(path)
            if relative_path:
                resolved_path = resolve_resource_path(relative_path)
                if resolved_path:
                    self._load_project(resolved_path)
                    self.config.project_path = relative_path
                    self.config.save()
                else:
                    QMessageBox.warning(self, "Error", "Failed to resolve project path.")
            else:
                QMessageBox.warning(self, "Error", "Failed to copy project to resources folder.")

    def _load_project(self, path):
        try:
            self.project = Project.load(path)
            self.table_view.project = self.project
            self.variables_panel.project = self.project
            self.bits_panel.project = self.project
            
            # Populate combo - strictly via _update_device_menu
            self._update_device_menu()
            
            self._sync_registers()
            self._update_ui_state()
            self.statusbar.showMessage(f"Imported {len(self.project.registers)} registers", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def _show_calibration_dialog(self):
        """Show the calibration dialog."""
        if not self.modbus.is_connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to the Modbus device before calibrating.")
            return
        
        # Get the first slave ID from config, or default to 1
        # If multiple devices are connected, use the first one
        slave_id = self.config.slave_ids[0] if self.config.slave_ids else 1
        
        if len(self.config.slave_ids) > 1:
            # If multiple devices, show a message
            QMessageBox.information(
                self,
                "Multiple Devices",
                f"Multiple devices connected. Calibration will be performed on Device {slave_id}.\n"
                "To calibrate a different device, disconnect others first."
            )
        
        dialog = CalibrationDialog(self.modbus, self.data_engine, slave_id, self)
        dialog.exec()
    
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

    def _show_window_properties(self):
        """Show the Window Properties dialog."""
        dialog = WindowPropertiesDialog(
            current_title=self.config.window_title or "Modbus Viewer",
            current_icon_path=self.config.window_icon_path or "",
            parent=self
        )
        
        if dialog.exec():
            # Update config
            new_title = dialog.get_title()
            new_icon_path = dialog.get_icon_path()
            
            self.config.window_title = new_title
            self.config.window_icon_path = new_icon_path
            self.config.save()
            
            # Update window
            self.setWindowTitle(new_title)
            self._set_window_icon()
    
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
        self.recording_panel.update_recording()

    def _on_error(self, msg):
        self.statusbar.showMessage(f"Error: {msg}", 5000)

    def _on_connection_lost(self):
        self.connect_action.setChecked(False)
        self._disconnect()
        # Only show dialog if not already shown
        if not self._connection_lost_dialog_shown:
            self._connection_lost_dialog_shown = True
            QMessageBox.warning(self, "Connection Lost", "Modbus connection lost.")
        # Connection state already updated by _disconnect()

    def _update_status(self):
        if self.data_engine.is_running:
            stats = self.data_engine.statistics
            self.poll_label.setText(f"Poll: {stats['last_poll_duration']:.1f}ms")
        else:
            self.poll_label.setText("Poll: --")

    def _on_toggle_connection_dock(self):
        """Toggle connection dock visibility via shortcut."""
        self.connection_dock.setVisible(not self.connection_dock.isVisible())

    def _add_text_panel(self, settings=None, object_name=None):
        """Add a new text panel dock."""
        panel = ViewerTextPanel()
        if settings:
            panel.set_settings(settings)
            
        dock = QDockWidget("Text Panel", self)
        # Use provided object name (for loading) or a new random one
        dock.setObjectName(object_name if object_name else f"TextPanel_{uuid.uuid4().hex[:8]}")
        dock.setWidget(panel)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._update_ui_state()

    def _add_image_panel(self, image_path=None, settings=None, object_name=None):
        """Add a new image panel dock."""
        panel = ViewerImagePanel()
        if settings:
            panel.set_settings(settings)
        elif image_path:
            panel.load_image(image_path)
            
        dock = QDockWidget("Image Panel", self)
        dock.setObjectName(object_name if object_name else f"ImagePanel_{uuid.uuid4().hex[:8]}")
        dock.setWidget(panel)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._update_ui_state()

    def _load_settings(self):
        """Load window geometry and dock layout."""
        # Recreate custom panels first so restoreState can find them
        for p_data in self.config.text_panels:
            self._add_text_panel(settings=p_data, object_name=p_data.get("object_name"))
            
        # Migrate image panel paths if needed
        migrated = False
        for p_data in self.config.image_panels:
            image_path = p_data.get("path", "")
            if image_path:
                # Check if it's an absolute path that needs migration
                if os.path.isabs(image_path) and os.path.exists(image_path):
                    # Migrate to relative path
                    relative_path = migrate_absolute_path_to_relative(image_path, "image")
                    if relative_path:
                        p_data["path"] = relative_path
                        migrated = True
                # If it's already relative or migrated, keep it
            # Check if p_data is old format (dict with just path?) or new settings dict
            # ViewerImagePanel.set_settings handles dict with defaults
            self._add_image_panel(settings=p_data, object_name=p_data.get("object_name"))
        
        # Save migrated paths
        if migrated:
            self.config.save()

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
        # Collect dynamic panels
        text_panels = []
        image_panels = []
        
        for dock in self.findChildren(QDockWidget):
            obj_name = dock.objectName()
            if obj_name.startswith("TextPanel_"):
                widget = dock.widget()
                if isinstance(widget, ViewerTextPanel):
                    data = widget.get_settings()
                    data["object_name"] = obj_name
                    text_panels.append(data)
            elif obj_name.startswith("ImagePanel_"):
                widget = dock.widget()
                if isinstance(widget, ViewerImagePanel):
                    data = widget.get_settings()
                    data["object_name"] = obj_name
                    image_panels.append(data)
                    
        self.config.text_panels = text_panels
        self.config.image_panels = image_panels

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

