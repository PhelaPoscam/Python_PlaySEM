# PlaySEM Library Documentation

**Version:** 0.1.0  
**Python:** 3.10+

## Overview

PlaySEM is a Python framework for orchestrating sensory effects across multiple devices and protocols. It provides a clean, modular API for device management, effect dispatching, and multi-protocol communication.

### Key Features

- **Protocol-Agnostic**: Support for MQTT, WebSocket, Serial, CoAP, UPnP
- **Device Registry**: Central device management with optional protocol isolation
- **Effect Orchestration**: Route effects to appropriate devices based on capabilities
- **Extensible Drivers**: Easy-to-implement driver interface for new hardware
- **Thread-Safe**: Concurrent access from multiple protocols
- **Well-Tested**: Comprehensive unit test coverage

---

## Installation

### From Source (Development)

```bash
git clone https://github.com/PhelaPoscam/Python_PlaySEM.git
cd Python_PlaySEM
pip install -e .
```

### Dependencies

- **Core**: paho-mqtt, pyyaml, websockets, aiocoap, async-upnp-client
- **Optional**: PyQt6 (for GUI), FastAPI/Uvicorn (for platform server)

---

## Quick Start

### Basic Usage

```python
from playsem import DeviceManager, EffectMetadata
from playsem.config import ConfigLoader

# Initialize device manager
manager = DeviceManager()
await manager.initialize("config/devices.yaml")

# Create and send effect
effect = EffectMetadata(
    effect_type="vibration",
    intensity=80,
    duration=1000
)
await manager.send_effect("device_id", effect)
```

### With Device Registry

```python
from playsem import DeviceRegistry, DeviceManager

# Create registry (shared mode by default)
registry = DeviceRegistry()

# Or enable protocol isolation (like Super Controller Device Simulator)
registry = DeviceRegistry(enable_protocol_isolation=True)

# Register devices from any protocol
registry.register_device({
    "id": "light_001",
    "name": "Smart Light",
    "type": "light",
    "protocols": ["mqtt"],
    "capabilities": ["light", "color"]
}, source_protocol="mqtt")

# Query all devices
all_devices = registry.get_all_devices()

# Query with protocol isolation (if enabled)
mqtt_devices = registry.get_all_devices(requesting_protocol="mqtt")
```

---

## Core Components

### DeviceManager

Manages device lifecycle and effect routing.

```python
from playsem import DeviceManager

manager = DeviceManager()
await manager.initialize("config/devices.yaml")

# Send effect to specific device
await manager.send_effect("device_id", effect)

# Broadcast effect to all devices of a type
await manager.broadcast_effect("light", effect)

# Get connected devices
devices = manager.get_devices()
```

### EffectDispatcher

Routes effects to appropriate devices based on capabilities.

```python
from playsem import EffectDispatcher

dispatcher = EffectDispatcher(device_manager)
await dispatcher.dispatch_effect(effect)
```

### EffectMetadata

Data structure for sensory effects.

```python
from playsem import EffectMetadata

effect = EffectMetadata(
    effect_type="vibration",  # Type: light, vibration, wind, scent, etc.
    intensity=80,             # 0-100
    duration=1000,           # milliseconds
    metadata={               # Additional parameters
        "pattern": "pulse",
        "frequency": 50
    }
)
```

### DeviceRegistry

Central registry for devices across all protocols.

#### Features

- **Shared Mode** (default): All devices visible to all protocols
- **Isolated Mode**: Devices only visible to their source protocol
- **Thread-Safe**: Concurrent access from multiple protocols
- **Event Notifications**: Listen for device changes
- **Multi-Protocol Support**: Devices can support multiple protocols

#### API

```python
from playsem import DeviceRegistry, DeviceInfo

# Create registry
registry = DeviceRegistry(enable_protocol_isolation=False)

# Register device
device = registry.register_device({
    "id": "device_123",
    "name": "My Device",
    "type": "light",
    "address": "192.168.1.100",
    "protocols": ["mqtt", "websocket"],
    "capabilities": ["light", "color"],
    "connection_mode": "isolated",
    "metadata": {"firmware": "1.0"}
}, source_protocol="mqtt")

# Query devices
all_devices = registry.get_all_devices()
all_devices = registry.get_all_devices(requesting_protocol="mqtt")  # With isolation
mqtt_devices = registry.get_devices_by_protocol("mqtt")
lights = registry.get_devices_by_type("light")
color_devices = registry.get_devices_by_capability("color")

# Get specific device
device = registry.get_device("device_123")
device = registry.get_device("device_123", requesting_protocol="mqtt")  # With isolation

# Check/change isolation mode
is_isolated = registry.is_protocol_isolation_enabled()
registry.set_protocol_isolation(True)

# Listen for events
def on_device_event(event_type, device):
    print(f"{event_type}: {device.name}")

registry.add_listener(on_device_event)

# Get statistics
stats = registry.get_stats()
stats = registry.get_stats(requesting_protocol="mqtt")  # With isolation

# Remove device
registry.unregister_device("device_123")

# Clear all
registry.clear()
```

