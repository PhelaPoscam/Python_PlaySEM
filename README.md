# PlaySEM - Sensory Effect Media Framework

[![CI](https://github.com/PhelaPoscam/Python_PlaySEM/actions/workflows/ci.yml/badge.svg)](https://github.com/PhelaPoscam/Python_PlaySEM/actions)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)



**PlaySEM** is a Python framework for orchestrating sensory effects across devices and protocols. Build immersive experiences with unified control of lights, haptics, wind, scent, and more.

This is a Python-based implementation and expansion of the original Java PlaySEM framework by [Estevão Bissoli](https://github.com/estevaobissoli).

---

## ✨ Features

- 🔌 **Multi-Protocol Support**: MQTT, WebSocket, Serial, CoAP, UPnP
- 🎯 **Device Registry**: Central management with optional protocol isolation
- 🔄 **Effect Routing**: Automatic effect dispatch based on device capabilities
- 🧩 **Extensible Drivers**: Easy plugin system for new hardware
- 🔒 **Thread-Safe**: Concurrent access from multiple protocols
- 🧪 **Well-Tested**: Comprehensive unit test coverage

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/PhelaPoscam/Python_PlaySEM.git
cd Python_PlaySEM
pip install -e .
```

### Basic Usage

```python
import asyncio
from playsem import DeviceManager, EffectMetadata
from playsem.config import ConfigLoader

async def main():
    # Create config loader (required!)
    config_loader = ConfigLoader(
        devices_path="config/devices.yaml",
        effects_path="config/effects.yaml",
        protocols_path="config/protocols.yaml"
    )
    
    # Initialize manager
    manager = DeviceManager(config_loader=config_loader)
    
    # Send effect
    effect = EffectMetadata(
        effect_type="vibration",
        intensity=80,
        duration=1000
    )
    await manager.send_effect("device_id", effect)

if __name__ == "__main__":
    asyncio.run(main())
```

### Device Registry (Multi-Protocol)

```python
from playsem import DeviceRegistry

# Create registry
registry = DeviceRegistry()

# Register devices from any protocol
registry.register_device({
    "id": "light_001",
    "name": "Smart Light",
    "type": "light",
    "protocols": ["mqtt"]
}, source_protocol="mqtt")

# Query devices (cross-protocol visibility!)
all_devices = registry.get_all_devices()
```

### Protocol Isolation Mode

```python
# Enable isolation (like Super Controller Device Simulator)
registry = DeviceRegistry(enable_protocol_isolation=True)

# Register devices for different protocols
registry.register_device({
    "id": "mqtt_light",
    "name": "MQTT Light",
    "type": "light"
}, source_protocol="mqtt")

registry.register_device({
    "id": "ws_haptic",
    "name": "WebSocket Haptic",
    "type": "haptic"
}, source_protocol="websocket")

# MQTT devices only visible to MQTT clients
mqtt_devices = registry.get_all_devices(requesting_protocol="mqtt")
for device in mqtt_devices:
    print(f"MQTT sees: {device.name} (ID: {device.id})")

# WebSocket devices only visible to WebSocket clients
ws_devices = registry.get_all_devices(requesting_protocol="websocket")
for device in ws_devices:
    print(f"WebSocket sees: {device.name} (ID: {device.id})")
```

---

## 📦 What's Included

### Core Library (`playsem/`)

```python
from playsem import DeviceManager, EffectMetadata, DeviceRegistry
from playsem.drivers import SerialDriver, MQTTDriver
from playsem.config import ConfigLoader
```

- **DeviceManager**: Device lifecycle and effect routing
- **EffectDispatcher**: Effect orchestration
- **DeviceRegistry**: Central device storage (NEW!)
- **Drivers**: Serial, MQTT, Bluetooth, Mock
- **Configuration**: YAML/JSON device config

### Examples

- `examples/simple_cli.py` - Basic usage
- `examples/device_registry_demo.py` - Multi-protocol demo

### Optional Components

- `tools/test_server/` - Multi-protocol backend server
- `gui/` - PyQt6 graphical interface

---

## 📖 Documentation

**Complete Library Documentation**: [`docs/LIBRARY.md`](docs/LIBRARY.md)

| Document | Description |
|----------|-------------|
| [`docs/LIBRARY.md`](docs/LIBRARY.md) | Complete API reference and usage guide |
| [`docs/REFACTORING.md`](docs/REFACTORING.md) | Refactoring progress and migration guide |
| [`docs/guides/quick-start.md`](docs/guides/quick-start.md) | Platform server setup |
| [`docs/guides/devices.md`](docs/guides/devices.md) | Device configuration |

---

## 🎯 Use Cases

### As a Library

```python
# Use PlaySEM in your own projects
from playsem import DeviceManager, DeviceRegistry

# Build your own control system
# Integrate with your application
# Create custom device drivers
```

### As a Platform

```bash
# Run the included platform server (modular)
python examples/platform/basic_server.py

# Or use the GUI
python -m gui.app
```

---

## 🔧 Development

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
pytest --cov=playsem
pytest -v
```

### Run Examples

```bash
python examples/simple_cli.py
python examples/device_registry_demo.py
```

---

## 🏗️ Architecture

### Library Structure

```
playsem/                    # Core library
├── device_manager.py      # Device management
├── effect_dispatcher.py   # Effect routing
├── effect_metadata.py     # Effect data structure
├── device_registry.py     # Central device registry (NEW!)
├── config/               # Configuration loading
└── drivers/              # Hardware drivers
    ├── serial_driver.py
    ├── mqtt_driver.py
    ├── bluetooth_driver.py
    └── mock_driver.py
```

### Optional Platform

```
tools/test_server/         # Multi-protocol server
gui/                       # PyQt6 interface
examples/                  # Usage examples
```

---

## 🌟 What's New

### Version 0.1.0 - Library Release

✅ **Phase 1: Library Extraction**
- Core modules extracted to `playsem/` package
- Clean import structure: `from playsem import ...`
- Installable via `pip install -e .`

✅ **Phase 2: Device Registry**
- Central device storage across all protocols
- **Protocol Isolation Mode**: Optional device visibility control
- Cross-protocol device discovery
- Thread-safe concurrent access
- Event notification system

**Migration Guide**: See [`docs/REFACTORING.md`](docs/REFACTORING.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [contribution guidelines](CONTRIBUTING.md).

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🔗 Links

- **Repository**: https://github.com/PhelaPoscam/Python_PlaySEM
- **Issues**: https://github.com/PhelaPoscam/Python_PlaySEM/issues
- **Original Java PlaySEM**: https://github.com/estevaobissoli/PlaySEM

---

## 🙏 Acknowledgments

- Original PlaySEM framework by [Estevão Bissoli](https://github.com/estevaobissoli)
- Python implementation and extensions by PhelaPoscam

---

## 📊 Project Status

**Current Version**: 0.1.0 (Library Release)

| Component | Status |
|-----------|--------|
| Core Library | ✅ Stable |
| Device Registry | ✅ Complete (with protocol isolation) |
| Serial Driver | ✅ Working |
| MQTT Driver | ✅ Working |
| Bluetooth Driver | ⚠️ Experimental |
| Platform Server | ⚠️ Refactoring (Phase 3) |
| GUI | ✅ Working |
| Documentation | ✅ Complete |

---

<p align="center">
  <strong>Transform your ideas into immersive experiences with PlaySEM! 🎮✨</strong>
</p>
