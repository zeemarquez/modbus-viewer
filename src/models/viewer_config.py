"""
Configuration model for the Modbus Viewer.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ViewerConfig:
    """Modbus Viewer application configuration."""
    
    admin_password: str = "admin123"
    project_path: str = ""  # Path to the exported JSON from Explorer
    
    # Window state
    layout_state: Optional[str] = None
    geometry: Optional[str] = None
    
    # Overrides for connection settings when in viewer mode
    port: str = ""
    baud_rate: int = 9600
    parity: str = "N"
    stop_bits: int = 1
    timeout: float = 1.0
    slave_ids: List[int] = field(default_factory=list)
    hidden_registers: List[str] = field(default_factory=list)  # List of designators
    hidden_columns: List[str] = field(default_factory=list)     # List of column names
    hidden_variables: List[str] = field(default_factory=list)   # List of designators
    hidden_variables_columns: List[str] = field(default_factory=list)
    hidden_bits: List[str] = field(default_factory=list)        # List of designators
    hidden_bits_columns: List[str] = field(default_factory=list)
    
    # Scanning options
    scan_timeout: float = 0.1
    scan_slave_limit: int = 100
    
    def to_dict(self) -> dict:
        return {
            "admin_password": self.admin_password,
            "project_path": self.project_path,
            "port": self.port,
            "baud_rate": self.baud_rate,
            "parity": self.parity,
            "stop_bits": self.stop_bits,
            "timeout": self.timeout,
            "slave_ids": self.slave_ids,
            "hidden_registers": self.hidden_registers,
            "hidden_columns": self.hidden_columns,
            "hidden_variables": self.hidden_variables,
            "hidden_variables_columns": self.hidden_variables_columns,
            "hidden_bits": self.hidden_bits,
            "hidden_bits_columns": self.hidden_bits_columns,
            "scan_timeout": self.scan_timeout,
            "scan_slave_limit": self.scan_slave_limit,
            "layout_state": self.layout_state,
            "geometry": self.geometry,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ViewerConfig":
        return cls(
            admin_password=data.get("admin_password", "admin123"),
            project_path=data.get("project_path", ""),
            port=data.get("port", ""),
            baud_rate=data.get("baud_rate", 9600),
            parity=data.get("parity", "N"),
            stop_bits=data.get("stop_bits", 1),
            timeout=data.get("timeout", 1.0),
            slave_ids=data.get("slave_ids", []),
            hidden_registers=data.get("hidden_registers", []),
            hidden_columns=data.get("hidden_columns", []),
            hidden_variables=data.get("hidden_variables", []),
            hidden_variables_columns=data.get("hidden_variables_columns", []),
            hidden_bits=data.get("hidden_bits", []),
            hidden_bits_columns=data.get("hidden_bits_columns", []),
            scan_timeout=data.get("scan_timeout", 0.1),
            scan_slave_limit=data.get("scan_slave_limit", 100),
            layout_state=data.get("layout_state"),
            geometry=data.get("geometry"),
        )
    
    def save(self, path: str = "viewer_config.json") -> None:
        """Save configuration to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
            
    @classmethod
    def load(cls, path: str = "viewer_config.json") -> "ViewerConfig":
        """Load configuration from JSON file."""
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return cls()