#### Protocol Isolation

**Shared Mode** (default):
- Devices from ANY protocol are visible to ALL protocols
- Use case: Unified device control across protocols

**Isolated Mode**:
- Devices only visible to their source protocol
- MQTT devices → MQTT clients only
- WebSocket devices → WebSocket clients only
- Use case: Protocol-specific device management (like Super Controller Device Simulator)

```python
# Enable isolation
registry = DeviceRegistry(enable_protocol_isolation=True)

# Or toggle at runtime
registry.set_protocol_isolation(True)

# Query with protocol context
mqtt_devices = registry.get_all_devices(requesting_protocol="mqtt")  # Only MQTT devices
ws_devices = registry.get_all_devices(requesting_protocol="websocket")  # Only WS devices
```

---

## Drivers

### Available Drivers

- **SerialDriver**: USB/Serial communication
- **MQTTDriver**: MQTT protocol
- **BluetoothDriver**: Bluetooth LE communication
- **MockConnectivityDriver**: Testing/development

### Creating Custom Drivers

```python
from playsem.drivers import BaseDriver

class MyDriver(BaseDriver):
    async def connect(self):
        # Implement connection logic
        pass
    
    async def disconnect(self):
        # Implement disconnection logic
        pass
    
    async def send_effect(self, effect: EffectMetadata):
        # Implement effect sending
        pass
    
    def is_connected(self) -> bool:
        return self._connected
```

---

## Configuration

### Device Configuration (YAML)

```yaml
devices:
  - id: light_001
    name: Smart Light
    type: light
    driver: mqtt
    address: 192.168.1.100
    capabilities:
      - light
      - color
    connection_mode: isolated

  - id: haptic_001
    name: Haptic Vest
    type: vibration
    driver: serial
    address: COM3
    capabilities:
      - vibration
```

### Loading Configuration

```python
from playsem.config import ConfigLoader

config = ConfigLoader.load("config/devices.yaml")
devices = config["devices"]
```

---

## Examples

### Simple CLI Application

```python
# examples/simple_cli.py
from playsem import DeviceManager, EffectMetadata
from playsem.config import ConfigLoader

async def main():
    manager = DeviceManager()
    
    try:
        config = ConfigLoader.load("config/devices.yaml")
        await manager.initialize(config)
    except FileNotFoundError:
        # Fallback to mock devices
        await manager.add_mock_devices()
    
    # Send test effect
    effect = EffectMetadata(effect_type="vibration", intensity=80)
    await manager.send_effect("device_001", effect)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Device Registry Demo

```python
# examples/device_registry_demo.py
from playsem import DeviceRegistry

registry = DeviceRegistry()

# Register MQTT device
registry.register_device({
    "id": "mqtt_light_001",
    "name": "MQTT Light",
    "type": "light",
    "protocols": ["mqtt"]
}, source_protocol="mqtt")

# Register WebSocket device
registry.register_device({
    "id": "ws_vibration_001",
    "name": "WS Haptic",
    "type": "vibration",
    "protocols": ["websocket"]
}, source_protocol="websocket")

# Query all devices (cross-protocol visibility!)
all_devices = registry.get_all_devices()
print(f"Total devices: {len(all_devices)}")
```

Run examples:
```bash
python examples/simple_cli.py
python examples/device_registry_demo.py
```

---

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_device_registry.py

# With coverage
pytest --cov=playsem

# Verbose
pytest -v
```

### Test Structure

```
tests/
├── test_device_manager.py
├── test_effect_dispatcher.py
├── test_effect_metadata.py
├── test_device_registry.py
└── test_config_loader.py
```

---

## Architecture

### Library Structure

