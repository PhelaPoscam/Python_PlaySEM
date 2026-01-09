# Configuration Files

This directory contains YAML configuration files for PlaySEM device management and effects.

## Files

- **devices.yaml** - Device registry and driver configuration
- **effects.yaml** - Effect mappings and parameter definitions
- **protocols.yaml** - Protocol server configuration

## Usage

These configs are loaded by:
- `playsem.config_loader.ConfigLoader`
- `playsem.device_manager.DeviceManager`
- `playsem.effect_dispatcher.EffectDispatcher`

Example:
```python
from playsem import DeviceManager

manager = DeviceManager()
await manager.initialize("config/devices.yaml")
```

## Location

**Kept in root** (`config/`) for:
- Easy discovery
- Consistent with all documentation
- Widely referenced in codebase (20+ locations)

Alternative `.config/` was considered but rejected to maintain backward compatibility.

## See Also

- [Device Configuration Guide](../docs/guides/devices.md)
- [Architecture Reference](../docs/reference/architecture.md)
