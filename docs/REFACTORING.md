# ⚠️ Migration Guide - Legacy `src/` to `playsem/`

**Status**: DEPRECATED - Only needed if migrating old code from `src/` directory  
**Last Updated**: December 2025  
**For New Users**: Start with [LIBRARY.md](LIBRARY.md) instead

---

# PlaySEM Library - Quick Start

## What Changed?

PlaySEM is now organized as a **clean, importable library** (`playsem/`) with the platform and tools as examples.

### New Structure:

```
playsem/              # 🆕 Core library (import this!)
├── device_manager.py
├── effect_dispatcher.py
├── effect_metadata.py
├── config/
└── drivers/

examples/             # Reference implementations
├── simple_cli.py     # 🆕 Basic usage example
└── ... (more to come)

src/                  # ⚠️ Old structure (still works, but deprecated)
```

## Using the Library

### Import and Use:

```python
from playsem import DeviceManager, EffectMetadata, DeviceRegistry
from playsem.drivers import MockDriver, SerialDriver

# Initialize device registry (for multi-protocol support)
registry = DeviceRegistry()

# Initialize device manager
manager = DeviceManager()
await manager.initialize("config/devices.yaml")

# Send effect
effect = EffectMetadata(effect_type="vibration", intensity=80)
await manager.send_effect("device_id", effect)
```

### Run Examples:

```bash
# Basic usage
python examples/simple_cli.py

# Device Registry demo (cross-protocol device discovery)
python examples/device_registry_demo.py
```

## Migration Guide

### Old Way (Deprecated):
```python
from src.device_manager import DeviceManager  # ❌ Deprecated
from src.device_driver.mock_driver import MockDriver  # ❌ Deprecated
```

### New Way:
```python
from playsem import DeviceManager  # ✅ Clean!
from playsem.drivers import MockDriver  # ✅ Organized!
```

## What's Next?

**Phase 1**: Library extraction ✅ COMPLETE
- Core modules moved to `playsem/`
- Clean imports and structure
- Simple example created

**Phase 2**: Device Registry ✅ COMPLETE
- Central device storage implemented
- Protocol isolation FIXED
- Cross-protocol device visibility
- See: `docs/development/PHASE_2_DEVICE_REGISTRY.md`

**Phase 3** (Next): Refactor Platform Server
- Split `tools/test_server/main.py` into modules
- Move to `examples/platform/`
- Integrate device registry

See `docs/development/REFACTORING_PLAN.md` for full roadmap.

## Benefits

✅ **Importable**: Use PlaySEM in your own projects
✅ **Modular**: Take only what you need
✅ **Testable**: Test library independent of platform
✅ **Clear Purpose**: Framework first, platform as example
✅ **Future-Proof**: Can publish to PyPI later

## Questions?

See the full refactoring plan: `docs/development/REFACTORING_PLAN.md`
