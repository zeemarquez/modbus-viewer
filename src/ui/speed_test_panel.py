"""
Speed test panel for measuring Modbus read performance.
"""

import time
from typing import List, Dict, Tuple
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
    
    def __init__(self, modbus: ModbusManager, registers: List[Register], num_samples: int,
                 use_batching: bool = False, clear_buffers: bool = True, close_port: bool = False):
        super().__init__()
        self.modbus = modbus
        self.registers = registers
        self.num_samples = num_samples
        self.use_batching = use_batching
        self.clear_buffers = clear_buffers
        self.close_port = close_port
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        
    def _group_registers(self, sorted_regs: List[Register]) -> List[Tuple[int, int]]:
        """Group registers into contiguous blocks for efficient reading."""
        if not sorted_regs:
            return []
        
        groups = []
        current_start = sorted_regs[0].address
        current_end = current_start + sorted_regs[0].size
        
        # Modbus limits: max 125 registers per request
        MAX_READ = 120 
        # Max gap to fill between registers (reading extra registers is often faster than new request)
        MAX_GAP = 20 
        
        for i in range(1, len(sorted_regs)):
            reg = sorted_regs[i]
            gap = reg.address - current_end
            
            if gap <= MAX_GAP and (reg.address + reg.size - current_start) <= MAX_READ:
                # Add to current group
                current_end = reg.address + reg.size
            else:
                # Close current group and start new one
                groups.append((current_start, current_end - current_start))
                current_start = reg.address
                current_end = current_start + reg.size
        
        # Add last group
        groups.append((current_start, current_end - current_start))
        return groups

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
            
            # Save original settings
            orig_clear = instrument.clear_buffers_before_each_transaction
            orig_close = instrument.close_port_after_each_call
            
            # Apply test settings
            instrument.clear_buffers_before_each_transaction = self.clear_buffers
            instrument.close_port_after_each_call = self.close_port
            
            # Prepare batches if enabled
            if self.use_batching:
                sorted_regs = sorted(self.registers, key=lambda r: r.address)
                batches = self._group_registers(sorted_regs)
            
            start_time = time.time()
            total_reads = 0
            total_registers = 0
            
            for i in range(self.num_samples):
                if not self._is_running:
                    break
                    
                if self.use_batching:
                    for start_addr, count in batches:
                        if not self._is_running:
                            break
                        instrument.read_registers(start_addr, count)
                        total_reads += 1
                        total_registers += count
                else:
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
            
            # Restore original settings
            instrument.clear_buffers_before_each_transaction = orig_clear
            instrument.close_port_after_each_call = orig_close
            
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
        settings_layout = QVBoxLayout(settings_group)
        
        # Samples row
        samples_row = QHBoxLayout()
        samples_row.addWidget(QLabel("Samples:"))
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(1, 10000)
        self.samples_spin.setValue(100)
        samples_row.addWidget(self.samples_spin)
        settings_layout.addLayout(samples_row)
        
        # Options row
        self.batch_check = QCheckBox("Batch Read")
        self.batch_check.setToolTip("Group contiguous registers into single Modbus requests. This is how the app normally polls data.")
        settings_layout.addWidget(self.batch_check)
        
        self.clear_buffers_check = QCheckBox("Clear Buffers")
        self.clear_buffers_check.setChecked(True)
        self.clear_buffers_check.setToolTip("Clear serial buffers before each transaction. Increases reliability but adds slight overhead.")
        settings_layout.addWidget(self.clear_buffers_check)
        
        self.close_port_check = QCheckBox("Close Port After Call")
        self.close_port_check.setToolTip("Close and reopen the serial port for every request. This will significantly decrease performance.")
        settings_layout.addWidget(self.close_port_check)
        
        layout.addWidget(settings_group)
        
        # Start button
        self.start_btn = QPushButton("Start Test")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                font-weight: bold; 
                background-color: {COLORS['accent']}; 
                color: white;
                border: none;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_disabled']};
            }}
        """)
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
            
    def set_connected(self, connected: bool):
        """Update connection state."""
        self.start_btn.setEnabled(connected)
        if not connected:
            self.status_label.setText("Modbus not connected")
        else:
            self.status_label.setText("Select registers and press Start")
            
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
            self.samples_spin.value(),
            use_batching=self.batch_check.isChecked(),
            clear_buffers=self.clear_buffers_check.isChecked(),
            close_port=self.close_port_check.isChecked()
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
