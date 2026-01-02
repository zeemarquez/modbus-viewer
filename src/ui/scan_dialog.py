"""
Scan dialog for finding Modbus devices on a serial port.
"""

import time
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QFormLayout, QGroupBox, QMessageBox, QHeaderView, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSettings

from src.core.modbus_manager import ModbusManager
from src.utils.serial_ports import get_available_ports
from src.ui.styles import COLORS


class ScanWorker(QThread):
    """Worker thread for scanning Modbus devices."""
    
    progress = Signal(int)  # Current ID being scanned
    found = Signal(int)     # Found Slave ID
    finished = Signal(list) # Final list of found IDs
    error = Signal(str)     # Error message
    
    def __init__(
        self, 
        port: str, 
        baud_rate: int, 
        register_address: int,
        parity: str = "N",
        stop_bits: int = 1,
        timeout: float = 0.1
    ):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.register_address = register_address
        self.parity = parity
        self.stop_bits = stop_bits
        self.timeout = timeout
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        found_ids = []
        try:
            for slave_id in range(1, 248):
                if self._is_cancelled:
                    break
                
                self.progress.emit(slave_id)
                
                if ModbusManager.probe_device(
                    port=self.port,
                    slave_id=slave_id,
                    baud_rate=self.baud_rate,
                    register_address=self.register_address,
                    parity=self.parity,
                    stop_bits=self.stop_bits,
                    timeout=self.timeout
                ):
                    found_ids.append(slave_id)
                    self.found.emit(slave_id)
                
                # Small sleep to keep system responsive
                time.sleep(0.001)
                
            self.finished.emit(found_ids)
        except Exception as e:
            self.error.emit(str(e))


