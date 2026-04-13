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
| -------- | -------- | -------- |
| `connect()` | ✅ | Establish connection |
| `disconnect()` | ✅ | Close connection |
| `send_command()` | ✅ | Send device command |
| `is_connected()` | ✅ | Check status |
| `get_interface_name()` | ✅ | Unique interface ID |
| `get_capabilities()` | ❌ | Device features |
| `get_driver_info()` | ❌ | Driver metadata |

---

## See Also

- [Core Usage Guide](../guides/core_guide.md)
- [Base Driver Source Code](../../playsem/drivers/base_driver.py)
- [MQTT Driver Example](../../playsem/drivers/mqtt_driver.py)

---

## 6. Add Resilience Hooks (Recommended)

Production drivers should include retry/reconnect behavior and telemetry.

### For Sync Drivers

Use `RetryPolicy` and retry in `connect()`:

```python
from playsem.drivers.retry_policy import RetryPolicy

class MyCustomDriver(BaseDriver):
    def __init__(self, interface_name: str, host: str):
        self.interface_name = interface_name
        self.host = host
        self._connected = False
        self.retry_policy = RetryPolicy(max_attempts=3, initial_delay=0.5)
        self._reconnect_attempts = 0
        self._last_reconnect_error = None

    def connect(self) -> bool:
        delays = self.retry_policy.delays()
        max_attempts = max(1, self.retry_policy.max_attempts)
        for attempt in range(1, max_attempts + 1):
            self._reconnect_attempts = attempt
            try:
                # real connect call
                self._connected = True
                self._last_reconnect_error = None
                return True
            except Exception as exc:
                self._last_reconnect_error = str(exc)
                if attempt < max_attempts and delays:
                    import time
                    time.sleep(delays[attempt - 1])
        return False
```

### For Async Drivers

Use bounded reconnect loops and avoid unbounded retries:

```python
async def connect(self) -> bool:
    delays = self.retry_policy.delays()
    max_attempts = max(1, self.retry_policy.max_attempts)
    for attempt in range(1, max_attempts + 1):
        try:
            await self._client.connect()
            return True
        except Exception:
            if attempt < max_attempts and delays:
                await asyncio.sleep(delays[attempt - 1])
    return False
```

---

## 7. Capability Contract and Validation

To support safe dispatch validation, return a standard capability payload from
`get_capabilities()` and keep parameter schemas explicit.

Dispatcher-side validation can be enabled with:

```python
dispatcher = EffectDispatcher(
    manager,
    validate_capabilities=True,
)
```

When enabled, invalid parameters are rejected before `send_command()`.

Recommended rules:

1. Include `device_id`, `device_type`, `driver_type`, and `effects` keys.
2. For each effect, define `effect_type` and explicit `parameters`.
3. Define `required`, `min_value`, `max_value`, and `enum_values` where needed.

---

## 8. Async Bridge Compatibility

`DeviceManager` is synchronous but supports async drivers via an internal bridge.

For single-driver mode:

```python
manager = DeviceManager(
    connectivity_driver=my_async_driver,
    async_bridge_timeout=5.0,
)
```

For mapped multi-driver mode, async `is_connected()`, `connect()`,
`disconnect()`, and `send_command()` are bridged automatically.

If your async driver has long operations, set a suitable
`async_bridge_timeout` and fail fast on hangs.

---

## 9. Managed Queue Integration (Optional)

If using queued effect dispatch (`managed_mode=True`), make sure one runtime
path drains the queue:

1. `Timeline(..., process_managed_queue=True)`
2. `WebSocketServer(..., process_managed_queue=True)`

Without queue processing, effects will be enqueued but not dispatched.
