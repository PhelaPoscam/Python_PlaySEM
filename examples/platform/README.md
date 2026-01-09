# PlaySEM Modular Server Architecture Examples

This directory contains examples demonstrating the **Phase 3 refactored modular architecture** for building FastAPI servers with PlaySEM.

## What's Inside

### 1. `basic_server.py`
**Minimal working server** - Shows the simplest way to use the modular architecture.

```bash
python examples/platform/basic_server.py
```

Features:
- Factory pattern with `create_app()`
- Service layer (DeviceService, EffectService)
- RESTful routes
- WebSocket support
- ~50 lines of code (vs 2139 in old monolith)

### 2. `custom_handler_server.py`
**Advanced server** - Demonstrates adding custom protocol handlers (MQTT, CoAP).

```bash
python examples/platform/custom_handler_server.py
```

Features:
- All features from basic_server
- Custom MQTT handler integration
- Shows how to extend ProtocolService
- Production-ready example

### 3. `README.md`
**Architecture guide** - Explains the modular design patterns used.

## Key Concepts

### Factory Pattern
```python
from tools.test_server.app import create_app

app = create_app()  # Returns configured FastAPI instance
```

### Service Layer
- **DeviceService** - Device management logic
- **EffectService** - Effect dispatching logic
- **TimelineService** - Timeline playback
- **ProtocolService** - Protocol handler orchestration

### Handler Layer
- **WebSocketHandler** - Real-time bidirectional communication
- **MQTTHandler** - MQTT pub/sub (example implementation)
- Custom handlers can be added easily

### Routes Layer
- **DeviceRoutes** - `/api/devices/*`
- **EffectRoutes** - `/api/effects/*`
- **UIRoutes** - Static files, WebSocket endpoint

## Migration from Monolith

**Before (Phase 2):**
```python
# tools/test_server/main.py - 2139 lines monolith
from tools.test_server.main import ControlPanelServer

server = ControlPanelServer()
server.run()
```

**After (Phase 3):**
```python
# Modular architecture - 214 lines factory
from tools.test_server.app import create_app

app = create_app()
# Run with: uvicorn app:app
```

## Architecture Benefits

| Aspect | Monolith (Old) | Modular (New) |
|--------|----------------|---------------|
| Lines of code | 2139 | 214 (factory) |
| Testability | Low (integration only) | High (unit testable) |
| Maintainability | Poor (single file) | Excellent (separated concerns) |
| Extensibility | Hard (edit monolith) | Easy (add handler/service) |
| Readability | Complex (mixed concerns) | Clear (single responsibility) |

## Production Usage

The full production server is at:
```
tools/test_server/
├── app/
│   ├── main.py           # Factory
│   ├── services/         # Business logic
│   ├── handlers/         # Protocol handlers
│   └── routes/           # HTTP routes
├── config.py             # Configuration
├── models.py             # Data models
└── static/               # Frontend assets
```

Run it:
```bash
cd tools/test_server
uvicorn app.main:app --reload
```

## See Also

- [Phase 3D Completion Report](../../docs/archive/PHASE_3D_COMPLETE.md)
- [Architecture Reference](../../docs/reference/architecture.md)
- [Protocol Examples](../protocols/)
