# Framework Refactoring Plan

**Goal**: Transform PythonPlaySEM from a monolithic application into a clean, importable library (`playsem`) while keeping the platform capabilities as examples.

**Decision**: Framework-first approach (Option A), with integrated platform built on top later.

---

## Why This Refactoring?

### Current Issues:
1. **Unclear purpose**: Is it a library? An app? A platform?
2. **Protocol isolation**: MQTT devices invisible to WebSocket clients
3. **Test server bloat**: 2138 lines in single file
4. **Hard to reuse**: Can't easily use core logic in other projects
5. **Mixed concerns**: Device management tied to server implementation

### After Refactoring:
✅ Clear library: `pip install playsem`
✅ Shared device registry across all protocols
✅ Modular server components
✅ Easy to test and extend
✅ Platform becomes "batteries-included example"

---

## New Structure

```
PythonPlaySEM/
├── playsem/                    # 🆕 Core library (importable)
│   ├── __init__.py
│   ├── device_manager.py       # Moved from src/
│   ├── effect_dispatcher.py    # Moved from src/
│   ├── effect_metadata.py      # Moved from src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py           # Moved from src/config_loader.py
│   └── drivers/
│       ├── __init__.py
│       ├── base_driver.py      # Moved from src/device_driver/
│       ├── serial_driver.py
│       ├── mqtt_driver.py
│       ├── bluetooth_driver.py
│       └── mock_driver.py
│
├── examples/                   # Reference implementations
│   ├── simple_cli.py          # Basic CLI using playsem
│   ├── basic_server/          # Minimal WebSocket server
│   │   ├── app.py
│   │   └── README.md
│   ├── platform/              # 🔄 Rename from tools/test_server
│   │   ├── app.py             # Main FastAPI app
│   │   ├── handlers/
│   │   │   ├── websocket.py   # Split from main.py
│   │   │   ├── mqtt.py
│   │   │   ├── http.py
│   │   │   └── coap.py
│   │   ├── device_registry.py # 🆕 Central device storage
│   │   └── README.md
│   └── gui_client/            # 🔄 Rename from gui/
│       └── ...
│
├── src/                       # ⚠️ Deprecated (kept for backwards compat)
├── gui/                       # ⚠️ Deprecated
├── tools/                     # ⚠️ Deprecated
│
├── tests/
│   ├── unit/                  # Test playsem library
│   └── integration/           # Test examples
│
├── docs/
│   ├── library/              # 🆕 Library API documentation
│   ├── examples/             # 🆕 Example usage guides
│   └── ... (existing docs)
│
├── setup.py                  # 🆕 Make installable
├── pyproject.toml           # 🆕 Modern packaging
└── README.md                # 🔄 Update to library-first
```

---

## Migration Phases

### ✅ Phase 1: Create Library Structure (CURRENT)

**Status**: In Progress

**Tasks**:
- [x] Create `playsem/` directory
- [x] Create `playsem/__init__.py` with core exports
- [x] Create `playsem/drivers/__init__.py`
- [ ] Copy and refactor core modules from `src/` to `playsem/`
  - [ ] `device_manager.py`
  - [ ] `effect_dispatcher.py`
  - [ ] `effect_metadata.py`
  - [ ] `config/loader.py` (from `config_loader.py`)
  - [ ] All drivers from `device_driver/`
- [ ] Remove protocol-specific code from core
- [ ] Add proper `__init__.py` exports
- [ ] Create `setup.py` for pip installation

**Testing**:
```python
# Should work after Phase 1:
from playsem import DeviceManager, EffectMetadata
from playsem.drivers import SerialDriver, MockDriver
```

---

### Phase 2: Create Device Registry

**Purpose**: Central device storage shared across ALL protocols

**File**: `examples/platform/device_registry.py`

```python
class DeviceRegistry:
    """
    Central registry for all devices, regardless of connection protocol.
    
    Features:
    - Protocol-agnostic storage
    - Query devices by any criteria
    - Emit events on device changes
    - Thread-safe operations
    """
    
    def register_device(self, device_info: dict, source_protocol: str):
        """Register device from any protocol"""
        
    def get_all_devices(self) -> list:
        """Get all devices regardless of protocol"""
        
    def get_devices_by_protocol(self, protocol: str) -> list:
        """Filter devices by connection protocol"""
```

**Key Fix**: MQTT device announcements go to registry → visible to ALL protocols

---

