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
    
    # Plot settings
    plot_registers: List[str] = field(default_factory=list)
    plot_variables: List[str] = field(default_factory=list)
    plot_line_width: float = 2.0
    plot_grid_alpha: float = 0.1
    plot_show_legend: bool = True
    plot_time_window_index: int = 4
    plot_y_auto_scale: bool = True
    plot_y_min: float = 0.0
    plot_y_max: float = 100.0
    
    # Custom Panels
    text_panels: List[dict] = field(default_factory=list)
    image_panels: List[dict] = field(default_factory=list)
    
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
            "plot_registers": self.plot_registers,
            "plot_variables": self.plot_variables,
            "plot_line_width": self.plot_line_width,
            "plot_grid_alpha": self.plot_grid_alpha,
            "plot_show_legend": self.plot_show_legend,
            "plot_time_window_index": self.plot_time_window_index,
            "plot_y_auto_scale": self.plot_y_auto_scale,
            "plot_y_min": self.plot_y_min,
            "plot_y_max": self.plot_y_max,
            "text_panels": self.text_panels,
            "image_panels": self.image_panels,
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
            plot_registers=data.get("plot_registers", []),
            plot_variables=data.get("plot_variables", []),
            plot_line_width=data.get("plot_line_width", 2.0),
            plot_grid_alpha=data.get("plot_grid_alpha", 0.1),
            plot_show_legend=data.get("plot_show_legend", True),
            plot_time_window_index=data.get("plot_time_window_index", 4),
            plot_y_auto_scale=data.get("plot_y_auto_scale", True),
            plot_y_min=data.get("plot_y_min", 0.0),
            plot_y_max=data.get("plot_y_max", 100.0),
            text_panels=data.get("text_panels", []),
            image_panels=data.get("image_panels", []),
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
