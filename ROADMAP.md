# Development Roadmap - PythonPlaySEM

## ✅ Completed (Phase 0 - Foundation)

### Core Infrastructure
- [x] **DeviceManager** - MQTT-based device communication with dependency injection
- [x] **EffectDispatcher** - Effect-to-device command mapping
- [x] **ConfigLoader** - XML configuration parser
- [x] **Unit Tests** - 100% passing with mocks/fixtures
- [x] **Mock Drivers** - Complete mock device implementations (Light, Wind, Vibration, Scent)
- [x] **Configuration Files** - devices.yaml and effects.yaml with sample data
- [x] **Documentation** - Comprehensive README.md
- [x] **Example Scripts** - mock_device_demo.py demonstrating all features

### What Works Now
```bash
# Run the demo
python examples/mock_device_demo.py

# Run tests
pytest -v
```

---

## ✅ Completed (Phase 1 - Enhanced Functionality)

### Priority 1: Configuration Enhancement
- [x] **YAML Config Loader** - Added YAML parsing support to config_loader.py
  - ✅ Uses pyyaml library (version 6.0.3)
  - ✅ Functions: `load_yaml_config()`, `load_devices_yaml()`, `load_effects_yaml()`
  - ✅ Full backward compatibility with XML configs
  - ✅ Config files: `config/devices.yaml` and `config/effects.yaml`

### Priority 2: Effect Metadata Parser
- [x] **Implemented effect_metadata.py** (340+ lines)
  - ✅ `EffectMetadata` dataclass with full validation
  - ✅ JSON and YAML parsing support (`parse_json()`, `parse_yaml()`)
  - ✅ `EffectTimeline` class for managing multiple effects
  - ✅ Convenience functions: `create_effect()`, `create_timeline()`
  - ✅ All fields supported: effect_type, timestamp, duration, intensity, location, parameters
  - ✅ 9 comprehensive unit tests
  - 🔜 MPEG-V XML parser (future enhancement)

### Priority 3: Enhanced Effect Dispatcher
- [x] **Updated EffectDispatcher** to use effect_metadata.py
  - ✅ Loads effect mappings from `config/effects.yaml`
  - ✅ Parameter mapping with value translation (e.g., "high" → 255)
  - ✅ Location-based routing support
  - ✅ `dispatch_effect_metadata()` method for EffectMetadata objects
  - ✅ Enhanced from 25 lines to 150+ lines

### Priority 4: Timeline Scheduler
- [x] **Created timeline.py** (320+ lines)
  - ✅ `Timeline` class with non-daemon background thread
  - ✅ Methods: `start()`, `pause()`, `resume()`, `stop()`, `seek()`, `get_position()`
  - ✅ `load_timeline()` for EffectTimeline objects
  - ✅ `add_event_effect()` for dynamic event-based triggering
  - ✅ Callback support: `on_start`, `on_stop`, `on_effect`, `on_complete`
  - ✅ Precise timing with 10ms tick interval
  - ✅ Thread-safe with proper cleanup
  - ✅ 5 comprehensive unit tests
  - ✅ Working demo: `examples/timeline_demo.py` (4 scenarios)

### What Works Now
```bash
# Run the enhanced demos
python examples/mock_device_demo.py     # Mock device drivers
python examples/timeline_demo.py        # Timeline scheduler (4 demos)
python examples/mqtt_server_demo.py     # MQTT server (requires broker)

# Run all tests (28 total)
pytest -v

# Test results: ✅ 28 passed in 0.55s
```

---

## ✅ Completed (Phase 2 - Communication Services - Part 1)

### MQTT Server
- [x] **Implemented MQTTServer in protocol_server.py** (330+ lines)
  - ✅ Subscribe to topics for incoming effect requests (wildcard support: `effects/#`)
  - ✅ Parse MQTT payloads as effect metadata (JSON and YAML formats)
  - ✅ Dispatch to EffectDispatcher automatically
  - ✅ Publish device status/responses to response topics
  - ✅ Callback support: `on_effect_received` for custom handling
  - ✅ Thread-safe with background loop (paho-mqtt loop_start/loop_stop)
  - ✅ 11 comprehensive unit tests
  - ✅ Working demo: `examples/mqtt_server_demo.py`

