"""
Register data model with scaling support.
"""

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ByteOrder(Enum):
    BIG = "big"
    LITTLE = "little"


class DisplayFormat(Enum):
    DECIMAL = "decimal"
    HEX = "hex"
    BINARY = "binary"
    FLOAT32 = "float32"


class AccessMode(Enum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


@dataclass
class Register:
    """Represents a Modbus register configuration."""
    
    address: int
    size: int = 1
    label: str = ""
    byte_order: ByteOrder = ByteOrder.BIG
    scale: float = 1.0
    access_mode: AccessMode = AccessMode.READ
    display_format: DisplayFormat = DisplayFormat.DECIMAL
    fast_poll: bool = False  # If True, poll at maximum speed
    
    # Runtime/context attributes
    slave_id: int = 1
    
    # Runtime values (not serialized)
    raw_value: Optional[int] = field(default=None, repr=False)
    scaled_value: Optional[float] = field(default=None, repr=False)
    previous_value: Optional[float] = field(default=None, repr=False)
    error: Optional[str] = field(default=None, repr=False)

    @property
    def designator(self) -> str:
        """Get the full designator (e.g., D1.R13)."""
        return f"D{self.slave_id}.R{self.address}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "address": self.address,
            "size": self.size,
            "label": self.label,
            "byte_order": self.byte_order.value,
            "scale": self.scale,
            "access_mode": self.access_mode.value,
            "display_format": self.display_format.value,
            "fast_poll": self.fast_poll,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Register":
        """Create Register from dictionary."""
        # Handle legacy 'expression' field
        scale = data.get("scale", 1.0)
        if "expression" in data and scale == 1.0:
            # Try to extract simple scale from expression like "value * 0.1"
            expr = data.get("expression", "value")
            if expr != "value":
                try:
                    # Simple parsing for "value * X" pattern
                    if "*" in expr:
                        parts = expr.replace("value", "").replace("*", "").strip()
                        scale = float(parts)
                except:
                    pass
        
        return cls(
            address=data["address"],
            size=data.get("size", 1),
            label=data.get("label", ""),
            byte_order=ByteOrder(data.get("byte_order", "big")),
            scale=scale,
            access_mode=AccessMode(data.get("access_mode", "read")),
            display_format=DisplayFormat(data.get("display_format", "decimal")),
            fast_poll=data.get("fast_poll", False),
        )
    
    def convert_raw_to_float(self, raw_value: int) -> float:
        """Convert raw integer value to float based on display format."""
        if self.display_format == DisplayFormat.FLOAT32 and self.size == 2:
            # Convert integer to 4 bytes
            # The _combine_registers function already handles word order,
            # so the integer's bytes are in the correct order for the byte_order setting
            int_val = int(raw_value) & 0xFFFFFFFF
            
            # Convert to bytes - use big-endian to preserve the order from _combine_registers
            bytes_val = int_val.to_bytes(4, byteorder='big')
            
            # Unpack as float32 according to byte order
            # For BIG: bytes are already in big-endian order, use '>f'
            # For LITTLE: bytes are in big-endian order but we need little-endian float,
            # so we need to reverse the bytes or use '<f' on reversed bytes
            if self.byte_order == ByteOrder.BIG:
                return struct.unpack('>f', bytes_val)[0]
            else:
                # For little-endian, reverse the byte order before unpacking
                bytes_val_le = bytes(reversed(bytes_val))
                return struct.unpack('<f', bytes_val_le)[0]
        else:
            # For non-float32 formats, return as float
            return float(raw_value)
    
    def apply_scale(self, raw_value: float) -> float:
        """Apply scale to raw value."""
        return raw_value * self.scale
    
    def format_value(self, value: Optional[float]) -> str:
        """Format value according to display format."""
        if value is None:
            return "---"
        
        try:
            if self.display_format == DisplayFormat.FLOAT32:
                # For float32, value is already a float (converted from raw integer)
                # Just format it with appropriate precision
                return f"{value:.6f}"
            
            int_val = int(value)
            if self.display_format == DisplayFormat.HEX:
                if self.size == 1:
                    return f"0x{int_val & 0xFFFF:04X}"
                else:
                    return f"0x{int_val & 0xFFFFFFFF:08X}"
            elif self.display_format == DisplayFormat.BINARY:
                if self.size == 1:
                    return f"{int_val & 0xFFFF:016b}"
                else:
                    return f"{int_val & 0xFFFFFFFF:032b}"
            else:
                # Decimal - show float if not integer
                if isinstance(value, float) and value != int_val:
                    return f"{value:.4f}"
                return str(int_val)
        except (ValueError, TypeError, struct.error):
            return str(value)
    
    def has_changed(self) -> bool:
        """Check if value has changed since last update."""
        if self.scaled_value is None or self.previous_value is None:
            return False
        return self.scaled_value != self.previous_value
    
    def copy(self) -> "Register":
        """Create a copy of this register."""
        return Register(
            address=self.address,
            size=self.size,
            label=self.label,
            byte_order=self.byte_order,
            scale=self.scale,
            access_mode=self.access_mode,
            display_format=self.display_format,
            fast_poll=self.fast_poll,
            slave_id=self.slave_id,
        )
