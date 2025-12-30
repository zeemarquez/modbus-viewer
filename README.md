# Modbus Viewer

A modern GUI application for reading and writing Modbus RTU registers with real-time table and plot views.

## Features

- **Serial RTU Connection**: Connect to Modbus devices via COM ports
- **Register Configuration**: Define registers with address, size, data type, and scaling expressions
- **Real-time Table View**: Monitor register values with live updates and color-coded changes
- **Real-time Plot View**: Visualize register values over time with configurable time windows
- **Write Support**: Double-click table cells to write values to registers
- **Project Files**: Save and load complete configurations including registers and view settings
- **Expression Scaling**: Apply mathematical expressions to convert raw values (e.g., `(value - 4000) / 16000 * 100`)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Quick Start

1. Select your COM port and configure connection settings
2. Click "Connect" to establish communication
3. Add registers using the Register Editor (Edit menu)
4. Click "Start" to begin polling
5. View data in Table or Plot views
6. Save your configuration with File > Save Project

### Register Configuration

Each register supports:
- **Address**: Modbus register address (0-65535)
- **Size**: Number of 16-bit registers (1, 2, or 4)
- **Label**: Descriptive name
- **Data Type**: uint16, int16, uint32, int32, float32
- **Byte Order**: Big or Little Endian
- **Expression**: Scaling formula using `value` variable
- **Format**: Display as decimal, hex, or binary

### Expression Examples

- Direct value: `value`
- Simple scaling: `value * 0.1`
- Temperature conversion: `value / 10 - 40`
- 4-20mA scaling: `(value - 4000) / 16000 * 100`

## Project File Format

Projects are saved as JSON files containing connection settings, register definitions, and view configurations.

## License

MIT License


