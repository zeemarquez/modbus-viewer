"""
Data engine for polling Modbus registers and processing values.
Supports multiple devices on the same serial bus.
"""

import time
import threading
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass
from collections import deque

from PySide6.QtCore import QObject, Signal, Slot

from src.models.register import Register, DisplayFormat
from src.models.variable import Variable
from src.core.modbus_manager import ModbusManager
from src.core.variable_engine import VariableEvaluator


@dataclass
class DataPoint:
    """A single data point for plotting."""
    timestamp: float
    value: float


class DataEngine(QObject):
    """
    Engine for polling Modbus registers and emitting data updates.
    Runs polling in a dedicated background thread for maximum performance.
    Supports multiple devices on the same serial bus.
    
    Signals:
        data_updated: Emitted when register values are updated
        error_occurred: Emitted when a read error occurs
        connection_lost: Emitted when connection is lost
    """
    
    # Signals
    data_updated = Signal()  # Emitted after each poll cycle
    error_occurred = Signal(str)  # Error message
    connection_lost = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.modbus: Optional[ModbusManager] = None
        self.registers: List[Register] = []
        self.variables: List[Variable] = []
        self.variable_evaluator = VariableEvaluator()
        
        # Polling state
        self._poll_interval = 100  # ms
        self._is_running = False
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._write_lock = threading.Lock()
        
        # Data history for plotting (designator -> deque of DataPoints)
        # Keys are like "D1.R0" for registers, "var_name" for variables
        self._history: Dict[str, deque] = {}
        self._history_max_seconds = 300  # 5 minutes max history
        
        # Statistics
        self._poll_count = 0
        self._error_count = 0
        self._last_poll_duration = 0.0  # ms
        self._last_poll_time = 0.0
        
        # Pre-calculated batches for faster polling, grouped by (slave_id, fast_poll)
        # Structure: Dict[slave_id, Dict['fast'|'slow', List[Tuple[start, count, regs]]]]
        self._device_batches: Dict[int, Dict[str, List[Tuple[int, int, List[Register]]]]] = {}
        self._last_slow_poll_time = 0.0
        self._slow_poll_interval = 0.5  # 500ms for slow registers
    
    @property
    def poll_interval(self) -> int:
        return self._poll_interval
    
    def set_poll_interval(self, ms: int) -> None:
        self._poll_interval = ms
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set registers to poll."""
        with self._write_lock:
            self.registers = registers
            self._rebuild_batches()
            
            # Initialize history for new registers
            for reg in registers:
                key = reg.designator  # e.g., "D1.R0"
                if key not in self._history:
                    self._history[key] = deque()
    
    def _rebuild_batches(self) -> None:
        """Rebuild polling batches grouped by slave_id."""
        self._device_batches.clear()
        
        # Group registers by slave_id
        by_device: Dict[int, List[Register]] = {}
        for reg in self.registers:
            if reg.slave_id not in by_device:
                by_device[reg.slave_id] = []
            by_device[reg.slave_id].append(reg)
        
        # For each device, split into fast and slow, then create batches
        for slave_id, device_regs in by_device.items():
            fast_regs = [r for r in device_regs if r.fast_poll]
            slow_regs = [r for r in device_regs if not r.fast_poll]
            
            fast_sorted = sorted(fast_regs, key=lambda r: r.address)
            slow_sorted = sorted(slow_regs, key=lambda r: r.address)
            
            self._device_batches[slave_id] = {
                'fast': self._group_registers(fast_sorted),
                'slow': self._group_registers(slow_sorted),
            }
    
    def set_variables(self, variables: List[Variable]) -> None:
        """Set variables to evaluate."""
        with self._write_lock:
            self.variables = variables
            self.variable_evaluator.set_registers(self.registers)
            # Initialize history for new variables
            for var in variables:
                key = var.designator
                if key not in self._history:
                    self._history[key] = deque()
    
    def start(self) -> None:
        """Start polling thread."""
        if self._is_running:
            return
        
        self._is_running = True
        self._stop_event.clear()
        self._poll_thread = threading.Thread(target=self._run_poll_loop, daemon=True)
        self._poll_thread.start()
    
    def stop(self) -> None:
        """Stop polling thread."""
        self._is_running = False
        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=1.0)
            self._poll_thread = None
    
    def _run_poll_loop(self) -> None:
        """Background thread loop for fast polling."""
        last_gui_update = 0
        GUI_UPDATE_INTERVAL = 0.033  # ~30 FPS limit for GUI updates
        
        while not self._stop_event.is_set():
            loop_start = time.perf_counter()
            
            # Perform poll
            if self._poll():
                # Success
                duration = (time.perf_counter() - loop_start) * 1000
                self._last_poll_duration = duration
                
                # Throttle GUI updates to ~30 FPS to save CPU and keep UI responsive
                now = time.time()
                if now - last_gui_update >= GUI_UPDATE_INTERVAL:
                    self.data_updated.emit()
                    last_gui_update = now
            
            # Minimal sleep to allow serial bus turnaround (Modbus RTU silent interval)
            # Even at high speed, most devices need 2-5ms to reset their state machine
            time.sleep(0.005)
    
    def _poll(self) -> bool:
        """Single poll cycle - polls all devices."""
        if not self.modbus or not self.modbus.is_connected:
            self._is_running = False
            self.connection_lost.emit()
            return False
        
        now = time.time()
        self._last_poll_time = now
        self._poll_count += 1
        
        poll_slow = now - self._last_slow_poll_time >= self._slow_poll_interval
        if poll_slow:
            self._last_slow_poll_time = now
        
        try:
            with self._write_lock:
                # Poll each device
                for slave_id, batches in self._device_batches.items():
                    try:
                        # Always poll fast registers
                        self._poll_device_batches(slave_id, batches['fast'], now)
                        
                        # Poll slow registers every 500ms
                        if poll_slow:
                            self._poll_device_batches(slave_id, batches['slow'], now)
                    except Exception as e:
                        # Device-specific error - don't stop the whole engine unless it's a serial port error
                        if any(err in str(e).lower() for err in ["access is denied", "file not found", "device not found", "permissionerror"]):
                            raise e
                        # Otherwise just log it and continue to next device
                        self._error_count += 1
                
                # Evaluate variables
                for variable in self.variables:
                    try:
                        value = self.variable_evaluator.evaluate(variable.expression)
                        variable.value = value
                        variable.error = None
                        self._append_history(variable.designator, value, now)
                    except Exception as e:
                        variable.value = None
                        variable.error = str(e)
        except Exception as e:
            # If we get here, it's a critical serial error from _poll_device_batches
            self._is_running = False
            self.modbus.is_connected = False
            self.connection_lost.emit()
            return False
        
        return True

    def _poll_device_batches(self, slave_id: int, batches: List[Tuple[int, int, List[Register]]], now: float) -> None:
        """Poll register batches for a specific device."""
        if not batches:
            return
        
        for start_addr, count, regs_in_group in batches:
            try:
                if count == 1:
                    # Single register read
                    raw_value = self.modbus.read_register_single(slave_id, start_addr)
                    self._update_register_values(regs_in_group, [raw_value], start_addr, now)
                else:
                    # Multi-register read
                    try:
                        raw_values = self.modbus.read_registers(slave_id, start_addr, count)
                        self._update_register_values(regs_in_group, raw_values, start_addr, now)
                    except Exception as e:
                        # Check for critical serial errors (like port unplugged)
                        if any(err in str(e).lower() for err in ["access is denied", "file not found", "device not found", "permissionerror"]):
                            raise e
                            
                        # Fallback: if batch read fails, try individual reads
                        for reg in regs_in_group:
                            try:
                                val = self.modbus.read_register_single(slave_id, reg.address)
                                self._update_register_values([reg], [val], reg.address, now)
                            except Exception as individual_e:
                                if any(err in str(individual_e).lower() for err in ["access is denied", "file not found", "device not found", "permissionerror"]):
                                    raise individual_e
                                reg.error = str(individual_e)
                                self._error_count += 1
                        
            except Exception as e:
                # If it's a critical serial error, re-raise to be caught in _poll
                if any(err in str(e).lower() for err in ["access is denied", "file not found", "device not found", "permissionerror"]):
                    raise e
                    
                for reg in regs_in_group:
                    reg.error = str(e)
                self._error_count += 1

    def _update_register_values(self, registers: List[Register], raw_values: List[int], start_addr: int, now: float) -> None:
        """Helper to map raw values back to registers and update their state."""
        for reg in registers:
            # Calculate offset within the raw values list
            offset = reg.address - start_addr
            if offset < 0 or offset >= len(raw_values):
                continue
                
            try:
                if reg.size == 1:
                    raw_val = raw_values[offset]
                else:
                    if offset + reg.size > len(raw_values):
                        continue
                    chunk = raw_values[offset:offset + reg.size]
                    raw_val = self.modbus._combine_registers(chunk, reg.byte_order)
                
                reg.raw_value = raw_val
                reg.error = None
                reg.previous_value = reg.scaled_value
                # For float32, convert raw integer to float first, then apply scale
                # For other formats, raw_val is already numeric
                if reg.display_format == DisplayFormat.FLOAT32 and reg.size == 2:
                    float_val = reg.convert_raw_to_float(raw_val)
                    reg.scaled_value = reg.apply_scale(float_val)
                else:
                    reg.scaled_value = reg.apply_scale(raw_val)
                self._append_history(reg.designator, reg.scaled_value, now)
            except Exception as e:
                reg.error = str(e)

    def _group_registers(self, sorted_regs: List[Register]) -> List[Tuple[int, int, List[Register]]]:
        """Group registers into contiguous blocks for efficient reading."""
        if not sorted_regs:
            return []
        
        groups = []
        current_group_regs = [sorted_regs[0]]
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
                current_group_regs.append(reg)
                current_end = reg.address + reg.size
            else:
                # Close current group and start new one
                groups.append((current_start, current_end - current_start, current_group_regs))
                current_group_regs = [reg]
                current_start = reg.address
                current_end = current_start + reg.size
        
        # Add last group
        groups.append((current_start, current_end - current_start, current_group_regs))
        return groups

    def _append_history(self, key: str, value: float, timestamp: float) -> None:
        """Append value to history buffer."""
        if key in self._history and value is not None:
            self._history[key].append(DataPoint(timestamp=timestamp, value=value))
            self._trim_history(key, timestamp)

    def _trim_history(self, key: str, now: float) -> None:
        """Trim old data from history."""
        history = self._history[key]
        cutoff = now - self._history_max_seconds
        while history and history[0].timestamp < cutoff:
            history.popleft()

    def get_history_arrays(self, key: str, window_seconds: float) -> Tuple[List[float], List[float]]:
        """Get history data as two lists (times relative to now, values)."""
        if key not in self._history:
            return [], []
        
        now = time.time()
        cutoff = now - window_seconds
        
        times = []
        values = []
        
        with self._write_lock:
            history = self._history[key]
            for dp in history:
                if dp.timestamp >= cutoff:
                    times.append(dp.timestamp - now)
                    values.append(dp.value)
        
        return times, values

    def write_register(self, register: Register, value: float) -> bool:
        """Write value to register, with locking to prevent thread conflicts."""
        if not self.modbus or not self.modbus.is_connected:
            return False
        
        try:
            with self._write_lock:
                # For float32 format, write the float value directly without scaling
                # For other formats, convert scaled value back to raw
                from src.models.register import DisplayFormat
                if register.display_format == DisplayFormat.FLOAT32 and register.size == 2:
                    raw_value = value  # Write float directly as IEEE 754
                else:
                    raw_value = value / register.scale if register.scale != 0 else value
                self.modbus.write_register(register, raw_value)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Write error: {e}")
            return False
    
    def read_register_safe(self, slave_id: int, address: int) -> Optional[int]:
        """Read a register safely with locking to prevent thread conflicts."""
        if not self.modbus or not self.modbus.is_connected:
            return None
        
        try:
            with self._write_lock:
                return self.modbus.read_register_single(slave_id, address)
        except Exception as e:
            # Don't emit error signal for calibration reads - just return None
            return None
    
    def clear_history(self) -> None:
        """Clear all history data."""
        with self._write_lock:
            for deque_obj in self._history.values():
                deque_obj.clear()

    @property
    def statistics(self) -> dict:
        """Get polling statistics."""
        return {
            'poll_count': self._poll_count,
            'error_count': self._error_count,
            'poll_interval': self._poll_interval,
            'is_running': self._is_running,
            'last_poll_duration': self._last_poll_duration,
        }
