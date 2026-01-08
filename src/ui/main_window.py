"""
Main application window with multi-device support.
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QMenuBar, QMenu, QDockWidget,
    QFileDialog, QMessageBox, QLabel, QApplication,
    QComboBox, QSpinBox, QToolButton, QWidgetAction,
    QFormLayout
)
from PySide6.QtCore import Qt, QSettings, QTimer, QByteArray, Signal
from PySide6.QtGui import QAction, QKeySequence, QIcon

from src.models.project import Project, ConnectionSettings
from src.core.modbus_manager import ModbusManager
from src.core.data_engine import DataEngine
from src.utils.serial_ports import get_available_ports
from src.ui.table_view import TableView
from src.ui.plot_view import PlotView
from src.ui.variables_panel import VariablesPanel
from src.ui.bits_panel import BitsPanel
from src.ui.speed_test_panel import SpeedTestPanel
from src.ui.register_editor import RegisterEditorDialog
from src.ui.scan_dialog import ScanDialog
from src.ui.styles import COLORS


class MainWindow(QMainWindow):
    """Main application window with dockable panels and multi-device support."""
    
    def __init__(self, initial_project_path: str = None):
        super().__init__()
        
        # Initialize components
        self.project = Project()
        self.modbus = ModbusManager()
        self.data_engine = DataEngine()
        self.data_engine.modbus = self.modbus
        
        # Track found devices from scan
        self._found_devices: list = []
        self._connected_slave_ids: list = []
        
        # Setup UI
        self.setWindowTitle("Modbus Explorer")
        self.setMinimumSize(1200, 700)
        
        # Explicitly set window icon (helps on some Windows versions)
        self._set_window_icon()
        
        # Set empty central widget (required by QMainWindow)
        central = QWidget()
        central.setMaximumSize(0, 0)
        self.setCentralWidget(central)
        
        # Allow nested docks and animated docking
        self.setDockNestingEnabled(True)
        
        self._setup_menu()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_dock_widgets()
        self._setup_connections()
        
        # Restore window state
        self._load_settings()
        
        # Refresh ports initially
        self._refresh_ports()
        
        # Load initial project if specified
        if initial_project_path:
            self._load_project_from_path(initial_project_path)
        
        # Status update timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(500)
    
    def _set_window_icon(self) -> None:
        """Set window icon from assets."""
        icon_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.ico"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.png"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icon.ico"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icon.png"),
        ]
        for path in icon_paths:
            if os.path.exists(path):
                self.setWindowIcon(QIcon(path))
                break

    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        register_action = QAction("&Registers...", self)
        register_action.setShortcut(QKeySequence("Ctrl+R"))
        register_action.triggered.connect(self._edit_registers)
        edit_menu.addAction(register_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        self._view_menu = view_menu  # Store for dock widget actions
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self) -> None:
        """Setup main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Port Selection
        toolbar.addWidget(QLabel(" Port: "))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        toolbar.addWidget(self.port_combo)
        
        self.refresh_ports_action = QAction("↻", self)
        self.refresh_ports_action.setToolTip("Refresh COM ports")
        self.refresh_ports_action.triggered.connect(self._refresh_ports)
        toolbar.addAction(self.refresh_ports_action)
        
        self.scan_action = QAction("Scan", self)
        self.scan_action.setToolTip("Scan for Modbus devices")
        self.scan_action.triggered.connect(self._open_scan_dialog)
        toolbar.addAction(self.scan_action)
        
        toolbar.addSeparator()
        
        # Device Selection (multi-select dropdown)
        self.device_btn = QToolButton()
        self.device_btn.setText("Select Devices")
        self.device_btn.setMinimumWidth(150)
        self.device_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.device_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        self.device_btn.setToolTip("Select devices to connect to (multi-select)")
        
        self.device_menu = QMenu(self)
        self.device_menu.aboutToHide.connect(self._on_device_menu_about_to_hide)
        self.device_btn.setMenu(self.device_menu)
        toolbar.addWidget(self.device_btn)
        
        toolbar.addSeparator()
        
        # Advanced Menu
        self.advanced_btn = QToolButton()
        self.advanced_btn.setText("Advanced")
        self.advanced_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.advanced_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        
        advanced_menu = QMenu(self)
        
        # Baud Rate
        baud_widget = QWidget()
        baud_layout = QHBoxLayout(baud_widget)
        baud_layout.setContentsMargins(10, 5, 10, 5)
        baud_layout.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self.baud_combo.setCurrentText("9600")
        baud_layout.addWidget(self.baud_combo)
        
        baud_action = QWidgetAction(self)
        baud_action.setDefaultWidget(baud_widget)
        advanced_menu.addAction(baud_action)
        
        # Parity
        parity_widget = QWidget()
        parity_layout = QHBoxLayout(parity_widget)
        parity_layout.setContentsMargins(10, 5, 10, 5)
        parity_layout.addWidget(QLabel("Parity:"))
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        parity_layout.addWidget(self.parity_combo)
        
        parity_action = QWidgetAction(self)
        parity_action.setDefaultWidget(parity_widget)
        advanced_menu.addAction(parity_action)
        
        # Stop Bits
        stop_widget = QWidget()
        stop_layout = QHBoxLayout(stop_widget)
        stop_layout.setContentsMargins(10, 5, 10, 5)
        stop_layout.addWidget(QLabel("Stop Bits:"))
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        stop_layout.addWidget(self.stopbits_combo)
        
        stop_action = QWidgetAction(self)
        stop_action.setDefaultWidget(stop_widget)
        advanced_menu.addAction(stop_action)
        
        # Timeout
        timeout_widget = QWidget()
        timeout_layout = QHBoxLayout(timeout_widget)
        timeout_layout.setContentsMargins(10, 5, 10, 5)
        timeout_layout.addWidget(QLabel("Timeout (ms):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 10000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSingleStep(100)
        timeout_layout.addWidget(self.timeout_spin)
        
        timeout_action = QWidgetAction(self)
        timeout_action.setDefaultWidget(timeout_widget)
        advanced_menu.addAction(timeout_action)
        
        advanced_menu.addSeparator()
        
        # Polling Interval
        poll_widget = QWidget()
        poll_layout = QHBoxLayout(poll_widget)
        poll_layout.setContentsMargins(10, 5, 10, 5)
        poll_layout.addWidget(QLabel("Poll Interval (ms):"))
        self.poll_combo = QComboBox()
        self.poll_combo.addItems(["1", "10", "50", "100", "200", "500", "1000", "2000"])
        self.poll_combo.setCurrentText("100")
        self.poll_combo.currentTextChanged.connect(self._on_poll_interval_text_changed)
        poll_layout.addWidget(self.poll_combo)
        
        poll_action = QWidgetAction(self)
        poll_action.setDefaultWidget(poll_widget)
        advanced_menu.addAction(poll_action)
        
        self.advanced_btn.setMenu(advanced_menu)
        toolbar.addWidget(self.advanced_btn)

        toolbar.addSeparator()
        
        # Connect button
        self.connect_action = QAction("Connect", self)
        self.connect_action.setCheckable(True)
        self.connect_action.triggered.connect(self._toggle_connection)
        toolbar.addAction(self.connect_action)

    def _refresh_ports(self) -> None:
        """Refresh available COM ports."""
        current = self.port_combo.currentData()
        self.port_combo.clear()
        
        ports = get_available_ports()
        for port, description in ports:
            self.port_combo.addItem(f"{port} - {description}", port)
        
        # Restore selection if still available
        if current:
            index = self.port_combo.findData(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def _update_device_menu(self) -> None:
        """Update the device selection menu with found devices."""
        self.device_menu.clear()
        
        if not self._found_devices:
            self.device_btn.setText("Run Scan")
            no_devices_action = QAction("No devices found - run scan first", self)
            no_devices_action.setEnabled(False)
            self.device_menu.addAction(no_devices_action)
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
        for slave_id in sorted(self._found_devices):
            action = QAction(f"Device {slave_id}", self)
            action.setCheckable(True)
            action.setChecked(slave_id in self._connected_slave_ids)
            action.setData(slave_id)
            action.triggered.connect(lambda checked, sid=slave_id: self._on_device_toggled(sid, checked))
            self.device_menu.addAction(action)
        
        self._update_device_btn_text()
    
    def _update_device_btn_text(self) -> None:
        """Update the device button text based on selection."""
        selected = self._get_selected_slave_ids()
        if not selected:
            if self._found_devices:
                self.device_btn.setText("Select Devices")
            else:
                self.device_btn.setText("Run Scan")
        elif len(selected) == 1:
            self.device_btn.setText(f"Device {selected[0]}")
        else:
            self.device_btn.setText(f"{len(selected)} Devices")
    
    def _get_selected_slave_ids(self) -> list:
        """Get the list of selected slave IDs from the menu."""
        selected = []
        for action in self.device_menu.actions():
            if action.isCheckable() and action.isChecked():
                slave_id = action.data()
                if slave_id is not None:
                    selected.append(slave_id)
        return sorted(selected)
    
    def _on_device_toggled(self, slave_id: int, checked: bool) -> None:
        """Handle device selection toggle."""
        if checked:
            if slave_id not in self._connected_slave_ids:
                self._connected_slave_ids.append(slave_id)
        else:
            if slave_id in self._connected_slave_ids:
                self._connected_slave_ids.remove(slave_id)
        self._connected_slave_ids.sort()
        self._update_device_btn_text()
    
    def _select_all_devices(self) -> None:
        """Select all devices."""
        self._connected_slave_ids = self._found_devices.copy()
        for action in self.device_menu.actions():
            if action.isCheckable():
                action.setChecked(True)
        self._update_device_btn_text()
    
    def _deselect_all_devices(self) -> None:
        """Deselect all devices."""
        self._connected_slave_ids = []
        for action in self.device_menu.actions():
            if action.isCheckable():
                action.setChecked(False)
        self._update_device_btn_text()
    
    def _on_device_menu_about_to_hide(self) -> None:
        """Called when device menu is about to hide - sync selected devices."""
        self._connected_slave_ids = self._get_selected_slave_ids()

    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Connection status
        self.connection_label = QLabel("🔴 Disconnected")
        self.connection_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 500;")
        self.statusbar.addWidget(self.connection_label)
        
        # Spacer
        spacer = QWidget()
        spacer.setFixedWidth(20)
        self.statusbar.addWidget(spacer)
        
        # Poll rate
        self.poll_label = QLabel("Poll: --")
        self.statusbar.addWidget(self.poll_label)
        
        # Actual poll duration
        self.poll_duration_label = QLabel("Actual: --")
        self.statusbar.addWidget(self.poll_duration_label)
        
        # Register count
        self.register_label = QLabel("Registers: 0")
        self.statusbar.addPermanentWidget(self.register_label)
    
    def _setup_dock_widgets(self) -> None:
        """Setup dockable panels."""
        # Registers table dock (center-top)
        self.registers_dock = QDockWidget("Registers", self)
        self.registers_dock.setObjectName("RegistersDock")
        self.registers_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.registers_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.table_view = TableView()
        self.registers_dock.setWidget(self.table_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.registers_dock)
        
        # Variables panel dock (tabbed with Registers)
        self.variables_dock = QDockWidget("Variables", self)
        self.variables_dock.setObjectName("VariablesDock")
        self.variables_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.variables_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.variables_panel = VariablesPanel()
        self.variables_dock.setWidget(self.variables_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.variables_dock)
        
        # Bits panel dock (tabbed with Registers and Variables)
        self.bits_dock = QDockWidget("Bits", self)
        self.bits_dock.setObjectName("BitsDock")
        self.bits_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.bits_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.bits_panel = BitsPanel()
        self.bits_dock.setWidget(self.bits_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bits_dock)
        
        # Speed Test panel dock
        self.speed_test_dock = QDockWidget("Speed Test", self)
        self.speed_test_dock.setObjectName("SpeedTestDock")
        self.speed_test_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.speed_test_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.speed_test_panel = SpeedTestPanel(self.modbus, self.data_engine)
        self.speed_test_dock.setWidget(self.speed_test_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.speed_test_dock)
        
        # Tab Variables, Bits and Speed Test with Registers
        self.tabifyDockWidget(self.registers_dock, self.variables_dock)
        self.tabifyDockWidget(self.variables_dock, self.bits_dock)
        self.tabifyDockWidget(self.bits_dock, self.speed_test_dock)
        # Make Registers the active tab
        self.registers_dock.raise_()
        
        # Plot dock (center-bottom)
        self.plot_dock = QDockWidget("Plot", self)
        self.plot_dock.setObjectName("PlotDock")
        self.plot_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.plot_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.plot_view = PlotView()
        self.plot_dock.setWidget(self.plot_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_dock)
        
        # Stack plot below registers/variables
        self.splitDockWidget(self.registers_dock, self.plot_dock, Qt.Orientation.Vertical)
        
        # Add all docks to view menu
        self._view_menu.addAction(self.registers_dock.toggleViewAction())
        self._view_menu.addAction(self.variables_dock.toggleViewAction())
        self._view_menu.addAction(self.bits_dock.toggleViewAction())
        self._view_menu.addAction(self.speed_test_dock.toggleViewAction())
        self._view_menu.addAction(self.plot_dock.toggleViewAction())
        
        self._view_menu.addSeparator()
        
        # Reset layout action
        reset_action = QAction("Reset Layout", self)
        reset_action.triggered.connect(self._reset_layout)
        self._view_menu.addAction(reset_action)
    
    def _reset_layout(self) -> None:
        """Reset dock layout to default."""
        # Show all docks
        self.registers_dock.show()
        self.variables_dock.show()
        self.bits_dock.show()
        self.speed_test_dock.show()
        self.plot_dock.show()
        
        # Float none
        self.registers_dock.setFloating(False)
        self.variables_dock.setFloating(False)
        self.bits_dock.setFloating(False)
        self.speed_test_dock.setFloating(False)
        self.plot_dock.setFloating(False)
        
        # Reset positions
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.registers_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.variables_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bits_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.speed_test_dock)
        self.tabifyDockWidget(self.registers_dock, self.variables_dock)
        self.tabifyDockWidget(self.variables_dock, self.bits_dock)
        self.tabifyDockWidget(self.bits_dock, self.speed_test_dock)
        self.registers_dock.raise_()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_dock)
        self.splitDockWidget(self.registers_dock, self.plot_dock, Qt.Orientation.Vertical)
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        # Data engine
        self.data_engine.data_updated.connect(self._on_data_updated)
        self.data_engine.error_occurred.connect(self._on_error)
        self.data_engine.connection_lost.connect(self._on_connection_lost)
        
        # Table view
        self.table_view.write_requested.connect(self._on_write_requested)
        self.table_view.edit_registers_requested.connect(self._edit_registers)
        
        # Variables panel
        self.variables_panel.variables_changed.connect(self._on_variables_changed)
        
        # Bits panel
        self.bits_panel.bits_changed.connect(self._on_bits_changed)
        self.bits_panel.bit_value_changed.connect(self._on_bit_value_changed)
        
        # Plot view
        self.plot_view.maximize_requested.connect(self._on_plot_maximize_requested)
    
    def _on_plot_maximize_requested(self) -> None:
        """Maximize plot as independent window."""
        self.plot_dock.setFloating(True)
        self.plot_dock.showMaximized()
        self.plot_dock.raise_()
    
    def _load_settings(self) -> None:
        """Load window settings (geometry only, layout comes from project)."""
        settings = QSettings()
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state from settings as fallback (when no project loaded)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def _save_settings(self) -> None:
        """Save window settings."""
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        # Save table view settings
        self.table_view.save_settings()
        self.variables_panel.save_settings()
        self.bits_panel.save_settings()
        
        # Also save layout state to project (convert QByteArray to bytes)
        self.project.layout_state = bytes(self.saveState().data())
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        self._save_settings()
        self.data_engine.stop()
        self.modbus.disconnect()
        event.accept()
    
    # Actions
    
    def _new_project(self) -> None:
        """Create new project."""
        self.data_engine.stop()
        self.project = Project()
        self._found_devices = []
        self._connected_slave_ids = []
        self._update_device_menu()
        self._update_ui_from_project()
        self.setWindowTitle("Modbus Explorer - Untitled")
    
    def _open_project(self) -> None:
        """Open project file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Modbus Project (*.json);;All Files (*)"
        )
        
        if file_path:
            self._load_project_from_path(file_path)
    
    def _load_project_from_path(self, file_path: str) -> bool:
        """Load a project from the given file path."""
        try:
            self.data_engine.stop()
            self.project = Project.load(file_path)
            
            self._update_ui_from_project()
            self.setWindowTitle(f"Modbus Explorer - {self.project.name}")
            
            # Save as last opened project
            settings = QSettings()
            settings.setValue("lastProjectPath", file_path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{e}")
            return False
    
    def _save_project(self) -> None:
        """Save current project."""
        if self.project.file_path:
            self._do_save()
        else:
            self._save_project_as()
    
    def _save_project_as(self) -> None:
        """Save project to new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "Modbus Project (*.json)"
        )
        
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            self.project.file_path = file_path
            self._do_save()
            self.setWindowTitle(f"Modbus Explorer - {self.project.name}")
    
    def _do_save(self) -> None:
        """Actually save the project."""
        try:
            # Update project from UI
            self._update_project_from_ui()
            # Save layout state before saving project (convert QByteArray to bytes)
            self.project.layout_state = bytes(self.saveState().data())
            self.project.save()
            
            # Save as last opened project
            settings = QSettings()
            settings.setValue("lastProjectPath", self.project.file_path)
            
            self.statusbar.showMessage("Project saved", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{e}")
    
    def _edit_registers(self) -> None:
        """Open register editor dialog."""
        dialog = RegisterEditorDialog(self.project.registers, self)
        if dialog.exec():
            self.project.registers = dialog.get_registers()
            self._sync_registers()
            self._update_register_count()
    
    def _sync_registers(self) -> None:
        """Sync registers to all components by creating live instances per device."""
        slave_ids = self._connected_slave_ids if self._connected_slave_ids else [1]
        
        # 1. Update Table View and Bits Panel definitions first
        self.table_view.set_registers(self.project.registers)
        self.table_view.set_slave_ids(slave_ids)
        
        self.bits_panel.set_registers(self.project.registers)
        
        # 2. Get live instances that were just created
        live_registers = self.table_view.get_live_registers()
        
        # 3. Propagate live instances to other components
        self.data_engine.set_registers(live_registers)
        self.plot_view.set_registers(live_registers)
        
        # Variables panel needs definitions and slave IDs
        self.variables_panel.set_registers(live_registers)
        self.variables_panel.set_variables(self.project.variables)
        self.variables_panel.set_slave_ids(slave_ids)
        
        # Bits panel needs live registers for value lookup
        self.bits_panel.set_slave_ids(slave_ids, live_registers)
        
        self.speed_test_panel.set_registers(live_registers)
    
    def _sync_variables(self) -> None:
        """Sync variables to all components using live instances from panel."""
        live_variables = self.variables_panel.get_live_variables()
        self.data_engine.set_variables(live_variables)
        self.plot_view.set_variables(live_variables)
    
    def _sync_bits(self) -> None:
        """Sync bits to all components."""
        self.bits_panel.set_bits(self.project.bits)
    
    def _toggle_connection(self, checked: bool) -> None:
        """Toggle Modbus connection."""
        if checked:
            self._connect()
        else:
            self._disconnect()
    
    def _get_connection_settings(self) -> ConnectionSettings:
        """Get current connection settings from toolbar."""
        parity_map = {"None": "N", "Even": "E", "Odd": "O"}
        
        # Get selected slave IDs from menu (sync first)
        self._connected_slave_ids = self._get_selected_slave_ids()
        slave_ids = self._connected_slave_ids if self._connected_slave_ids else []
        
        return ConnectionSettings(
            port=self.port_combo.currentData() or "",
            slave_ids=slave_ids,
            baud_rate=int(self.baud_combo.currentText()),
            parity=parity_map.get(self.parity_combo.currentText(), "N"),
            stop_bits=int(self.stopbits_combo.currentText()),
            timeout=self.timeout_spin.value() / 1000.0,
            found_devices=self._found_devices.copy(),
        )

    def _connect(self) -> None:
        """Connect to Modbus devices."""
        settings = self._get_connection_settings()
        
        if not settings.port:
            QMessageBox.warning(self, "Warning", "Please select a COM port")
            self.connect_action.setChecked(False)
            return
        
        if not settings.slave_ids:
            QMessageBox.warning(self, "Warning", "Please scan for devices first or configure slave IDs")
            self.connect_action.setChecked(False)
            return
        
        try:
            self.modbus.connect(
                port=settings.port,
                slave_ids=settings.slave_ids,
                baud_rate=settings.baud_rate,
                parity=settings.parity,
                stop_bits=settings.stop_bits,
                timeout=settings.timeout,
            )
            
            self.project.connection = settings
            device_str = ", ".join(str(s) for s in settings.slave_ids)
            self.connection_label.setText(f"🟢 Connected: {settings.port} (D{device_str})")
            self.connection_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: 500;")
            self.speed_test_panel.set_connected(True)
            self.connect_action.setText("Disconnect")
            
            # Update device combo to show connected status
            self._update_device_menu()
            
            # Disable settings while connected
            self._set_connection_widgets_enabled(False)
            
            # Start polling automatically
            self._sync_registers()
            self._sync_variables()
            self.data_engine.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connect_action.setChecked(False)
    
    def _disconnect(self) -> None:
        """Disconnect from Modbus devices."""
        self.data_engine.stop()
        self.modbus.disconnect()
        # Keep the device selection so user can easily reconnect
        self.connection_label.setText("🔴 Disconnected")
        self.connection_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 500;")
        self.speed_test_panel.set_connected(False)
        self.connect_action.setText("Connect")
        
        # Re-enable settings
        self._set_connection_widgets_enabled(True)

    def _set_connection_widgets_enabled(self, enabled: bool) -> None:
        """Enable/disable connection settings widgets."""
        self.port_combo.setEnabled(enabled)
        self.refresh_ports_action.setEnabled(enabled)
        self.device_btn.setEnabled(enabled)
        self.baud_combo.setEnabled(enabled)
        self.parity_combo.setEnabled(enabled)
        self.stopbits_combo.setEnabled(enabled)
        self.timeout_spin.setEnabled(enabled)

    def _on_poll_interval_text_changed(self, text: str) -> None:
        """Handle poll interval change from dropdown."""
        try:
            interval = int(text)
            self.data_engine.set_poll_interval(interval)
            self.project.views.poll_interval = interval
        except ValueError:
            pass
    
    def _open_scan_dialog(self) -> None:
        """Open the Modbus device scan dialog."""
        # Clear previous scan results
        self._found_devices = []
        self._connected_slave_ids = []
        self._update_device_menu()
        
        # If already connected, disconnect first to free the serial port for scanning
        if self.modbus.is_connected:
            self.connect_action.setChecked(False)
            self._disconnect()
            
        dialog = ScanDialog(
            parent=self,
            initial_port=self.port_combo.currentData() or "",
            initial_baud=int(self.baud_combo.currentText())
        )
        # Pre-set parity and stop bits from main window
        dialog.parity_combo.setCurrentText(self.parity_combo.currentText())
        dialog.stopbits_combo.setCurrentText(self.stopbits_combo.currentText())
        
        dialog.connect_requested.connect(self._on_scan_connect_requested)
        dialog.devices_found.connect(self._on_devices_found)
        dialog.exec()

    def _on_devices_found(self, found_ids: list) -> None:
        """Handle devices found from scan."""
        self._found_devices = found_ids.copy()
        self._connected_slave_ids = found_ids.copy()  # Select all by default
        self.project.connection.found_devices = found_ids.copy()
        self._update_device_menu()

    def _on_scan_connect_requested(self, settings: dict) -> None:
        """Handle connection request from scan dialog."""
        # Update UI with scanned settings
        index = self.port_combo.findData(settings["port"])
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        
        # Store found devices and selected slave IDs
        self._found_devices = settings.get("found_devices", settings.get("slave_ids", []))
        self._connected_slave_ids = settings.get("slave_ids", [])
        
        self.baud_combo.setCurrentText(str(settings["baud_rate"]))
        self.parity_combo.setCurrentText(settings["parity"])
        self.stopbits_combo.setCurrentText(str(settings["stop_bits"]))
        
        self._update_device_menu()
        
        # Trigger actual connection
        self.connect_action.setChecked(True)
        self._connect()
    
    def _clear_data(self) -> None:
        """Clear all data history."""
        self.data_engine.clear_history()
        self.plot_view.clear()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        # Try to find icon for about dialog
        icon_path = ""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.png"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icon.png"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                icon_path = p
                break

        about_text = (
            "<h2>Modbus Explorer</h2>"
            "<p>A modern GUI for Modbus RTU communication.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Multi-device support (connect to multiple slaves)</li>"
            "<li>Real-time register monitoring</li>"
            "<li>Computed variables with expressions</li>"
            "<li>Live plotting</li>"
            "<li>Read and write support</li>"
            "</ul>"
        )
        
        if icon_path:
            # Add icon to about dialog if it exists
            about_text = f"<table><tr><td><img src='{icon_path}' width='64'></td><td style='padding-left: 20px;'>{about_text}</td></tr></table>"

        QMessageBox.about(self, "About Modbus Explorer", about_text)
    
    # Event handlers
    
    def _on_data_updated(self) -> None:
        """Handle data update from engine."""
        self.table_view.update_values()
        self.plot_view.update_plot(self.data_engine)
        self.variables_panel.update_values()
        self.bits_panel.update_values()
    
    def _on_error(self, message: str) -> None:
        """Handle error from engine."""
        self.statusbar.showMessage(f"Error: {message}", 5000)
    
    def _on_connection_lost(self) -> None:
        """Handle lost connection."""
        self.connect_action.setChecked(False)
        self.connect_action.setText("Connect")
        # Keep device selection so user can easily reconnect
        self.speed_test_panel.set_connected(False)
        self._disconnect()
        QMessageBox.warning(self, "Connection Lost", "Connection to Modbus device was lost.")
    
    def _on_write_requested(self, register, value) -> None:
        """Handle write request from table."""
        success = self.data_engine.write_register(register, value)
        if success:
            self.statusbar.showMessage(f"Wrote {value} to {register.designator}", 3000)
            # Clear bits panel pending values for this register
            self.bits_panel.clear_pending(register.slave_id, register.address)
    
    def _on_variables_changed(self) -> None:
        """Handle variables change from panel."""
        self.project.variables = self.variables_panel.get_variables()
        self._sync_variables()
    
    def _on_bits_changed(self) -> None:
        """Handle bits change from panel."""
        self.project.bits = self.bits_panel.get_bits()
    
    def _on_bit_value_changed(self, slave_id: int, address: int, new_value: int) -> None:
        """Handle bit value change - update the register's new value field."""
        self.table_view.set_register_new_value(slave_id, address, new_value)
    
    def _update_status(self) -> None:
        """Update status bar."""
        if self.data_engine.is_running:
            stats = self.data_engine.statistics
            self.poll_label.setText(f"Poll: {stats['poll_interval']}ms")
            duration = stats['last_poll_duration']
            self.poll_duration_label.setText(f"Actual: {duration:.1f}ms")
        else:
            self.poll_label.setText("Poll: --")
            self.poll_duration_label.setText("Actual: --")
    
    def _update_register_count(self) -> None:
        """Update register count in status bar."""
        count = len(self.project.registers)
        devices = len(set(r.slave_id for r in self.project.registers))
        self.register_label.setText(f"Registers: {count} ({devices} devices)")
    
    def _update_ui_from_project(self) -> None:
        """Update UI from project data."""
        # Update toolbar settings
        settings = self.project.connection
        index = self.port_combo.findData(settings.port)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        
        # Update found devices from project
        self._found_devices = settings.found_devices.copy()
        self._connected_slave_ids = self._found_devices.copy()  # Select all by default
        self._update_device_menu()
        
        self.baud_combo.setCurrentText(str(settings.baud_rate))
        
        parity_map = {"N": "None", "E": "Even", "O": "Odd"}
        self.parity_combo.setCurrentText(parity_map.get(settings.parity, "None"))
        
        self.stopbits_combo.setCurrentText(str(settings.stop_bits))
        self.timeout_spin.setValue(int(settings.timeout * 1000))
        
        # Poll interval
        self.poll_combo.setCurrentText(str(self.project.views.poll_interval))
        self.data_engine.set_poll_interval(self.project.views.poll_interval)
        
        self._sync_registers()
        self._sync_variables()
        self._sync_bits()
        self.plot_view.set_selected_registers(self.project.views.plot_registers)
        self.plot_view.set_selected_variables(self.project.views.plot_variables)
        self.plot_view.set_plot_options(self.project.views.plot_options)
        self._update_register_count()
        
        # Restore layout state from project if available
        if self.project.layout_state:
            # Convert bytes to QByteArray for restoreState
            self.restoreState(QByteArray(self.project.layout_state))
    
    def _update_project_from_ui(self) -> None:
        """Update project from UI state."""
        self.project.connection = self._get_connection_settings()
        self.project.views.poll_interval = self.data_engine.poll_interval
        self.project.views.plot_registers = self.plot_view.get_selected_registers()
        self.project.views.plot_variables = self.plot_view.get_selected_variables()
        self.project.views.plot_options = self.plot_view.get_plot_options()
        self.project.variables = self.variables_panel.get_variables()
        self.project.bits = self.bits_panel.get_bits()
