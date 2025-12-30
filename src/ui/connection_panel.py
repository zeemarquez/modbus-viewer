"""
Connection settings panel widget.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QPushButton, QLabel, QGroupBox, QSlider
)
from PySide6.QtCore import Signal, Qt

from src.models.project import ConnectionSettings
from src.utils.serial_ports import get_available_ports
from src.ui.styles import COLORS


class ConnectionPanel(QFrame):
    """Panel for configuring Modbus connection settings."""
    
    connection_changed = Signal()
    poll_interval_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self._is_connected = False
        self._setup_ui()
        self._refresh_ports()
    
    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Serial settings group
        serial_group = QGroupBox("Serial Port")
        serial_layout = QFormLayout(serial_group)
        serial_layout.setSpacing(6)
        serial_layout.setContentsMargins(8, 12, 8, 8)
        serial_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.setSpacing(4)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        port_layout.addWidget(self.port_combo, 1)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setToolTip("Refresh port list")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_btn)
        
        serial_layout.addRow("Port:", port_layout)
        
        # Slave ID
        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(1, 247)
        self.slave_spin.setValue(1)
        self.slave_spin.setFixedWidth(80)
        serial_layout.addRow("Slave ID:", self.slave_spin)
        
        # Baud rate
        self.baud_combo = QComboBox()
        baud_rates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800"]
        self.baud_combo.addItems(baud_rates)
        self.baud_combo.setCurrentText("9600")
        serial_layout.addRow("Baud Rate:", self.baud_combo)
        
        # Parity
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        serial_layout.addRow("Parity:", self.parity_combo)
        
        # Stop bits
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.stopbits_combo.setFixedWidth(80)
        serial_layout.addRow("Stop Bits:", self.stopbits_combo)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 10000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setSingleStep(100)
        serial_layout.addRow("Timeout:", self.timeout_spin)
        
        layout.addWidget(serial_group)
        
        # Polling settings group
        poll_group = QGroupBox("Polling")
        poll_layout = QVBoxLayout(poll_group)
        poll_layout.setSpacing(6)
        poll_layout.setContentsMargins(8, 12, 8, 8)
        
        # Poll interval slider
        interval_label_layout = QHBoxLayout()
        interval_label_layout.addWidget(QLabel("Poll Interval:"))
        self.interval_value_label = QLabel("100 ms")
        self.interval_value_label.setStyleSheet("font-weight: 500;")
        interval_label_layout.addWidget(self.interval_value_label)
        interval_label_layout.addStretch()
        poll_layout.addLayout(interval_label_layout)
        
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(1, 2000)  # Min 1ms
        self.interval_slider.setValue(100)
        self.interval_slider.setSingleStep(5)  # 5ms increments
        self.interval_slider.setPageStep(50)
        self.interval_slider.valueChanged.connect(self._on_interval_changed)
        poll_layout.addWidget(self.interval_slider)
        
        # Interval presets
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)
        for interval in [1, 10, 50, 100, 500]:
            btn = QPushButton(f"{interval}")
            btn.setFixedWidth(44)
            btn.setProperty("interval", interval)
            btn.clicked.connect(self._on_preset_clicked)
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        poll_layout.addLayout(preset_layout)
        
        layout.addWidget(poll_group)
        
        layout.addStretch()
        
        # Connect change signals
        self.port_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.slave_spin.valueChanged.connect(self._on_settings_changed)
        self.baud_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.parity_combo.currentIndexChanged.connect(self._on_settings_changed)
        self.stopbits_combo.currentIndexChanged.connect(self._on_settings_changed)
    
    def _refresh_ports(self) -> None:
        """Refresh available COM ports."""
        current = self.port_combo.currentText()
        self.port_combo.clear()
        
        ports = get_available_ports()
        for port, description in ports:
            self.port_combo.addItem(f"{port} - {description}", port)
        
        # Restore selection if still available
        for i in range(self.port_combo.count()):
            if self.port_combo.itemData(i) == current:
                self.port_combo.setCurrentIndex(i)
                break
    
    def _on_settings_changed(self) -> None:
        """Handle settings change."""
        if not self._is_connected:
            self.connection_changed.emit()
    
    def _on_interval_changed(self, value: int) -> None:
        """Handle poll interval change."""
        self.interval_value_label.setText(f"{value} ms")
        self.poll_interval_changed.emit(value)
    
    def _on_preset_clicked(self) -> None:
        """Handle interval preset button click."""
        btn = self.sender()
        interval = btn.property("interval")
        self.interval_slider.setValue(interval)
    
    def get_settings(self) -> ConnectionSettings:
        """Get current connection settings."""
        parity_map = {"None": "N", "Even": "E", "Odd": "O"}
        
        return ConnectionSettings(
            port=self.port_combo.currentData() or "",
            slave_id=self.slave_spin.value(),
            baud_rate=int(self.baud_combo.currentText()),
            parity=parity_map.get(self.parity_combo.currentText(), "N"),
            stop_bits=int(self.stopbits_combo.currentText()),
            timeout=self.timeout_spin.value() / 1000.0,
        )
    
    def set_settings(self, settings: ConnectionSettings) -> None:
        """Set connection settings."""
        # Find and select port
        for i in range(self.port_combo.count()):
            if self.port_combo.itemData(i) == settings.port:
                self.port_combo.setCurrentIndex(i)
                break
        
        self.slave_spin.setValue(settings.slave_id)
        self.baud_combo.setCurrentText(str(settings.baud_rate))
        
        parity_map = {"N": "None", "E": "Even", "O": "Odd"}
        self.parity_combo.setCurrentText(parity_map.get(settings.parity, "None"))
        
        self.stopbits_combo.setCurrentText(str(settings.stop_bits))
        self.timeout_spin.setValue(int(settings.timeout * 1000))
    
    def set_connected(self, connected: bool) -> None:
        """Update connected state."""
        self._is_connected = connected
        
        # Disable/enable settings when connected
        self.port_combo.setEnabled(not connected)
        self.refresh_btn.setEnabled(not connected)
        self.slave_spin.setEnabled(not connected)
        self.baud_combo.setEnabled(not connected)
        self.parity_combo.setEnabled(not connected)
        self.stopbits_combo.setEnabled(not connected)
        self.timeout_spin.setEnabled(not connected)
    
    def get_poll_interval(self) -> int:
        """Get current poll interval in ms."""
        return self.interval_slider.value()
    
    def set_poll_interval(self, interval: int) -> None:
        """Set poll interval."""
        self.interval_slider.setValue(interval)
