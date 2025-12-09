# System Architecture

## Overview

PythonPlaySEM is a Python application for controlling effects on networked devices through a desktop GUI. The system uses an async-first architecture with dual protocol support (WebSocket and HTTP).

```
┌─────────────────────────────────────────────────────┐
│         Desktop GUI (PyQt6 + qasync)                │
│  ┌───────────────────────────────────────────────┐  │
│  │  Main Window with Tabs                        │  │
│  │  - Control Panel                              │  │
│  │  - Device Manager                             │  │
│  │  - Effect Explorer                            │  │
│  │  - Timeline Player                            │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼─────┐         ┌────▼──────┐
   │ WebSocket │         │   HTTP    │
   │ Protocol  │         │ Protocol  │
   └────┬─────┘         └────┬──────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────┐
        │   Backend Server        │
        │  (FastAPI + Uvicorn)    │
        │  localhost:8090         │
        └──────────┬──────────────┘
                   │
        ┌──────────▼──────────────┐
        │   Device Abstraction    │
        │  (BaseDriver Pattern)   │
        └──────────┬──────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐         ┌─────▼──┐
   │ Serial   │         │ Mock   │
   │ Devices  │         │ Devices│
   └──────────┘         └────────┘
```

## Component Structure

### Frontend (GUI)

**Technology**: PyQt6 6.7.0 + qasync 0.27.0+

Located in: `gui/`

- **app.py** - Entry point
  - Creates QApplication
  - Initializes QEventLoop (from qasync)
  - Launches MainWindow
  - Single integrated asyncio event loop

- **app_controller.py** - State management
  - Manages connection state
  - Delegates protocol handling
  - Sends device/effect messages
  - Handles UI callbacks

- **ui/main_window.py** - Main window
  - Creates tab interface
  - @asyncSlot decorated handlers
  - Manages UI updates
  - Delegates to controllers

- **ui/panels/** - Panel implementations
  - ControlPanel - Effect control
  - DevicePanel - Device management
  - EffectPanel - Effect explorer
  - TimelinePanel - Timeline playback

### Protocol Layer

**Location**: `gui/protocols/`

**Pattern**: Factory pattern with BaseProtocol interface

- **base_protocol.py**
  - Abstract BaseProtocol class
  - connect() - Establish connection
  - disconnect() - Close connection
  - send_effect() - Send effect
  - Message callbacks

- **websocket_protocol.py**
  - Full duplex WebSocket connection
  - Real-time device updates
  - Streaming effects

- **http_protocol.py**
  - REST-based HTTP with polling
  - GET /api/devices - Device discovery
  - POST /api/effects - Send effects
  - Polling for updates (TODO)

- **factory.py**
  - ProtocolFactory class
  - Returns protocol instances
  - Validates protocol names

### Backend Server

**Technology**: FastAPI + Uvicorn

**Location**: `examples/server/main.py`

**Endpoints**:
- `GET /api/devices` - List available devices
- `POST /api/devices/{id}/effects` - Send effect
- `WS /ws` - WebSocket connection

**Features**:
- Mock device support
- Effect application
- CORS enabled
- JSON message format

### Device Abstraction

**Location**: `src/device_driver/`

**Pattern**: BaseDriver abstract class

- **base_driver.py**
  - Abstract interface
  - connect()
  - send_effect()
  - get_status()

- **serial_driver.py**
  - Physical serial device support
  - COM port communication
  - USB enumeration

- **mock_driver.py**
  - Testing/demo device
  - Simulated effects
  - No hardware required

## Event Loop Architecture

### Problem (Pre-qasync)
- Qt had its own main event loop
- asyncio had separate event loop
- Async handlers created new event loops
- Result: "no running event loop" errors
- Threading issues: QObject in different thread

### Solution (qasync)
```python
from qasync import QEventLoop

app = QApplication(sys.argv)
loop = QEventLoop(app)  # Single integrated loop
asyncio.set_event_loop(loop)

window = MainWindow()
window.show()

with loop:
    loop.run_forever()
```

### Result
- Single unified event loop
- Qt and asyncio coexist
- No threading complexity
- @asyncSlot handlers work seamlessly

## Message Flow

### Device Discovery

```
User clicks "Scan"
    ↓
MainWindow.on_scan_devices() [@asyncSlot]
    ↓
app_controller.scan_devices()
    ↓
protocol.connect()
    ↓
Backend: GET /api/devices
    ↓
Device list returned
    ↓
Update UI with devices
```

### Effect Sending

```
User selects effect
    ↓
MainWindow.on_send_effect() [@asyncSlot]
    ↓
app_controller.send_effect(device_id, effect)
    ↓
protocol.send_effect(...)
    ↓
Backend: POST /api/devices/{id}/effects
    ↓
Device applies effect
    ↓
UI updated with result
```

## Data Structures

### Device Object
```json
{
  "id": "device-1",
  "name": "Living Room",
  "type": "light",
  "status": "connected",
  "capabilities": ["on/off", "brightness", "color"]
}
```

### Effect Object
```json
{
  "id": "effect-1",
  "name": "Rainbow",
  "duration": 5000,
  "params": {
    "speed": 0.5,
    "intensity": 1.0
  }
}
```

### Protocol Message
```json
{
  "type": "device_list" | "effect_applied" | "error",
  "payload": {...},
  "timestamp": "2025-12-09T10:30:00Z"
}
```

## Key Design Patterns

### 1. Factory Pattern (Protocols)
```python
protocol = ProtocolFactory.create("websocket")
# returns WebSocketProtocol instance
```

### 2. Abstract Base Classes (Drivers)
```python
class BaseDriver(ABC):
    @abstractmethod
    def send_effect(self, effect): pass
```

### 3. Callback Pattern (Messages)
```python
def on_device_list(devices):
    # Update UI with devices

protocol.on_message = on_device_list
```

### 4. Async/Await (Event Handling)
```python
@asyncSlot()
async def on_button_click():
    await protocol.send_effect(effect)
```

## Configuration

### Device Configuration
**File**: `config/devices.yaml`

```yaml
mock_devices:
  - id: device-1
    name: Living Room
    type: light
```

### Effect Configuration
**File**: `config/effects.yaml`

```yaml
effects:
  - id: rainbow
    name: Rainbow Effect
    duration: 5000
```

## Testing Architecture

### Unit Tests (tests/)
- `test_device_manager.py` - Device management
- `test_effect_metadata.py` - Effect handling
- `test_config_loader.py` - Configuration loading

### Integration Tests
- Protocol communication
- Device discovery
- Effect sending

### Test Coverage
- 9/9 test categories passing (100%)
- Mock devices for isolated testing
- No hardware required

## Performance Characteristics

### Event Loop
- Single threaded async model
- No context switching overhead
- Responsive UI with concurrent operations

### Protocol Communication
- WebSocket: Real-time, low latency
- HTTP: Polling, higher latency
- Both non-blocking

### Memory
- Minimal overhead from qasync
- Qt manages widget lifecycle
- Device objects cached in memory

## Deployment Considerations

### GUI Application
- Requires: PyQt6, qasync, Python 3.10+
- Single executable deployment possible
- Cross-platform (Windows, Linux, macOS)

### Backend Server
- FastAPI framework
- Can run on separate machine
- REST endpoints discoverable
- WebSocket capable

### Scalability
- Single device → multiple devices
- Single protocol → multiple protocol support
- Single backend → load balanced backend

## Security Notes

- ⚠️ Backend has CORS enabled (dev only)
- No authentication implemented (demo)
- Device IDs transmitted in clear text
- Consider TLS for production deployment

---

*Last updated: December 9, 2025*