```
playsem/                    # Core library (import this)
├── __init__.py            # Exports: DeviceManager, EffectMetadata, DeviceRegistry
├── device_manager.py      # Device lifecycle management
├── effect_dispatcher.py   # Effect routing
├── effect_metadata.py     # Effect data structure
├── device_registry.py     # Central device registry
├── config/
│   ├── __init__.py
│   └── loader.py         # Configuration loading
└── drivers/
    ├── __init__.py
    ├── base_driver.py    # Driver interface
    ├── serial_driver.py  # Serial/USB communication
    ├── mqtt_driver.py    # MQTT protocol
    ├── bluetooth_driver.py
    └── mock_driver.py    # Testing/development
```

### Platform Components (Optional)

```
examples/                   # Reference implementations
├── simple_cli.py          # Basic usage example
└── device_registry_demo.py

tools/                     # Platform server (optional)
└── test_server/          # Multi-protocol backend server

gui/                       # PyQt6 GUI (optional)
└── app.py                # Graphical interface
```

---

## Migration from Old Structure

### Old Imports (Deprecated)
```python
from src.device_manager import DeviceManager  # ❌
from src.device_driver.mock_driver import MockDriver  # ❌
```

### New Imports
```python
from playsem import DeviceManager, DeviceRegistry  # ✅
from playsem.drivers import MockConnectivityDriver  # ✅
from playsem.config import ConfigLoader  # ✅
```

---

## Refactoring Status

### ✅ Phase 1: Library Extraction (COMPLETE)
- Core modules moved to `playsem/`
- Clean import structure
- Simple examples created

### ✅ Phase 2: Device Registry (COMPLETE)
- Central device storage implemented
- Protocol isolation option added
- Cross-protocol device visibility
- Thread-safe operations
- Event notifications

### ⏳ Phase 3: Platform Refactoring (PLANNED)
- Split monolithic server into modules
- Integrate Device Registry
- Clean architecture

---

## API Reference

### DeviceManager Methods

| Method | Description |
|--------|-------------|
| `initialize(config)` | Load devices from configuration |
| `send_effect(device_id, effect)` | Send effect to specific device |
| `broadcast_effect(device_type, effect)` | Send effect to all devices of type |
| `get_devices()` | Get list of connected devices |
| `add_device(device_config)` | Add device dynamically |
| `remove_device(device_id)` | Remove device |

### DeviceRegistry Methods

| Method | Description |
|--------|-------------|
| `register_device(data, protocol)` | Register device from protocol |
| `unregister_device(device_id)` | Remove device |
| `get_device(device_id, protocol?)` | Get device by ID |
| `get_all_devices(protocol?)` | Get all devices |
| `get_devices_by_protocol(protocol)` | Filter by protocol |
| `get_devices_by_type(type)` | Filter by type |
| `get_devices_by_capability(capability)` | Filter by capability |
| `is_protocol_isolation_enabled()` | Check isolation mode |
| `set_protocol_isolation(enabled)` | Toggle isolation |
| `add_listener(callback)` | Listen for events |
| `get_stats(protocol?)` | Get statistics |

### EffectMetadata Properties

| Property | Type | Description |
|----------|------|-------------|
| `effect_type` | str | Type (light, vibration, wind, etc.) |
| `intensity` | int | 0-100 |
| `duration` | int | Milliseconds |
| `metadata` | dict | Additional parameters |

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'playsem'`

**Solution**: Install in editable mode:
```bash
pip install -e .
```

### Protocol Isolation Not Working

**Problem**: All devices visible when isolation is enabled

**Solution**: Pass `requesting_protocol` parameter:
```python
devices = registry.get_all_devices(requesting_protocol="mqtt")
```

### Device Not Connecting

**Problem**: Device fails to connect

**Solution**:
1. Check device configuration in YAML
2. Verify driver is correct (serial, mqtt, etc.)
3. Check address/port
4. Enable debug logging

---

## Contributing

### Development Setup

```bash
git clone https://github.com/PhelaPoscam/Python_PlaySEM.git
cd Python_PlaySEM
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
pytest --cov=playsem
pytest -v
```

### Code Style

- Black formatting (line length: 79)
- Type hints where applicable
- Docstrings for public APIs

---

## License

MIT License - see LICENSE file for details

## Links

- **Repository**: https://github.com/PhelaPoscam/Python_PlaySEM
- **Issues**: https://github.com/PhelaPoscam/Python_PlaySEM/issues
