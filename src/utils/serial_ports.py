"""
Serial port detection utilities.
"""

import serial.tools.list_ports
from typing import List, Tuple


def get_available_ports() -> List[Tuple[str, str]]:
    """
    Get list of available serial ports.
    
    Returns:
        List of tuples (port_name, description)
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        description = port.description or port.device
        ports.append((port.device, description))
    
    # Sort by port name
    ports.sort(key=lambda x: x[0])
    return ports


def get_port_names() -> List[str]:
    """Get just the port names."""
    return [port[0] for port in get_available_ports()]