### What Works Now
```bash
# Run MQTT server (requires mosquitto broker running)
python examples/mqtt_server_demo.py

# Test with mosquitto_pub
mosquitto_pub -t "effects/light" -m '{"effect_type":"light","timestamp":0,"duration":1000,"intensity":100}'
```

---

## ✅ Completed (Phase 2 - Communication Services - Part 2)

### WebSocket Server
- [x] **Implemented WebSocketServer in protocol_server.py** (280+ lines)
  - ✅ Uses websockets library (asyncio-based)
  - ✅ Real-time bidirectional communication with JSON messages
  - ✅ Support for web apps and VR applications
  - ✅ Event-based effect streaming with broadcast to all clients
  - ✅ Client connection/disconnection callbacks
  - ✅ Ping/pong heartbeat support
  - ✅ 12 comprehensive unit tests (async tests with pytest-asyncio)
  - ✅ Working demo: `examples/websocket_server_demo.py`
  - ✅ HTML test client: `examples/websocket_client.html`

### What Works Now
```bash
# Run WebSocket server (default: ws://localhost:8765)
python examples/websocket_server_demo.py

# Open in browser
examples/websocket_client.html  # Interactive web interface

# Test with command-line tools
wscat -c ws://localhost:8765
```

---

## ✅ Completed (Phase 2 - Communication Services - Part 3)

### CoAP Server
- [x] **Implemented CoAPServer in protocol_server.py**
  - ✅ Async server using aiocoap with POST /effects endpoint
  - ✅ JSON/YAML payload parsing via EffectMetadataParser
  - ✅ Dispatches to EffectDispatcher and returns JSON response codes
  - ✅ Demo server: `examples/coap_server_demo.py`
  - ✅ Test client: `examples/test_coap_client.py`
  - ✅ Integration test: `tests/test_coap_server_integration.py`
  - ✅ Dependency added: `aiocoap>=0.4.7`

### UPnP Server (Optional)
- [ ] **Implement UPnPServer**
  - Device discovery
  - Service advertisements
  - Compatible with original PlaySEM clients

---

## 🔌 Phase 3 - Device Connectivity

### Serial Driver
- [ ] **Implement serial_driver.py**
  - Use pyserial library
  - Support Arduino and USB devices
  - Methods: open_connection(), send_bytes(), close_connection()
  - Handle serial port discovery

### Bluetooth Driver
- [ ] **Implement bluetooth_driver.py**
  - Use pybluez or bleak library
  - Support BLE devices
  - Device pairing and connection management

### Driver Integration
- [ ] **Update DeviceManager**
  - Accept connectivity_driver parameter
  - Support multiple driver types (MQTT, Serial, Bluetooth, Mock)
  - Auto-detect driver based on config

---

## 🎯 Phase 4 - Advanced Features

### Delay Compensation
- [ ] Calculate latency chain (parsing → network → device)
- [ ] Adjust timing in TimeLineDeviceCommand
- [ ] Measure actual device response times

### Device Capabilities
- [ ] Generate capability descriptions (JSON/XML)
- [ ] Expose via /capabilities endpoint
- [ ] Support capability negotiation

### Reset & Lifecycle
- [ ] Add reset_device() to all drivers
- [ ] Call on startup and shutdown
- [ ] Graceful error handling and recovery

### Location Support
- [ ] Implement MPEG-V LocationCS scheme
- [ ] Support spatial audio-like positioning
- [ ] Multi-device coordination for location-based effects

---

## 📝 Phase 5 - Polish & Production

### Logging & Debugging
- [ ] Structured logging throughout
- [ ] Debug mode with verbose output
- [ ] Performance metrics and profiling

### Testing
- [ ] Integration tests with real MQTT broker
- [ ] Performance/load tests
- [ ] Device driver tests with mock serial ports

### Documentation
- [ ] API reference documentation
- [ ] Device driver development guide
- [ ] Configuration guide with examples
- [ ] Troubleshooting guide