### Phase 3: Refactor Platform Server

**Split** `tools/test_server/main.py` (2138 lines) into:

```
examples/platform/
├── app.py                    # FastAPI setup + routes
├── device_registry.py        # Shared device state
├── handlers/
│   ├── websocket_handler.py  # WebSocket logic
│   ├── mqtt_handler.py       # MQTT broker integration
│   ├── http_handler.py       # REST endpoints
│   └── coap_handler.py       # CoAP server
└── protocol_servers/
    ├── mqtt_server.py        # Embedded MQTT broker
    ├── coap_server.py        # CoAP server
    └── upnp_server.py        # UPnP discovery
```

**Benefits**:
- Each file < 300 lines
- Easy to test individual protocols
- Can enable/disable protocols via config
- Shared device registry fixes isolation issue

---

### Phase 4: Simplify GUI Client

**Move** `gui/` → `examples/gui_client/`

**Simplify**:
- GUI ONLY connects via WebSocket (remove multi-protocol complexity)
- Backend handles protocol translation
- Simpler, more maintainable

**Reasoning**:
- End users don't need to choose protocols
- Backend is the protocol hub
- GUI is just another client

---

### Phase 5: Create Simple Examples

**File**: `examples/simple_cli.py`
```python
"""Minimal example using playsem library"""
import asyncio
from playsem import DeviceManager, EffectMetadata

async def main():
    # Initialize with config
    manager = DeviceManager()
    await manager.initialize("config/devices.yaml")
    
    # Send effect
    effect = EffectMetadata(
        effect_type="vibration",
        intensity=80,
        duration=1000
    )
    await manager.send_effect("my_device", effect)

if __name__ == "__main__":
    asyncio.run(main())
```

**File**: `examples/basic_server/app.py`
```python
"""Minimal WebSocket server example"""
from fastapi import FastAPI, WebSocket
from playsem import DeviceManager

app = FastAPI()
manager = DeviceManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Simple server in <50 lines
    pass
```

---

### Phase 6: Documentation & Packaging

**Tasks**:
- [ ] API documentation for `playsem` library
- [ ] Migration guide for existing users
- [ ] Example galleries
- [ ] Create `setup.py` / `pyproject.toml`
- [ ] Publish to PyPI (optional)

**README Structure**:
```markdown
# PythonPlaySEM

**A Python framework for sensory effect devices**

## Quick Start (Library)

```python
pip install playsem

from playsem import DeviceManager, EffectMetadata
# ... usage
```

## Quick Start (Platform)

```bash
git clone ...
python examples/platform/app.py
```

## Examples

- [Simple CLI](examples/simple_cli.py)
- [WebSocket Server](examples/basic_server/)
- [Full Platform](examples/platform/)
- [GUI Client](examples/gui_client/)
```

---

## Backwards Compatibility

### Deprecated Structure (Keep for Now)
```
src/          # ⚠️ Import from playsem instead
gui/          # ⚠️ Use examples/gui_client
tools/        # ⚠️ Use examples/platform
```

### Migration Path for Users

**Old way**:
```python
from src.device_manager import DeviceManager  # Deprecated
```

**New way**:
```python
from playsem import DeviceManager  # Clean!
```

---

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Clarity** | "What is this project?" | "It's a framework" |
| **Reusability** | Copy src/ folder | `pip install playsem` |
| **Testing** | Test entire platform | Test library separately |
| **Protocol Isolation** | MQTT ≠ WebSocket devices | All devices shared |
| **Server Complexity** | 2138-line file | Modular <300 lines each |
| **GUI Complexity** | Multi-protocol client | Simple WebSocket client |
| **Maintenance** | Monolithic | Separated concerns |

---

## Current Status

**Phase 1**: ✅ In Progress
- Created `playsem/` structure
- Next: Copy and refactor core modules

**Timeline**:
- Phase 1-2: Foundation (1-2 days)
- Phase 3-4: Refactor existing (2-3 days)
- Phase 5-6: Polish & docs (1-2 days)

**Total**: ~1 week of focused work

---

## Questions to Answer

1. **Versioning**: Start at 0.1.0 or 1.0.0?
2. **PyPI**: Publish library publicly?
3. **Deprecation**: Remove old structure immediately or keep for transition?
4. **Examples**: Which examples to include in repo vs docs?

---

**Next Steps**: Continue Phase 1 - copy core modules to `playsem/` with cleaned imports.