class ScanDialog(QDialog):
    """Dialog for scanning Modbus devices."""
    
    # Signal emitted when user wants to connect to a found device
    connect_requested = Signal(dict)
    
    def __init__(self, parent=None, initial_port: str = "", initial_baud: int = 9600):
        super().__init__(parent)
        self.setWindowTitle("Scan Modbus Devices")
        self.setMinimumWidth(400)
        
        self.worker: Optional[ScanWorker] = None
        self.found_ids: List[int] = []
        
        self._setup_ui(initial_port, initial_baud)
        
    def _setup_ui(self, initial_port: str, initial_baud: int):
        layout = QVBoxLayout(self)
        
        # Settings Group
        settings_group = QGroupBox("Scan Settings")
        form_layout = QFormLayout(settings_group)
        
        self.port_combo = QComboBox()
        ports = get_available_ports()
        for port, desc in ports:
            self.port_combo.addItem(f"{port} - {desc}", port)
        
        if initial_port:
            index = self.port_combo.findData(initial_port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        
        form_layout.addRow("Port:", self.port_combo)

        # Advanced Options Toggle
        self.advanced_toggle = QPushButton("Advanced Options ▼")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setStyleSheet("QPushButton { text-align: left; padding: 5px; border: none; color: #1976d2; font-weight: bold; }")
        self.advanced_toggle.clicked.connect(self._toggle_advanced)
        form_layout.addRow(self.advanced_toggle)

        # Advanced Settings Widget
        self.advanced_widget = QWidget()
        advanced_layout = QFormLayout(self.advanced_widget)
        advanced_layout.setContentsMargins(10, 0, 0, 0)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self.baud_combo.setCurrentText(str(initial_baud))
        
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        self.parity_combo.setCurrentText("None")
        
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.stopbits_combo.setCurrentText("1")

        self.register_spin = QSpinBox()
        self.register_spin.setRange(0, 65535)
        self.register_spin.setValue(0)
        self.register_spin.setToolTip("Register address to probe (0-65535)")
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 2000)
        self.timeout_spin.setValue(100)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setToolTip("Short timeout for faster scanning")
        
        advanced_layout.addRow("Baud Rate:", self.baud_combo)
        advanced_layout.addRow("Parity:", self.parity_combo)
        advanced_layout.addRow("Stop Bits:", self.stopbits_combo)
        advanced_layout.addRow("Target Register:", self.register_spin)
        advanced_layout.addRow("Probe Timeout:", self.timeout_spin)
        
        self.advanced_widget.setVisible(False)
        form_layout.addRow(self.advanced_widget)
        
        layout.addWidget(settings_group)
        
        # Progress Group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(1, 247)
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat("ID: %v / 247")
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to scan")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Results Group
        results_group = QGroupBox("Found Devices")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Slave ID", "Status", "Action"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(2, 100)
        self.results_table.verticalHeader().setDefaultSectionSize(36)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setMinimumHeight(200)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self._toggle_scan)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        # Load saved settings
        self._load_settings()
        
    def _toggle_scan(self):
        if self.worker and self.worker.isRunning():
            self._stop_scan()
        else:
            self._start_scan()
            
    def _toggle_advanced(self, checked: bool):
        self.advanced_widget.setVisible(checked)
        self.advanced_toggle.setText("Advanced Options ▲" if checked else "Advanced Options ▼")
        # Adjust dialog size
        self.adjustSize()

    def _load_settings(self):
        """Load scan settings from QSettings."""
        settings = QSettings()
        settings.beginGroup("ScanDialog")
        
        # Port is handled by initial_port usually, but we can override if saved
        port = settings.value("port")
        if port:
            index = self.port_combo.findData(port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
                
        baud = settings.value("baud_rate")
        if baud:
            self.baud_combo.setCurrentText(str(baud))
            
        parity = settings.value("parity")
        if parity:
            self.parity_combo.setCurrentText(parity)
            
        stop_bits = settings.value("stop_bits")
        if stop_bits:
            self.stopbits_combo.setCurrentText(str(stop_bits))
            
        reg = settings.value("register_address")
        if reg is not None:
            self.register_spin.setValue(int(reg))
            
        timeout = settings.value("timeout_ms")
        if timeout:
            self.timeout_spin.setValue(int(timeout))
            
        is_advanced = settings.value("show_advanced", "false") == "true"
        if is_advanced:
            self.advanced_toggle.setChecked(True)
            self._toggle_advanced(True)
            
        settings.endGroup()

    def _save_settings(self):
        """Save scan settings to QSettings."""
        settings = QSettings()
        settings.beginGroup("ScanDialog")
        
        settings.setValue("port", self.port_combo.currentData())
        settings.setValue("baud_rate", self.baud_combo.currentText())
        settings.setValue("parity", self.parity_combo.currentText())
        settings.setValue("stop_bits", self.stopbits_combo.currentText())
        settings.setValue("register_address", self.register_spin.value())
        settings.setValue("timeout_ms", self.timeout_spin.value())
        settings.setValue("show_advanced", "true" if self.advanced_toggle.isChecked() else "false")
        
        settings.endGroup()

    def _start_scan(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a COM port")
            return
            
        baud = int(self.baud_combo.currentText())
        parity_map = {"None": "N", "Even": "E", "Odd": "O"}
        parity = parity_map.get(self.parity_combo.currentText(), "N")
        stop_bits = int(self.stopbits_combo.currentText())
        reg = self.register_spin.value()
        timeout = self.timeout_spin.value() / 1000.0
        
        self.results_table.setRowCount(0)
        self.found_ids = []
        self.progress_bar.setValue(1)
        self.status_label.setText(f"Scanning port {port} at {baud} baud...")
        self.scan_btn.setText("Stop Scan")
        self.port_combo.setEnabled(False)
        self.advanced_toggle.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.parity_combo.setEnabled(False)
        self.stopbits_combo.setEnabled(False)
        self.register_spin.setEnabled(False)
        self.timeout_spin.setEnabled(False)
        
        # Save settings for next time
        self._save_settings()
        
        self.worker = ScanWorker(
            port=port,
            baud_rate=baud,
            register_address=reg,
            parity=parity,
            stop_bits=stop_bits,
            timeout=timeout
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.found.connect(self._on_found)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
        
    def _stop_scan(self):
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Stopping...")
            self.scan_btn.setEnabled(False)
            
    def _on_progress(self, slave_id: int):
        self.progress_bar.setValue(slave_id)
        
    def _on_found(self, slave_id: int):
        self.found_ids.append(slave_id)
        
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # ID item
        id_item = QTableWidgetItem(str(slave_id))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setForeground(Qt.GlobalColor.darkGreen)
        
        # Status item
        status_item = QTableWidgetItem("Responded")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setForeground(Qt.GlobalColor.darkGreen)
        
        self.results_table.setItem(row, 0, id_item)
        self.results_table.setItem(row, 1, status_item)
        
        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(lambda: self._request_connect(slave_id))
        self.results_table.setCellWidget(row, 2, connect_btn)

    def _request_connect(self, slave_id: int):
        """Emit signal and close dialog."""
        settings = {
            "port": self.port_combo.currentData(),
            "slave_id": slave_id,
            "baud_rate": int(self.baud_combo.currentText()),
            "parity": self.parity_combo.currentText(),
            "stop_bits": int(self.stopbits_combo.currentText()),
            "timeout": 1.0, # Default full timeout for actual connection
        }
        self.connect_requested.emit(settings)
        self.accept()
        
    def _on_finished(self, found_ids: list):
        self.scan_btn.setText("Start Scan")
        self.scan_btn.setEnabled(True)
        self.port_combo.setEnabled(True)
        self.advanced_toggle.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.parity_combo.setEnabled(True)
        self.stopbits_combo.setEnabled(True)
        self.register_spin.setEnabled(True)
        self.timeout_spin.setEnabled(True)
        
        if not found_ids:
            self.status_label.setText("Scan complete. No devices found.")
        else:
            self.status_label.setText(f"Scan complete. Found {len(found_ids)} device(s).")
            
    def _on_error(self, message: str):
        QMessageBox.critical(self, "Scan Error", f"An error occurred during scan:\n{message}")
        self._on_finished([])

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()

