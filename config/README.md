# Configuration Files

This directory contains YAML configuration files for PlaySEM device management and effects.

## Files

- **devices.yaml** — Device registry and driver configuration
- **effects.yaml** — Effect mappings and parameter definitions

## Usage

These configs are loaded by:

- `playsem.config.loader.ConfigLoader`
- `playsem.device_manager.DeviceManager`
- `playsem.effect_dispatcher.EffectDispatcher`

Example:

```python
from playsem.config.loader import ConfigLoader

loader = ConfigLoader(
    devices_path="config/devices.yaml",
    effects_path="config/effects.yaml"
)
```
