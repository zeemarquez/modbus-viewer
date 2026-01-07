"""
Project configuration model for saving/loading workspace state.
"""

import json
import base64
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from .register import Register
from .variable import Variable
from .bit import Bit


@dataclass
class ConnectionSettings:
    """Serial connection configuration."""
    
    port: str = ""
    slave_ids: List[int] = field(default_factory=lambda: [1])  # List of slave IDs to connect to
    baud_rate: int = 9600
    parity: str = "N"  # N, E, O
    stop_bits: int = 1
    timeout: float = 1.0
    
    # Devices found during last scan (for dropdown population)
    found_devices: List[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "slave_ids": self.slave_ids,
            "baud_rate": self.baud_rate,
            "parity": self.parity,
            "stop_bits": self.stop_bits,
            "timeout": self.timeout,
            "found_devices": self.found_devices,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionSettings":
        # Handle legacy single slave_id field
        slave_ids = data.get("slave_ids", [])
        if not slave_ids and "slave_id" in data:
            slave_ids = [data["slave_id"]]
        if not slave_ids:
            slave_ids = [1]
            
        return cls(
            port=data.get("port", ""),
            slave_ids=slave_ids,
            baud_rate=data.get("baud_rate", 9600),
            parity=data.get("parity", "N"),
            stop_bits=data.get("stop_bits", 1),
            timeout=data.get("timeout", 1.0),
            found_devices=data.get("found_devices", []),
        )


@dataclass
class PlotOptions:
    """Plot appearance and behavior options."""
    
    line_width: float = 2.0
    grid_alpha: float = 0.1
    show_legend: bool = True
    time_window_index: int = 4  # Index in time window combo (0=1s, 1=5s, 2=10s, 3=30s, 4=1min, 5=2min, 6=5min)
    y_auto_scale: bool = True
    y_min: float = 0.0
    y_max: float = 100.0
    
    def to_dict(self) -> dict:
        return {
            "line_width": self.line_width,
            "grid_alpha": self.grid_alpha,
            "show_legend": self.show_legend,
            "time_window_index": self.time_window_index,
            "y_auto_scale": self.y_auto_scale,
            "y_min": self.y_min,
            "y_max": self.y_max,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlotOptions":
        return cls(
            line_width=data.get("line_width", 2.0),
            grid_alpha=data.get("grid_alpha", 0.1),
            show_legend=data.get("show_legend", True),
            time_window_index=data.get("time_window_index", 4),
            y_auto_scale=data.get("y_auto_scale", True),
            y_min=data.get("y_min", 0.0),
            y_max=data.get("y_max", 100.0),
        )


@dataclass
class ViewSettings:
    """View configuration for plots and display options."""
    
    plot_registers: List[str] = field(default_factory=list)  # Designators like "D1.R0"
    plot_variables: List[str] = field(default_factory=list)  # Variable names
    plot_time_window: int = 60  # seconds (deprecated, use plot_options.time_window_index)
    poll_interval: int = 100  # milliseconds
    plot_options: PlotOptions = field(default_factory=PlotOptions)
    
    def to_dict(self) -> dict:
        return {
            "plot_registers": self.plot_registers,
            "plot_variables": self.plot_variables,
            "plot_time_window": self.plot_time_window,
            "poll_interval": self.poll_interval,
            "plot_options": self.plot_options.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ViewSettings":
        # Handle legacy plot_registers format (list of ints)
        plot_registers = data.get("plot_registers", [])
        if plot_registers and isinstance(plot_registers[0], int):
            # Convert old format (address only) to new format (D1.R<addr>)
            plot_registers = [f"D1.R{addr}" for addr in plot_registers]
        
        return cls(
            plot_registers=plot_registers,
            plot_variables=data.get("plot_variables", []),
            plot_time_window=data.get("plot_time_window", 60),
            poll_interval=data.get("poll_interval", 100),
            plot_options=PlotOptions.from_dict(data.get("plot_options", {})),
        )


@dataclass
class Project:
    """Complete project configuration."""
    
    version: str = "2.0"  # Updated version for multi-device support
    connection: ConnectionSettings = field(default_factory=ConnectionSettings)
    registers: List[Register] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    bits: List[Bit] = field(default_factory=list)
    views: ViewSettings = field(default_factory=ViewSettings)
    layout_state: Optional[bytes] = field(default=None, repr=False)  # QByteArray as bytes
    file_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = {
            "version": self.version,
            "connection": self.connection.to_dict(),
            "registers": [r.to_dict() for r in self.registers],
            "variables": [v.to_dict() for v in self.variables],
            "bits": [b.to_dict() for b in self.bits],
            "views": self.views.to_dict(),
        }
        
        # Encode layout state as base64 if present
        if self.layout_state:
            result["layout_state"] = base64.b64encode(self.layout_state).decode('utf-8')
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        project = cls(
            version=data.get("version", "1.0"),
            connection=ConnectionSettings.from_dict(data.get("connection", {})),
            registers=[Register.from_dict(r) for r in data.get("registers", [])],
            variables=[Variable.from_dict(v) for v in data.get("variables", [])],
            bits=[Bit.from_dict(b) for b in data.get("bits", [])],
            views=ViewSettings.from_dict(data.get("views", {})),
        )
        
        # Decode layout state from base64 if present
        if "layout_state" in data:
            try:
                project.layout_state = base64.b64decode(data["layout_state"])
            except Exception:
                project.layout_state = None
        
        return project
    
    def save(self, file_path: Optional[str] = None) -> None:
        """Save project to JSON file."""
        path = file_path or self.file_path
        if not path:
            raise ValueError("No file path specified")
        
        self.file_path = path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> "Project":
        """Load project from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        project = cls.from_dict(data)
        project.file_path = file_path
        return project
    
    def get_register_by_designator(self, designator: str) -> Optional[Register]:
        """Find register definition by designator (e.g., D1.R13)."""
        # For common definitions, we just need to match the address part
        if ".R" in designator:
            try:
                addr = int(designator.split(".R")[1])
                for reg in self.registers:
                    if reg.address == addr:
                        return reg
            except (ValueError, IndexError):
                pass
        return None
    
    def get_register(self, address: int) -> Optional[Register]:
        """Find register definition by address."""
        for reg in self.registers:
            if reg.address == address:
                return reg
        return None
    
    @property
    def name(self) -> str:
        """Get project name from file path."""
        if self.file_path:
            return Path(self.file_path).stem
        return "Untitled"
