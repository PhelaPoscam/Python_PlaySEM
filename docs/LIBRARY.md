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

### From Source

```bash
# Minimal installation (core only)
pip install -e .

# Full installation (all protocols: MQTT, Bluetooth, CoAP, etc.)
pip install -e ".[all]"
```

### Protocol-Specific Installation

If you only need specific protocols, you can install them individually:

```bash
pip install -e ".[mqtt]"      # MQTT support
pip install -e ".[coap]"      # CoAP support
pip install -e ".[upnp]"      # UPnP support
pip install -e ".[bluetooth]" # Bluetooth LE support
pip install -e ".[serial]"    # Serial/Arduino support
pip install -e ".[websocket]" # WebSocket server
pip install -e ".[server]"    # REST API / Platform Server
```

### Dependencies

- **Core**: pyyaml, numpy, aiohttp
- **Optional**: See "Protocol-Specific Installation" above.

---

## Quick Start

### Basic Usage

```python
from playsem import DeviceManager, EffectMetadata
from playsem.config import ConfigLoader

# Initialize configuration loader
loader = ConfigLoader(
    devices_path="config/devices.yaml",
    effects_path="config/effects.yaml"
)

# Initialize device manager
manager = DeviceManager(config_loader=loader)
await manager.start_async_workers()

# Create the EffectDispatcher
dispatcher = EffectDispatcher(device_manager=manager)

# Create effect
effect = EffectMetadata(
    effect_type="vibration",
    intensity=80,
    duration=1000
)

# Dispatch asynchronously
result = await dispatcher.async_dispatch_effect_metadata_result(effect)
print(f"Dispatch status: {result.status} (Accepted: {result.accepted})")

# Cleanup when done
await manager.stop_async_workers()
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

Manages device lifecycle and routes commands to concrete driver instances.

```python
from playsem import DeviceManager
from playsem.config.loader import ConfigLoader

loader = ConfigLoader(devices_path="config/devices.yaml")
manager = DeviceManager(config_loader=loader)

# Send command to specific device (sync)
success = manager.send_command(
    device_id="device_123",
    command="vibration",
    params={"intensity": 80, "duration": 1000}
)

# Send command to specific device asynchronously
success = await manager.async_send_command(
    device_id="device_123",
    command="vibration",
    params={"intensity": 80, "duration": 1000}
)
```

### EffectDispatcher

Routes effects to appropriate devices based on capabilities, resolving parameter mappings (e.g. from intensity/duration values) dynamically.

```python
from playsem import EffectDispatcher
from playsem.effect_metadata import EffectMetadata

dispatcher = EffectDispatcher(device_manager)

# Dispatch effect using EffectMetadata object (async)
success = await dispatcher.async_dispatch_effect_metadata(effect)

# Or dispatch by effect name and parameters (async)
success = await dispatcher.async_dispatch_effect(
    "vibration",
    {"intensity": 80, "duration": 1000}
)
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

## API Reference

### DeviceManager Methods

| Method | Description |
| :-- | :-- |
| `__init__(drivers, config_loader, ...)` | Initialize manager with optional drivers and config loader |
| `send_command(device_id, command, params)` | Send command to specific device (sync) |
| `async_send_command(device_id, command, params)` | Send command to specific device (async) |
| `connect_all()` | Connect all driver instances |
| `async_connect_all()` | Connect all driver instances (async) |
| `disconnect_all()` | Disconnect all driver instances |
| `async_disconnect_all()` | Disconnect all driver instances (async) |
| `start_async_workers()` | Start background async worker tasks for per-device queues |
| `stop_async_workers()` | Stop background async worker tasks |
| `get_device_capabilities(device_id)` | Get capabilities dictionary for device |
| `get_device_info(device_id)` | Get configuration dictionary for device |
| `discover_all_devices()` | Discover devices across registered scanners |

### DeviceRegistry Methods

| Method | Description |
| :-- | :-- |
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
| :-- | :-- | :-- |
| `effect_type` | str | Type (light, vibration, wind, etc.) |
| `intensity` | int | 0-100 |
| `duration` | int | Milliseconds |
| `metadata` | dict | Additional parameters |

---

For runnable examples, see [examples/README.md](../examples/README.md).
