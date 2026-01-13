"""
Calibration dialog for Modbus sensor calibration.
Supports two-point calibration protocol.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QMessageBox, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from src.models.register import Register, DisplayFormat, ByteOrder, AccessMode
from src.core.modbus_manager import ModbusManager
from src.core.data_engine import DataEngine


class CalibrationDialog(QDialog):
    """Dialog for calibrating Modbus sensors using two-point calibration."""
    
    # Command codes for calibration
    CMD_CALIBRATE_CH1_PT0 = 410
    CMD_CALIBRATE_CH1_PT1 = 411
    CMD_CALIBRATE_CH2_PT0 = 420
    CMD_CALIBRATE_CH2_PT1 = 421
    CMD_CALIBRATE_CH3_PT0 = 430
    CMD_CALIBRATE_CH3_PT1 = 431
    CMD_CALIBRATE_CH4_PT0 = 440
    CMD_CALIBRATE_CH4_PT1 = 441
    
    # Register addresses
    REG_CALIBRATION_VALUE = 56  # Size 2, float32 (was incorrectly 54)
    REG_CALIBRATION_CMD = 10    # Size 1, decimal int
    REG_STATUS = 0              # Size 1, bit 3 indicates calibration status
    
    def __init__(self, modbus: ModbusManager, data_engine: DataEngine, slave_id: int = 1, parent=None):
        super().__init__(parent)
        self.modbus = modbus
        self.data_engine = data_engine
        self.slave_id = slave_id
        self.current_point = 0  # 0 = First point, 1 = Second point
        self.current_channel = 1
        self.bit3_seen_high = False  # Track if we've seen bit 3 go to 1 (calibration started)
        
        self.setWindowTitle("Sensor Calibration")
        self.setMinimumWidth(250)
        self.setMaximumWidth(250)
        self.setModal(True)
        
        # Status monitoring timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_calibration_status)
        self.status_timer.setInterval(100)  # Check every 100ms
        
        # Timeout timer for calibration (30 seconds max)
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_calibration_timeout)
        self.status_check_count = 0
        
        self._setup_ui()
        self._update_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Channel selector
        channel_layout = QHBoxLayout()
        channel_label = QLabel("Channel:")
        # Calculate max label width to align labels
        channel_label_width = channel_label.fontMetrics().boundingRect("Channel:").width()
        value_label_width = channel_label.fontMetrics().boundingRect("Point 2 output:").width()
        max_label_width = max(channel_label_width, value_label_width) + 10
        channel_label.setFixedWidth(max_label_width)
        channel_layout.addWidget(channel_label)
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["1", "2", "3", "4"])
        self.channel_combo.setCurrentIndex(0)
        self.channel_combo.currentIndexChanged.connect(self._on_channel_changed)
        channel_layout.addWidget(self.channel_combo)
        channel_layout.addStretch()
        layout.addLayout(channel_layout)
        
        # Reference value input
        value_layout = QHBoxLayout()
        self.value_label = QLabel("Point 1 output:")
        self.value_label.setFixedWidth(max_label_width)
        value_layout.addWidget(self.value_label)
        self.value_input = QDoubleSpinBox()
        self.value_input.setDecimals(6)
        self.value_input.setRange(-1e10, 1e10)
        self.value_input.setValue(0.0)  # Default for point 1
        value_layout.addWidget(self.value_input)
        value_layout.addStretch()  # Add stretch to match channel layout structure
        layout.addLayout(value_layout)
        
        # Align channel combo box width with float input width
        # Set both to have the same preferred width (not expanding)
        input_width = 115  # Fixed preferred width for both inputs
        self.value_input.setMinimumWidth(input_width)
        self.value_input.setMaximumWidth(input_width)
        self.channel_combo.setMinimumWidth(input_width)
        self.channel_combo.setMaximumWidth(input_width)
        # Use Preferred policy so they don't expand beyond their preferred size
        self.value_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.channel_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Calibrate button
        self.calibrate_btn = QPushButton("Calibrate First Point")
        self.calibrate_btn.setMinimumHeight(40)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.calibrate_btn.setFont(font)
        self.calibrate_btn.clicked.connect(self._on_calibrate_clicked)
        layout.addWidget(self.calibrate_btn)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _on_channel_changed(self, index):
        """Handle channel selection change."""
        self.current_channel = index + 1
        # Reset to first point when channel changes
        self.current_point = 0
        self._update_ui()
    
    def _update_ui(self):
        """Update UI based on current state."""
        if self.current_point == 0:
            self.value_label.setText("Point 1 output:")
            self.value_input.setValue(0.0)  # Default for point 1
            self.calibrate_btn.setText("Calibrate First Point")
            self.status_label.setText("")
        elif self.current_point == 1:
            self.value_label.setText("Point 2 output:")
            self.value_input.setValue(100.0)  # Default for point 2
            self.calibrate_btn.setText("Calibrate Second Point")
            self.status_label.setText("")
        else:
            # Finished
            self.value_label.setText("Point 2 output:")
            self.calibrate_btn.setEnabled(False)
            self.status_label.setText("")
    
    def _get_command_code(self, channel: int, point: int) -> int:
        """Get the command code for the given channel and point."""
        base = 400 + (channel * 10)
        return base + point
    
    def _on_calibrate_clicked(self):
        """Handle calibrate button click."""
        print(f"[CALIB] Calibrate button clicked - Channel {self.current_channel}, Point {self.current_point}")
        
        if not self.modbus.is_connected:
            print("[CALIB] ERROR: Modbus not connected")
            QMessageBox.warning(self, "Not Connected", "Please connect to the Modbus device first.")
            return
        
        if not self.modbus.instrument:
            print("[CALIB] ERROR: Modbus instrument not available")
            QMessageBox.warning(self, "Not Connected", "Modbus instrument not available.")
            return
        
        if not self.data_engine:
            print("[CALIB] ERROR: Data engine not available")
            QMessageBox.warning(self, "Not Available", "Data engine not available.")
            return
        
        try:
            # Get reference value
            reference_value = self.value_input.value()
            
            # Disable controls during calibration
            self.calibrate_btn.setEnabled(False)
            self.channel_combo.setEnabled(False)
            self.value_input.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Writing calibration value...")
            self.repaint()
            
            # Step 1: Write reference value to register 54 (float32, size 2)
            # Use data_engine which handles locking and proper error handling
            # Small delay to ensure UI updates (non-blocking)
            QTimer.singleShot(100, lambda ref_val=reference_value: self._write_calibration_value(ref_val))
            
        except Exception as e:
            self._reset_ui()
            QMessageBox.critical(self, "Calibration Error", f"Failed to start calibration:\n{str(e)}")
    
    def _write_calibration_value(self, reference_value):
        """Write the calibration value (called after delay)."""
        try:
            print(f"[CALIB] Writing calibration value: {reference_value} to register {self.REG_CALIBRATION_VALUE}")
            
            if not self.modbus.is_connected or not self.modbus.instrument:
                raise ConnectionError("Modbus device not connected")
            
            calib_value_reg = Register(
                address=self.REG_CALIBRATION_VALUE,
                size=2,
                display_format=DisplayFormat.FLOAT32,
                byte_order=ByteOrder.BIG,
                access_mode=AccessMode.WRITE,
                slave_id=self.slave_id
            )
            
            print(f"[CALIB] Register config: address={calib_value_reg.address}, size={calib_value_reg.size}, "
                  f"format={calib_value_reg.display_format}, slave_id={calib_value_reg.slave_id}")
            
            # Use data_engine.write_register() which has proper locking (like explorer does)
            print(f"[CALIB] Calling data_engine.write_register()...")
            success = self.data_engine.write_register(calib_value_reg, reference_value)
            
            if not success:
                raise Exception("Write operation returned False (check data engine error signal)")
            
            print(f"[CALIB] Successfully wrote calibration value")
            
            self.status_label.setText("Waiting 1 second...")
            self.repaint()
            
            # Step 2: Wait 1 second using QTimer (non-blocking) - matching modbus explorer protocol
            QTimer.singleShot(1000, self._send_calibration_command)
            
        except Exception as e:
            import traceback
            print(f"[CALIB] ERROR writing calibration value: {str(e)}")
            print(f"[CALIB] Traceback: {traceback.format_exc()}")
            self._reset_ui()
            error_msg = f"Failed to write calibration value to register {self.REG_CALIBRATION_VALUE}:\n{str(e)}"
            QMessageBox.critical(self, "Calibration Error", error_msg)
    
    def _send_calibration_command(self):
        """Send the calibration command after the delay."""
        try:
            command_code = self._get_command_code(self.current_channel, self.current_point)
            print(f"[CALIB] Writing calibration command: {command_code} to register {self.REG_CALIBRATION_CMD}")
            
            if not self.modbus.is_connected or not self.modbus.instrument:
                raise ConnectionError("Modbus device not connected")
            
            cmd_reg = Register(
                address=self.REG_CALIBRATION_CMD,
                size=1,
                display_format=DisplayFormat.DECIMAL,
                access_mode=AccessMode.WRITE,
                slave_id=self.slave_id
            )
            
            print(f"[CALIB] Command register config: address={cmd_reg.address}, size={cmd_reg.size}, "
                  f"format={cmd_reg.display_format}, slave_id={cmd_reg.slave_id}")
            
            # Use data_engine.write_register() which has proper locking (like explorer does)
            print(f"[CALIB] Calling data_engine.write_register() for command...")
            success = self.data_engine.write_register(cmd_reg, float(command_code))
            
            if not success:
                raise Exception("Write operation returned False (check data engine error signal)")
            
            print(f"[CALIB] Successfully wrote calibration command")
            
            self.status_label.setText(f"Calibration command sent. Monitoring status...")
            self.repaint()
            
            # Step 4: Monitor bit 3 of register 0 for calibration completion
            # Protocol: bit 3 should go from 0 -> 1 (calibration started) -> 0 (calibration complete)
            self.status_check_count = 0
            self.bit3_seen_high = False  # Reset flag - we need to see bit 3 go to 1 first
            self.timeout_timer.start(30000)  # 30 second timeout
            self.status_timer.start()
            print(f"[CALIB] Started monitoring calibration status (waiting for bit 3: 0 -> 1 -> 0)...")
            
        except Exception as e:
            import traceback
            print(f"[CALIB] ERROR writing calibration command: {str(e)}")
            print(f"[CALIB] Traceback: {traceback.format_exc()}")
            self._reset_ui()
            error_msg = f"Failed to write calibration command to register {self.REG_CALIBRATION_CMD}:\n{str(e)}"
            QMessageBox.critical(self, "Calibration Error", error_msg)
    
    
    def _check_calibration_status(self):
        """Check if calibration is complete by monitoring bit 3 of register 0."""
        try:
            self.status_check_count += 1
            
            # Use data_engine's safe read method which uses locking
            print(f"[CALIB] Reading status register (check #{self.status_check_count})...")
            status_value = self.data_engine.read_register_safe(self.slave_id, self.REG_STATUS)
            
            if status_value is None:
                # Read failed - skip this check
                if self.status_check_count % 10 == 0:  # Only print every 10th failure
                    print(f"[CALIB] WARNING: Failed to read status register (check #{self.status_check_count})")
                
                # If we can't read status after many attempts, show error
                if self.status_check_count > 100:  # After 10 seconds of failed reads
                    print(f"[CALIB] ERROR: Failed to read status after {self.status_check_count} attempts")
                    self.status_timer.stop()
                    self.timeout_timer.stop()
                    self._reset_ui()
                    QMessageBox.warning(
                        self,
                        "Status Read Error",
                        f"Could not read calibration status from device after {self.status_check_count} attempts.\n\n"
                        "Please check the connection and try again."
                    )
                return  # Skip this check, try again next time
            
            print(f"[CALIB] Status register value: {status_value} (binary: {status_value:016b})")
            
            # Check bit 3 (0-indexed, so bit 3 is the 4th bit)
            is_calibrating = (status_value >> 3) & 1
            
            if self.status_check_count % 10 == 0:  # Print every 10 checks (every second)
                print(f"[CALIB] Status check #{self.status_check_count}: register 0 = {status_value:016b}, bit 3 = {is_calibrating}, seen_high = {self.bit3_seen_high}")
            
            # Protocol: bit 3 should go from 0 -> 1 (calibration started) -> 0 (calibration complete)
            if is_calibrating:
                # Bit 3 is 1 - calibration is in progress
                if not self.bit3_seen_high:
                    self.bit3_seen_high = True
                    print(f"[CALIB] Bit 3 went HIGH (calibration started) after {self.status_check_count} checks")
            elif self.bit3_seen_high:
                # Bit 3 went from 1 back to 0 - calibration is complete
                print(f"[CALIB] Calibration complete detected after {self.status_check_count} checks (bit 3: 1 -> 0)")
                self.status_timer.stop()
                self.timeout_timer.stop()
                self._on_calibration_complete()
            # else: bit 3 is 0 but we haven't seen it go high yet - keep waiting
                
        except Exception as e:
            # Catch any unexpected errors to prevent crash
            import traceback
            print(f"[CALIB] CRITICAL ERROR in status check: {str(e)}")
            print(f"[CALIB] Traceback: {traceback.format_exc()}")
            # Stop timers to prevent further errors
            try:
                self.status_timer.stop()
                self.timeout_timer.stop()
            except:
                pass
            # Don't show message box here as it might cause recursion - just log and continue
            # The timeout timer will eventually catch this if it persists
    
    def _on_calibration_complete(self):
        """Handle calibration completion."""
        self.progress_bar.setVisible(False)
        
        if self.current_point == 0:
            # First point done, move to second point (no popup)
            self.current_point = 1
            self._update_ui()
            self._reset_ui()
        else:
            # Second point done, calibration complete
            self.current_point = 2
            self._update_ui()
            self._reset_ui()
            # Show simple completion message
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Calibration Complete")
            msg.setText(f"Channel {self.current_channel} calibration complete.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()  # Wait for user to click OK
            # Close calibration dialog after message box is dismissed
            self.accept()
    
    def _reset_ui(self):
        """Reset UI controls to enabled state."""
        self.calibrate_btn.setEnabled(True)
        self.channel_combo.setEnabled(True)
        self.value_input.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def _on_calibration_timeout(self):
        """Handle calibration timeout."""
        self.status_timer.stop()
        self._reset_ui()
        QMessageBox.warning(
            self,
            "Calibration Timeout",
            "Calibration did not complete within 30 seconds.\n"
            "Please check the device status and try again."
        )
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self.status_timer.stop()
        self.timeout_timer.stop()
        super().closeEvent(event)
