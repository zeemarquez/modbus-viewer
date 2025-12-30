"""
Speed test panel for measuring Modbus read performance.
"""

import time
from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpinBox, QLabel, QGroupBox, QScrollArea, QCheckBox,
    QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread, Slot

from src.models.register import Register
from src.core.modbus_manager import ModbusManager
from src.core.data_engine import DataEngine
from src.ui.styles import COLORS


class SpeedTestWorker(QThread):
    """Worker thread for running the speed test."""
    
    finished = Signal(dict)
    progress = Signal(int)
    error = Signal(str)
    
    def __init__(self, modbus: ModbusManager, registers: List[Register], num_samples: int):
        super().__init__()
        self.modbus = modbus
        self.registers = registers
        self.num_samples = num_samples
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        
    def run(self):
        if not self.modbus.is_connected:
            self.error.emit("Modbus not connected")
            return
            
        if not self.registers:
            self.error.emit("No registers selected")
            return

        try:
            # We use the instrument directly to bypass any high-level logic and get max speed
            instrument = self.modbus.instrument
            
            start_time = time.time()
            total_reads = 0
            total_registers = 0
            
            for i in range(self.num_samples):
                if not self._is_running:
                    break
                    
                for reg in self.registers:
                    if not self._is_running:
                        break
                    
                    if reg.size == 1:
                        instrument.read_register(reg.address, 0)
                    else:
                        instrument.read_registers(reg.address, reg.size)
                        
                    total_reads += 1
                    total_registers += reg.size
                
                self.progress.emit(int((i + 1) / self.num_samples * 100))
                
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 0:
                results = {
                    'duration': duration,
                    'total_reads': total_reads,
                    'total_registers': total_registers,
                    'reads_per_second': total_reads / duration,
                    'registers_per_second': total_registers / duration,
                    'sampling_frequency': (self.num_samples) / duration
                }
                self.finished.emit(results)
            else:
                self.error.emit("Test duration too short")
                
        except Exception as e:
            self.error.emit(str(e))


class SpeedTestPanel(QWidget):
    """Panel for testing Modbus read speed."""
    
    def __init__(self, modbus: ModbusManager, data_engine: DataEngine, parent=None):
        super().__init__(parent)
        self.modbus = modbus
        self.data_engine = data_engine
        self.registers: List[Register] = []
        self._register_checkboxes: Dict[int, QCheckBox] = {}
        self.worker: SpeedTestWorker = None
        self._was_polling = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Register selection group
        reg_group = QGroupBox("Available Registers")
        reg_layout = QVBoxLayout(reg_group)
        
        # Scroll area for registers
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        
        reg_layout.addWidget(self.scroll)
        
        # Select All/None buttons
        btn_layout = QHBoxLayout()
        all_btn = QPushButton("All")
        all_btn.clicked.connect(self._select_all)
        none_btn = QPushButton("None")
        none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(all_btn)
        btn_layout.addWidget(none_btn)
        reg_layout.addLayout(btn_layout)
        
        layout.addWidget(reg_group, stretch=1)
        
        # Settings group
        settings_group = QGroupBox("Test Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Samples:"))
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(1, 10000)
        self.samples_spin.setValue(100)
        settings_layout.addWidget(self.samples_spin)
        
        layout.addWidget(settings_group)
        
        # Start button
        self.start_btn = QPushButton("Start Test")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(f"font-weight: bold; background-color: {COLORS['accent']}; color: white;")
        self.start_btn.clicked.connect(self._toggle_test)
        layout.addWidget(self.start_btn)
        
        # Results group
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout(results_group)
        results_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.setSpacing(5)
        
        # Tooltip for the results group
        results_group.setToolTip(
            "Frequency calculation:\n"
            "Frequency = 1 / (Total Time / Number of Samples)\n\n"
            "This represents how many times per second the entire set of\n"
            "selected registers can be read at maximum speed."
        )
        
        freq_title = QLabel("Sampling Frequency")
        freq_title.setObjectName("subheading")
        freq_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(freq_title)
        
        self.freq_value_label = QLabel("-- Hz")
        self.freq_value_label.setObjectName("heading")
        self.freq_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.freq_value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['accent']}; margin: 10px 0;")
        results_layout.addWidget(self.freq_value_label)
        
        self.status_label = QLabel("Select registers and press Start")
        self.status_label.setObjectName("subheading")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self.status_label)
        
        layout.addWidget(results_group)
        
    def set_registers(self, registers: List[Register]):
        """Update available registers."""
        self.registers = registers
        
        # Clear existing checkboxes
        for cb in self._register_checkboxes.values():
            cb.deleteLater()
        self._register_checkboxes.clear()
        
        # Add new checkboxes
        for reg in registers:
            cb = QCheckBox(reg.label or f"R{reg.address}")
            self.scroll_layout.addWidget(cb)
            self._register_checkboxes[reg.address] = cb
            
    def _select_all(self):
        for cb in self._register_checkboxes.values():
            cb.setChecked(True)
            
    def _select_none(self):
        for cb in self._register_checkboxes.values():
            cb.setChecked(False)
            
    def _toggle_test(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.start_btn.setText("Stopping...")
            self.start_btn.setEnabled(False)
            return
            
        selected_addresses = [addr for addr, cb in self._register_checkboxes.items() if cb.isChecked()]
        selected_registers = [reg for reg in self.registers if reg.address in selected_addresses]
        
        if not selected_registers:
            self.status_label.setText("Error: No registers selected")
            self.status_label.setStyleSheet(f"color: {COLORS['error']};")
            return

        # Stop polling if active
        self._was_polling = self.data_engine.is_running
        if self._was_polling:
            self.data_engine.stop()
            
        self.start_btn.setText("Stop Test")
        self.freq_value_label.setText("Testing...")
        self.status_label.setText("Reading registers at max speed...")
        self.status_label.setStyleSheet("")
        
        self.worker = SpeedTestWorker(
            self.modbus,
            selected_registers,
            self.samples_spin.value()
        )
        self.worker.finished.connect(self._on_test_finished)
        self.worker.error.connect(self._on_test_error)
        self.worker.start()
        
    @Slot(dict)
    def _on_test_finished(self, results: dict):
        self.freq_value_label.setText(f"{results['sampling_frequency']:.2f} Hz")
        self.status_label.setText(f"Completed {self.samples_spin.value()} samples")
        self._finalize_test()
        
    @Slot(str)
    def _on_test_error(self, error: str):
        self.freq_value_label.setText("Error")
        self.status_label.setText(error)
        self.status_label.setStyleSheet(f"color: {COLORS['error']};")
        self._finalize_test()

    def _finalize_test(self):
        self.start_btn.setText("Start Test")
        self.start_btn.setEnabled(True)
        self.worker = None
        
        # Resume polling if it was active
        if self._was_polling:
            self.data_engine.start()
            self._was_polling = False
