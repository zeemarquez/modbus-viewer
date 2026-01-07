"""
Modbus RTU communication manager with multi-device support.
"""

import struct
from typing import Optional, Union, List, Dict
import minimalmodbus
import serial

from src.models.register import Register, ByteOrder


class ModbusManager:
    """Manages Modbus RTU serial communication with multiple devices."""
    
    def __init__(self):
        self.instrument: Optional[minimalmodbus.Instrument] = None
        self.port: str = ""
        self.slave_ids: List[int] = []  # List of connected slave IDs
        self.is_connected: bool = False
        self._current_slave_id: int = 1  # Currently active slave ID
    
    def connect(
        self,
        port: str,
        slave_ids: List[int] = None,
        baud_rate: int = 9600,
        parity: str = "N",
        stop_bits: int = 1,
        timeout: float = 1.0,
    ) -> None:
        """
        Connect to Modbus devices on a serial port.
        
        Args:
            port: COM port (e.g., "COM11")
            slave_ids: List of Modbus slave addresses to connect to (1-247)
            baud_rate: Serial baud rate
            parity: Parity ('N', 'E', 'O')
            stop_bits: Stop bits (1 or 2)
            timeout: Read timeout in seconds
        """
        self.disconnect()
        
        if slave_ids is None:
            slave_ids = [1]
        
        self.port = port
        self.slave_ids = slave_ids
        self._current_slave_id = slave_ids[0] if slave_ids else 1
        
        # Create instrument with first slave ID
        self.instrument = minimalmodbus.Instrument(port, self._current_slave_id)
        
        # Configure serial settings
        self.instrument.serial.baudrate = baud_rate
        self.instrument.serial.bytesize = 8
        
        # Set parity
        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD,
        }
        self.instrument.serial.parity = parity_map.get(parity, serial.PARITY_NONE)
        self.instrument.serial.stopbits = stop_bits
        self.instrument.serial.timeout = timeout
        
        # Set write timeout
        self.instrument.serial.write_timeout = 0.5
        
        # Re-enable buffer clearing for reliability
        # This prevents the "fails after 1s" issue by ensuring we start fresh
        self.instrument.clear_buffers_before_each_transaction = False # Changed to False for performance
        
        # Keep persistent connection
        self.instrument.close_port_after_each_call = False
        
        self.is_connected = True
    
    def disconnect(self) -> None:
        """Disconnect from Modbus devices."""
        if self.instrument and self.instrument.serial.is_open:
            self.instrument.serial.close()
        self.instrument = None
        self.is_connected = False
        self.slave_ids = []
    
    def set_slave_id(self, slave_id: int) -> None:
        """
        Set the current slave ID for communication.
        
        Args:
            slave_id: Modbus slave address to communicate with
        """
        if self.instrument and slave_id != self._current_slave_id:
            self.instrument.address = slave_id
            self._current_slave_id = slave_id
            # Small delay after switching slave ID to allow RS485 bus to settle
            import time
            time.sleep(0.01)  # 10ms
    
    def read_registers(self, slave_id: int, address: int, count: int) -> List[int]:
        """
        Read multiple 16-bit registers from a device.
        
        Args:
            slave_id: Device address
            address: Start register address
            count: Number of registers to read
            
        Returns:
            List of integers
        """
        if not self.instrument:
            raise ConnectionError("Not connected")
            
        self.set_slave_id(slave_id)
        return self.instrument.read_registers(address, count)

    def read_register_single(self, slave_id: int, address: int) -> int:
        """
        Read a single 16-bit register from a device.
        
        Args:
            slave_id: Device address
            address: Register address
            
        Returns:
            Register value
        """
        if not self.instrument:
            raise ConnectionError("Not connected")
            
        self.set_slave_id(slave_id)
        return self.instrument.read_register(address, 0)

    
    def read_register(self, register: Register) -> Union[int, float]:
        """
        Read value from a register.
        
        Args:
            register: Register configuration (includes slave_id)
            
        Returns:
            Raw value (unsigned integer)
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
        # Switch to correct slave ID
        self.set_slave_id(register.slave_id)
        
        try:
            if register.size == 1:
                # Single 16-bit register
                return self.instrument.read_register(register.address, 0)
            else:
                # Multiple registers
                regs = self.instrument.read_registers(register.address, register.size)
                return self._combine_registers(regs, register.byte_order)
        except Exception as e:
            # Re-raise with better message
            raise Exception(f"Modbus read error at D{register.slave_id}.R{register.address}: {e}")

    def read_registers_batch(self, slave_id: int, start_address: int, count: int) -> list:
        """
        Read a batch of contiguous 16-bit registers from a specific device.
        
        Args:
            slave_id: Modbus slave address
            start_address: First register address
            count: Number of registers to read
            
        Returns:
            List of 16-bit integers
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
        # Switch to correct slave ID
        self.set_slave_id(slave_id)
        
        try:
            return self.instrument.read_registers(start_address, count)
        except Exception as e:
            raise Exception(f"Modbus batch read error (D{slave_id}, {start_address}, {count}): {e}")
    
    def write_register(self, register: Register, value: Union[int, float]) -> None:
        """
        Write value to a register.
        
        Args:
            register: Register configuration (includes slave_id)
            value: Value to write
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
        # Switch to correct slave ID
        self.set_slave_id(register.slave_id)
        
        if register.size == 1:
            # Single 16-bit register
            int_value = int(value) & 0xFFFF
            self.instrument.write_register(register.address, int_value, 0)
        else:
            # Multiple registers - need to split value
            regs = self._split_value(value, register.size, register.byte_order)
            self.instrument.write_registers(register.address, regs)
    
    def _combine_registers(
        self,
        regs: list,
        byte_order: ByteOrder,
    ) -> int:
        """Combine multiple 16-bit registers into a single unsigned value."""
        if byte_order == ByteOrder.LITTLE:
            regs = list(reversed(regs))
        
        # Combine registers (big endian order after potential reversal)
        combined = 0
        for reg in regs:
            combined = (combined << 16) | reg
        
        return combined
    
    def _split_value(
        self,
        value: Union[int, float],
        size: int,
        byte_order: ByteOrder,
    ) -> list:
        """Split a value into multiple 16-bit registers."""
        combined = int(value)
        if combined < 0:
            # Handle signed values
            if size == 2:
                combined = combined & 0xFFFFFFFF
            elif size == 4:
                combined = combined & 0xFFFFFFFFFFFFFFFF
        
        # Split into 16-bit registers (big endian)
        regs = []
        for _ in range(size):
            regs.insert(0, combined & 0xFFFF)
            combined >>= 16
        
        if byte_order == ByteOrder.LITTLE:
            regs = list(reversed(regs))
        
        return regs
    
    def test_connection(self, slave_id: int = None) -> bool:
        """Test if connection is working by trying to read a register."""
        if not self.instrument:
            return False
        
        if slave_id is not None:
            self.set_slave_id(slave_id)
        
        try:
            self.instrument.read_register(0, 0)
            return True
        except Exception:
            return False

    @staticmethod
    def probe_device(
        port: str,
        slave_id: int,
        baud_rate: int,
        register_address: int,
        parity: str = "N",
        stop_bits: int = 1,
        timeout: float = 0.1,
    ) -> bool:
        """
        Probe a single slave ID to see if it responds.
        
        Args:
            port: COM port
            slave_id: Modbus slave address
            baud_rate: Serial baud rate
            register_address: Register address to try reading
            parity: Parity ('N', 'E', 'O')
            stop_bits: Stop bits (1 or 2)
            timeout: Read timeout in seconds
            
        Returns:
            True if device responded, False otherwise
        """
        try:
            instrument = minimalmodbus.Instrument(port, slave_id)
            instrument.serial.baudrate = baud_rate
            
            parity_map = {
                'N': serial.PARITY_NONE,
                'E': serial.PARITY_EVEN,
                'O': serial.PARITY_ODD,
            }
            instrument.serial.parity = parity_map.get(parity, serial.PARITY_NONE)
            instrument.serial.stopbits = stop_bits
            instrument.serial.timeout = timeout
            
            # Try reading the specified register
            instrument.read_register(register_address, 0)
            return True
        except Exception:
            return False
        finally:
            if 'instrument' in locals() and instrument.serial.is_open:
                instrument.serial.close()
