"""
Modbus RTU communication manager.
"""

import struct
from typing import Optional, Union
import minimalmodbus
import serial

from src.models.register import Register, ByteOrder


class ModbusManager:
    """Manages Modbus RTU serial communication."""
    
    def __init__(self):
        self.instrument: Optional[minimalmodbus.Instrument] = None
        self.port: str = ""
        self.slave_id: int = 1
        self.is_connected: bool = False
    
    def connect(
        self,
        port: str,
        slave_id: int = 1,
        baud_rate: int = 9600,
        parity: str = "N",
        stop_bits: int = 1,
        timeout: float = 1.0,
    ) -> None:
        """
        Connect to Modbus device.
        
        Args:
            port: COM port (e.g., "COM11")
            slave_id: Modbus slave address (1-247)
            baud_rate: Serial baud rate
            parity: Parity ('N', 'E', 'O')
            stop_bits: Stop bits (1 or 2)
            timeout: Read timeout in seconds
        """
        self.disconnect()
        
        self.port = port
        self.slave_id = slave_id
        
        # Create instrument
        self.instrument = minimalmodbus.Instrument(port, slave_id)
        
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
        self.instrument.clear_buffers_before_each_transaction = True
        
        # Keep persistent connection
        self.instrument.close_port_after_each_call = False
        
        self.is_connected = True
    
    def disconnect(self) -> None:
        """Disconnect from Modbus device."""
        if self.instrument and self.instrument.serial.is_open:
            self.instrument.serial.close()
        self.instrument = None
        self.is_connected = False
    
    def read_register(self, register: Register) -> Union[int, float]:
        """
        Read value from a register.
        
        Args:
            register: Register configuration
            
        Returns:
            Raw value (unsigned integer)
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
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
            raise Exception(f"Modbus read error at address {register.address}: {e}")

    def read_registers_batch(self, start_address: int, count: int) -> list:
        """
        Read a batch of contiguous 16-bit registers.
        
        Args:
            start_address: First register address
            count: Number of registers to read
            
        Returns:
            List of 16-bit integers
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
        try:
            return self.instrument.read_registers(start_address, count)
        except Exception as e:
            raise Exception(f"Modbus batch read error ({start_address}, {count}): {e}")
    
    def write_register(self, register: Register, value: Union[int, float]) -> None:
        """
        Write value to a register.
        
        Args:
            register: Register configuration
            value: Value to write
        """
        if not self.instrument:
            raise ConnectionError("Not connected to Modbus device")
        
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
    
    def test_connection(self) -> bool:
        """Test if connection is working by trying to read a register."""
        if not self.instrument:
            return False
        try:
            self.instrument.read_register(0, 0)
            return True
        except Exception:
            return False