### Examples
- [ ] Timeline-based video sync example
- [ ] Game event integration example
- [ ] VR application integration
- [ ] Custom device driver example

---

## 🔧 Quick Commands Reference

```bash
# Testing
pytest -v                           # Run all tests (17 tests)
pytest --cov=src tests/             # Run with coverage
pytest tests/test_timeline.py -v   # Run specific test file

# Demos
python examples/mock_device_demo.py    # Mock device drivers demo
python examples/timeline_demo.py       # Timeline scheduler demo (15-20s, 4 scenarios)

# Development
black src/ tests/                   # Format code
flake8 src/ tests/                  # Lint code

# Dependencies
pip install -r requirements.txt     # Install all dependencies
pip install pyyaml paho-mqtt pytest # Install core dependencies

# Future commands (when implemented)
python -m src.main --config config.xml --broker mqtt
python -m src.main --server websocket --port 8080
```

---

## 📊 Feature Parity Checklist (vs. Upstream PlaySEM)

| Feature | Upstream (Java) | Python Port | Status |
|---------|----------------|-------------|--------|
| MQTT Communication | ✅ | ✅ | Done (client + server) |
| Mock Devices | ✅ | ✅ | Done (4 types) |
| XML Config | ✅ | ✅ | Done |
| YAML Config | ❌ | ✅ | Done (better than upstream!) |
| Effect Dispatcher | ✅ | ✅ | Done + YAML mapping |
| Effect Metadata | ✅ | ✅ | Done (JSON/YAML) |
| Timeline Scheduler | ✅ | ✅ | Done + callbacks |
| MQTT Server | ✅ | ✅ | Done + JSON/YAML parsing |
| WebSocket Server | ✅ | ✅ | Done + broadcast + HTML client |
| Serial Devices | ✅ | ❌ | Not started |
| Bluetooth Devices | ✅ | ❌ | Not started |
| MPEG-V Parser | ✅ | 🟡 | JSON/YAML done, XML pending |
| CoAP Server | ✅ | ✅ | Done (POST /effects, demos, tests) |
| UPnP Server | ✅ | ❌ | Not started |
| Delay Compensation | ✅ | ❌ | Not started |
| Device Capabilities | ✅ | ❌ | Not started |
| Location Support | ✅ | 🟡 | Basic support in dispatcher |
| Unit Tests | 🟡 | ✅ | 40 tests, 100% passing |

**Legend:** ✅ Complete | 🟡 Partial | ❌ Not started

**Progress Summary:** 
- ✅ **11/18 features complete** (~61% - over halfway! 🚀)
- 🟡 **2/18 features partial** (11%)
- Phase 1 (Enhanced Functionality) **100% complete** ✅
- Phase 2 (Communication Services) **75% complete** (MQTT ✅, WebSocket ✅, CoAP ✅; UPnP pending)

---

## 🎓 Learning Resources

### Original PlaySEM Papers
1. "A Mulsemedia Framework for Delivering Sensory Effects to Heterogeneous Systems"
2. "Mulsemedia DIY: A Survey of Devices and a Tutorial"
3. "Coping with the Challenges of Delivering Multiple Sensorial Media"

### Python Libraries Used
- **paho-mqtt**: MQTT client library
- **pyyaml**: YAML parsing
- **pyserial**: Serial/USB communication (future)
- **websockets**: WebSocket server (future)
- **aiocoap**: CoAP protocol (future)

---

**Last Updated**: November 12, 2025  
**Status**: Project paused; Communication Services largely complete (MQTT, WebSocket, CoAP)  
**Current Phase**: Phase 2 - Communication Services (3/4 complete: MQTT ✅, WebSocket ✅, CoAP ✅)  
**Next Up (when resumed)**: UPnP discovery, then Phase 3 (Serial/Bluetooth drivers)

> Pause note: The repository is in a stable state with runnable demos for WebSocket, MQTT (including public-broker example), and CoAP, plus integration tests. See TESTING.md for how to run them on Windows PowerShell.
