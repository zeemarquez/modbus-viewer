"""
Bit data model for individual register bits.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Bit:
    """Represents a single bit from a register."""
    
    name: str
    register_address: int  # Address of the source register
    bit_index: int  # 0-15 for 16-bit registers
    slave_id: int = 1  # Slave ID of the device this bit's register belongs to
    label: str = ""
    
    # Runtime values (not serialized)
    value: Optional[bool] = field(default=None, repr=False)
    error: Optional[str] = field(default=None, repr=False)
    
    @property
    def designator(self) -> str:
        """Get the full designator for this bit (e.g., D1.R13.B5)."""
        return f"D{self.slave_id}.R{self.register_address}.B{self.bit_index}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "register_address": self.register_address,
            "bit_index": self.bit_index,
            "label": self.label,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bit":
        """Create Bit from dictionary."""
        return cls(
            name=data["name"],
            register_address=data["register_address"],
            bit_index=data["bit_index"],
            label=data.get("label", ""),
        )
    
    def extract_from_value(self, register_value: int) -> bool:
        """Extract this bit's value from a register value."""
        return bool((register_value >> self.bit_index) & 1)
    
    def apply_to_value(self, register_value: int, bit_value: bool) -> int:
        """Apply this bit's value to a register value, returning new register value."""
        if bit_value:
            return register_value | (1 << self.bit_index)
        else:
            return register_value & ~(1 << self.bit_index)
    
    def copy(self) -> "Bit":
        """Create a copy of this bit."""
        return Bit(
            name=self.name,
            register_address=self.register_address,
            bit_index=self.bit_index,
            slave_id=self.slave_id,
            label=self.label,
        )
