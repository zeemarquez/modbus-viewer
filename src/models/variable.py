"""
Variable data model for computed values from register expressions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict


class VariableFormat(Enum):
    DECIMAL = "decimal"
    FIXED_2 = "fixed_2"
    FIXED_4 = "fixed_4"
    SCIENTIFIC = "scientific"
    PERCENTAGE = "percentage"


@dataclass
class Variable:
    """Represents a computed variable from register expressions."""
    
    name: str
    label: str = ""
    expression: str = ""
    format: VariableFormat = VariableFormat.DECIMAL
    
    # Runtime values (not serialized)
    value: Optional[float] = field(default=None, repr=False)
    error: Optional[str] = field(default=None, repr=False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "label": self.label,
            "expression": self.expression,
            "format": self.format.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Variable":
        """Create Variable from dictionary."""
        return cls(
            name=data["name"],
            label=data.get("label", ""),
            expression=data.get("expression", ""),
            format=VariableFormat(data.get("format", "decimal")),
        )
    
    def format_value(self, value: Optional[float]) -> str:
        """Format value according to display format."""
        if value is None:
            return "---"
        
        try:
            if self.format == VariableFormat.FIXED_2:
                return f"{value:.2f}"
            elif self.format == VariableFormat.FIXED_4:
                return f"{value:.4f}"
            elif self.format == VariableFormat.SCIENTIFIC:
                return f"{value:.4e}"
            elif self.format == VariableFormat.PERCENTAGE:
                return f"{value:.2f}%"
            else:
                # Decimal - show float if not integer
                int_val = int(value)
                if isinstance(value, float) and abs(value - int_val) > 0.0001:
                    return f"{value:.4f}"
                return str(int_val)
        except (ValueError, TypeError):
            return str(value)
    
    def copy(self) -> "Variable":
        """Create a copy of this variable."""
        return Variable(
            name=self.name,
            label=self.label,
            expression=self.expression,
            format=self.format,
        )

