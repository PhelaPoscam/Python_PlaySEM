# Phase 3A: Main.py Refactoring Analysis

**File**: `tools/test_server/main.py`  
**Size**: 2138 lines (note: was counted as 1879 earlier, actual is 2138)  
**Status**: Ready to refactor

---

## 📊 Current Structure Analysis

### Main Components

#### 1. **Data Model**
```python
@dataclass
class ConnectedDevice:
    - id, name, type, address
    - driver, manager, dispatcher
    - connected_at (timestamp)
```

#### 2. **ControlPanelServer Class** (Main class, everything here!)

**Initialization** (`__init__`):
- FastAPI app setup
- Devices dict storage
- WebSocket clients tracking
- Stats tracking
- Route setup

**Core Methods** (44 methods total):

**Lifecycle**:
- `_shutdown()` - Cleanup
- `run()` - Start server
- `signal_handler()` - Shutdown signal

**Route Setup**:
- `_setup_routes()` - Defines ALL API routes

**WebSocket/Connection Management**:
- `handle_client()` - Main WebSocket handler
- `handle_super_controller_message()` - Controller-specific
- `register_web_device()` - HTTP device registration
- `unregister_web_device()` - HTTP device deregistration
- `broadcast_device_list()` - Send device list to clients

**Device Discovery**:
- `scan_devices()` - Start device scan
- `scan_bluetooth()` - Scan for BLE devices
- `scan_serial()` - Scan for serial ports
- `scan_mock()` - Create mock devices

**Device Management**:
- `connect_device()` - Connect to device
- `disconnect_device()` - Disconnect device
- `announce_device_discovery()` - Broadcast device found
- `send_device_list()` - HTTP endpoint for devices

**Effect/Timeline Processing**:
- `send_effect()` - Main effect dispatch
- `send_effect_protocol()` - Protocol-specific send
- `_broadcast_effect()` - Broadcast effect result
- `_on_timeline_effect()` - Timeline callback
- `_on_timeline_complete()` - Timeline callback
- `_broadcast_timeline_effect()` - Send timeline effect
- `_broadcast_timeline_status()` - Send timeline status

**Timeline Management**:
- `handle_timeline_upload()` - Upload timeline file
- `pause_timeline()` - Pause playback
- `resume_timeline()` - Resume playback
- `stop_timeline()` - Stop playback
- `get_timeline_status()` - Get timeline status

**Protocol Servers**:
- `start_protocol_server()` - Start MQTT/CoAP/etc
- `stop_protocol_server()` - Stop protocol server

**Message Handling**:
- `handle_message()` - Main message router
- `_setup_routes()` - Define all HTTP routes

---

## 🎯 Proposed Module Architecture

### New Structure

```
tools/test_server/
├── __init__.py
├── main.py                    ← Entry point (minimal)
├── config.py                  ← Configuration
├── server.py                  ← FastAPI + server orchestration
├── models.py                  ← Data models (ConnectedDevice, etc.)
├── handlers/
│   ├── __init__.py
│   ├── websocket_handler.py   ← WebSocket logic
│   ├── http_handler.py        ← HTTP REST endpoints
│   └── device_handler.py      ← Device-specific logic
├── services/
│   ├── __init__.py
│   ├── device_service.py      ← Device connect/disconnect/scan
│   ├── effect_service.py      ← Effect dispatch
│   ├── timeline_service.py    ← Timeline management
│   └── protocol_service.py    ← Protocol server management
├── protocols/
│   ├── __init__.py
│   ├── scanner.py             ← Device discovery
│   ├── drivers.py             ← Driver initialization
│   └── effects.py             ← Effect routing
└── routes/
    ├── __init__.py
    ├── devices.py             ← Device endpoints
    ├── effects.py             ← Effect endpoints
    ├── health.py              ← Health check
    └── ui.py                  ← UI serving
```

---

## 📋 Refactoring Tasks

### Task 1: Create `models.py`
**Extract**: `ConnectedDevice` dataclass
**Lines**: ~10
**Purpose**: Centralize data models

### Task 2: Create `config.py`
**Extract**: Configuration constants
**Add**: Settings management
**Lines**: ~30
**Purpose**: Configuration centralization

### Task 3: Create `services/device_service.py`
**Extract from**: `scan_bluetooth()`, `scan_serial()`, `scan_mock()`, `connect_device()`, `disconnect_device()`, `send_device_list()`
**Lines**: ~200
**Purpose**: Device lifecycle management

