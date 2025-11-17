# Examples Directory

This directory contains **demonstration and testing code only**. The actual working framework code is in `src/`.

## 📂 Directory Structure

### `clients/` - Protocol Test Clients
Simple test scripts that send effects to PlaySEM servers. Use these to verify protocol servers are working.

- `test_http_client.py` - HTTP REST API client
- `test_websocket_client.py` - WebSocket streaming client  
- `test_mqtt_client.py` - MQTT publisher (local broker)
- `test_mqtt_client_public.py` - MQTT publisher (public broker)
- `test_coap_client.py` - CoAP client
- `test_upnp_client.py` - UPnP discovery client

**Usage**: Run these after starting a protocol server to test communication.

---

### `demos/` - Standalone Server Demos
Individual protocol server examples showing how to use the framework in isolation.

- `http_server_demo.py` - HTTP REST API server
- `websocket_server_demo.py` - WebSocket real-time server
- `mqtt_server_demo.py` - MQTT subscriber (local broker)
- `mqtt_server_demo_public.py` - MQTT subscriber (public broker)
- `coap_server_demo.py` - CoAP server
- `upnp_server_demo.py` - UPnP discovery server
- `unified_server_demo.py` - All protocols in one server
- `timeline_demo.py` - Timeline-based effect scheduling
- `mock_device_demo.py` - Mock device testing
- `driver_integration_demo.py` - Device driver integration
- `end_to_end_integration_demo.py` - Complete system test

**Usage**: Run any demo script directly to see how that specific feature works.

---

### `control_panel/` - Full-Featured Web Control Panel
**The recommended way to test PlaySEM!**

Production-ready web interface with:
- Device management (Serial, Bluetooth, Mock)
- All protocol servers (HTTP, WebSocket, MQTT, CoAP, UPnP)
- Effect testing interface
- Real-time activity log
- System statistics

**Files**:
- `control_panel_server.py` - Backend server
- `control_panel.html` - Web UI
- `HOW_TO_TEST.md` - Comprehensive testing guide
- `QUICKSTART.md` - 3-minute quick start
- `PROTOCOL_TESTING.md` - Protocol examples
- `README.md` - Control panel documentation

**Usage**:
```bash
python examples/control_panel/control_panel_server.py
# Open http://localhost:8090
```

---

### `web/` - Simple HTML Testers
Lightweight HTML pages for quick browser-based testing.

- `phone_tester.html` - Test phone vibration via WebSocket
- `phone_tester_server.py` - Simple HTTP server for phone tester
- `websocket_client.html` - WebSocket client UI

**Usage**: Serve with any HTTP server or use `phone_tester_server.py`

---

## 🎯 Quick Start

**For Testing**: Use the control panel (most features in one place)
```bash
python examples/control_panel/control_panel_server.py
```

**For Learning**: Run individual demos to understand each component
```bash
python examples/demos/http_server_demo.py
```

**For Integration**: Use test clients to verify your own PlaySEM server
```bash
python examples/clients/test_http_client.py
```

---

## 📝 Note

These are **examples only**. The actual PlaySEM framework code is in:
- `src/` - Core framework (config_loader, device_manager, effect_dispatcher, protocol_server, etc.)
- `tests/` - Unit and integration tests (57 tests)
- `config/` - YAML/XML configuration files

See the main README.md for framework documentation.
