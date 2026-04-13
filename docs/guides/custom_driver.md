# Custom Driver HOWTO

This guide explains how to implement a custom driver for any hardware device that isn't covered by the built-in drivers (MQTT, Serial, Bluetooth, Mock).

---

## 1. Choose Your Base Class

### Option A: Synchronous Driver (BaseDriver)
Use for drivers that use blocking I/O (e.g., USB Serial, HTTP).

```python
from playsem.drivers.base_driver import BaseDriver
```

### Option B: Asynchronous Driver (AsyncBaseDriver)
Use for drivers that need async/await (e.g., BLE, async HTTP).

```python
from playsem.drivers.base_driver import AsyncBaseDriver
```

---

## 2. Implement the Driver

### Synchronous Example

```python
import logging
from typing import Dict, Any, Optional
from playsem.drivers.base_driver import BaseDriver

logger = logging.getLogger(__name__)

class MyCustomDriver(BaseDriver):
    """Driver for my custom hardware device."""

    def __init__(self, interface_name: str, host: str, port: int = 80):
        self.interface_name = interface_name
        self.host = host
        self.port = port
        self._connected = False

    def connect(self) -> bool:
        """Establish connection to the device."""
        # Your connection logic here
        self._connected = True
        logger.info(f"Connected to {self.host}:{self.port}")
        return True

    def disconnect(self) -> bool:
        """Close connection and cleanup."""
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a command to a specific device."""
        if params is None:
            params = {}
        
        # Your command sending logic
        payload = {"device": device_id, "cmd": command, "params": params}
        # ... send via your protocol
        return True

    def get_interface_name(self) -> str:
        """Unique name matching the config file."""
        return self.interface_name
```

### Asynchronous Example

```python
import asyncio
import logging
from typing import Dict, Any, Optional
from playsem.drivers.base_driver import AsyncBaseDriver

logger = logging.getLogger(__name__)

class MyAsyncDriver(AsyncBaseDriver):
    """Async driver for BLE or async protocol devices."""

    def __init__(self, interface_name: str, address: str):
        self.interface_name = interface_name
        self.address = address
        self._connected = False
        self._client = None

    async def connect(self) -> bool:
        """Async connection establishment."""
        # Your async connection logic
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        """Async disconnect and cleanup."""
        self._connected = False
        return True

    async def is_connected(self) -> bool:
        return self._connected

    async def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Async command sending."""
        # Your async send logic
        return True

    def get_interface_name(self) -> str:
        return self.interface_name
```

---

## 3. Define Device Capabilities

Implement `get_capabilities()` to let the system know what your device supports:

```python
from playsem.device_capabilities import (
    DeviceCapabilities,
    EffectCapability,
    EffectType,
    create_standard_intensity_param,
    create_standard_duration_param,
)

def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
    caps = DeviceCapabilities(
        device_id=device_id,
        device_type="MyDevice",
        manufacturer="MyCompany",
        model="ModelX",
        driver_type="custom",
    )

    # Add supported effects
    caps.effects.append(EffectCapability(
        effect_type=EffectType.VIBRATION,
        description="Custom vibration motor",
        parameters=[
            create_standard_intensity_param(),
            create_standard_duration_param(),
        ],
    ))


    return caps.to_dict()
```

---

## 4. Register in Configuration


Add your driver to the device configuration YAML:

```yaml
connectivityInterfaces:
  - name: my_custom_interface
    type: custom  # or your driver identifier
    driverClass: MyCustomDriver
    config:
      host: "192.168.1.100"
      port: 8080

devices:
  - deviceId: my_device_1
    name: "My Custom Device"
    connectivityInterface: my_custom_interface
```

---

## 5. Initialize in Code

```python
from playsem import DeviceManager

# Option A: Pass driver instance directly
driver = MyCustomDriver(
    interface_name="my_custom_interface",
    host="192.168.1.100",
    port=8080
)

manager = DeviceManager(
    drivers=[driver],
    config_loader=ConfigLoader("config/devices.yaml")
)

# Send effect
from playsem.effect_metadata import EffectMetadata

await manager.send_command(
    device_id="my_device_1",
    command="vibration",
    params={"intensity": 100, "duration": 500}
)

# Or via EffectMetadata + EffectDispatcher
from playsem.effect_dispatcher import EffectDispatcher

effect = EffectMetadata(
    effect_type="vibration",
    intensity=100,
    duration=500
)
dispatcher = EffectDispatcher(manager)
dispatcher.dispatch_effect_metadata(effect)
```

---

## Quick Reference

| Method | Required | Description |
|--------|----------|-------------|
| `connect()` | ✅ | Establish connection |
| `disconnect()` | ✅ | Close connection |
| `send_command()` | ✅ | Send device command |
| `is_connected()` | ✅ | Check status |
| `get_interface_name()` | ✅ | Unique interface ID |
| `get_capabilities()` | ❌ | Device features |
| `get_driver_info()` | ❌ | Driver metadata |

---

## See Also

- [Device Configuration](../guides/devices.md)
- [Base Driver Source Code](../../playsem/drivers/base_driver.py)
- [MQTT Driver Example](../../playsem/drivers/mqtt_driver.py)