### Task 4: Create `services/effect_service.py`
**Extract from**: `send_effect()`, `send_effect_protocol()`, `_broadcast_effect()`
**Lines**: ~150
**Purpose**: Effect dispatch logic

### Task 5: Create `services/timeline_service.py`
**Extract from**: `handle_timeline_upload()`, `pause_timeline()`, `resume_timeline()`, `stop_timeline()`, `get_timeline_status()`, timeline callbacks
**Lines**: ~100
**Purpose**: Timeline management

### Task 6: Create `services/protocol_service.py`
**Extract from**: `start_protocol_server()`, `stop_protocol_server()`
**Lines**: ~50
**Purpose**: Protocol server lifecycle

### Task 7: Create `handlers/websocket_handler.py`
**Extract from**: `handle_client()`, `handle_super_controller_message()`, `handle_message()`, broadcasting methods
**Lines**: ~150
**Purpose**: WebSocket protocol handling

### Task 8: Create `handlers/device_handler.py`
**Extract from**: `register_web_device()`, `unregister_web_device()`, `announce_device_discovery()`, `broadcast_device_list()`
**Lines**: ~80
**Purpose**: Device registration/announcement

### Task 9: Create `routes/devices.py`
**Extract from**: Device-related HTTP endpoints
**Lines**: ~50
**Purpose**: Device API endpoints

### Task 10: Create `routes/effects.py`
**Extract from**: Effect-related HTTP endpoints
**Lines**: ~50
**Purpose**: Effect API endpoints

### Task 11: Create `routes/ui.py`
**Extract from**: UI serving routes (controller, receiver, mobile_device)
**Lines**: ~50
**Purpose**: Static UI serving

### Task 12: Create `server.py`
**Extract from**: FastAPI setup, route registration, initialization
**Lines**: ~100
**Purpose**: Main server orchestrator

### Task 13: Create new `main.py`
**New**: Simple entry point
**Lines**: ~20
**Purpose**: Clean CLI entry point

### Task 14: Update all imports
**Action**: Change `from src.X import Y` → `from playsem import Y`
**Files**: All 13 new modules
**Priority**: HIGH

### Task 15: Add tests
**New**: Unit tests for each new module
**Lines**: ~200
**Purpose**: Verify refactoring works

---

## 📊 Expected Results

**Before**:
- 1 file: 2138 lines
- Everything mixed together
- Hard to test individual components
- Imports from deprecated `src/`

**After**:
- 13+ focused modules
- ~150-250 lines each
- Each component testable in isolation
- Imports from `playsem/`
- Clean separation of concerns
- Easy to maintain and extend

---

## ✅ Implementation Order

### Phase 1: Models & Config (Foundation)
1. Create `models.py` - Data structures
2. Create `config.py` - Configuration
3. Create `__init__.py` - Package setup

### Phase 2: Services (Business Logic)
4. Create `services/device_service.py` - Device management
5. Create `services/effect_service.py` - Effect dispatch
6. Create `services/timeline_service.py` - Timeline
7. Create `services/protocol_service.py` - Protocols

### Phase 3: Handlers (Protocol Handling)
8. Create `handlers/websocket_handler.py` - WebSocket
9. Create `handlers/device_handler.py` - Device registration

### Phase 4: Routes (API Endpoints)
10. Create `routes/devices.py` - Device endpoints
11. Create `routes/effects.py` - Effect endpoints
12. Create `routes/ui.py` - UI serving

### Phase 5: Integration (Tie it Together)
13. Create `server.py` - Main orchestrator
14. Refactor `main.py` - Clean entry point
15. Update imports everywhere

### Phase 6: Testing & Verification
16. Add unit tests
17. Add integration tests
18. Verify all functionality

---

## 🚀 Implementation Strategy

**Build incrementally**:
1. Start with foundation (models, config)
2. Extract services one by one
3. Test after each extraction
4. Integrate into server
5. Verify functionality preserved
6. Update imports globally

**Keep old main.py working** until new modules ready, then switch over.

**No breaking changes** - Server must remain functional during refactoring.

---

## 🎯 Success Criteria

- ✅ All 2138 lines of logic preserved
- ✅ Imports changed from `src/` to `playsem/`
- ✅ Device Registry integrated as core
- ✅ Each module < 250 lines
- ✅ Clear separation of concerns
- ✅ Unit tests for each service
- ✅ All functionality verified working
- ✅ No performance degradation

---

**Ready to start?** Begin with Phase 1: Creating `models.py` and `config.py`

