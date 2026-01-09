# PythonPlaySEM Desktop GUI

A professional PyQt6-based desktop application for controlling sensory effects across multiple devices using various communication protocols.

## Features

✨ **Multiple Communication Protocols**
- WebSocket (included)
- HTTP/REST (included)
- MQTT (included)
- Easily extensible for other protocols

🎮 **Device Management**
- Real-time device discovery
- Multi-device support
- Device type detection (Light, Vibration, Wind, etc.)

🎨 **Effect Control**
- Multiple effect types (Light, Vibration, Wind, Scent, Heat, Cold)
- Intuitive sliders for intensity control
- Color picker for light effects
- Duration control
- Custom parameters

📊 **Real-time Monitoring**
- Connection status indicator
- Device list with live updates
- Effect execution feedback

## Installation

### Requirements
- Python 3.10+
- PyQt6

### Setup

1. **Install dependencies:**
```bash
pip install PyQt6==6.7.0
pip install websockets>=9.0
pip install httpx>=0.27.0
```

2. **Optional: Install protocol libraries:**
```bash
# For MQTT support
pip install paho-mqtt

# For CoAP support  
pip install aiocoap[ws]==0.4.7
```

## Quick Start

### Method 1: Simple Launch (WebSocket)

```bash
# Start the backend server
python examples/server/main.py

# In another terminal, start the GUI
python gui/app.py
```

Then:
1. GUI opens with Connection panel
2. Click "Connect" (defaults to WebSocket on localhost:8090)
3. Click "Scan Devices" to see connected devices
4. Select a device and switch to Effects tab
5. Adjust effect parameters and click "Send Effect"

### Method 2: With Custom Protocols

```python
# In gui/app.py, before MainWindow creation:
# See examples/protocols/custom_protocols_guide.py for implementation
from examples.protocols.custom_protocols_guide import register_custom_protocols

register_custom_protocols()  # Registers MQTT, CoAP, etc.

window = MainWindow()
window.show()
```

## Architecture

```
┌─────────────────────────────────────┐
│       PyQt6 GUI Application         │
│  (MainWindow, Panels, Widgets)      │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│     AppController                   │
│  (Protocol abstraction, state mgmt) │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Protocol Factory                  │
│  (WebSocket, HTTP, MQTT, CoAP)      │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   FastAPI Backend Server            │
│  (Already running on port 8090)     │
└─────────────────────────────────────┘
```

## File Structure

```
gui/
├── __init__.py                          # Package init
├── app.py                               # Entry point
├── app_controller.py                    # Core application logic
├── (moved to examples/protocols/custom_protocols_guide.py)
├── protocols/
│   ├── __init__.py
│   ├── base_protocol.py                 # Abstract base class
│   ├── websocket_protocol.py            # WebSocket implementation
│   ├── http_protocol.py                 # HTTP/REST implementation
│   └── protocol_factory.py              # Factory pattern
└── ui/
    ├── __init__.py
    ├── main_window.py                   # Main application window
    ├── connection_panel.py              # Connection management UI
    ├── device_panel.py                  # Device list UI
    ├── effect_panel.py                  # Effect control UI
    └── status_bar.py                    # Status display
```

## Adding Custom Protocols

### Step 1: Create your protocol class

```python
from gui.protocols import BaseProtocol

class MyProtocol(BaseProtocol):
    async def connect(self) -> bool:
        # Your connection logic
        pass
    
    async def disconnect(self) -> bool:
        # Your disconnection logic
        pass
    
    async def send(self, data: Dict[str, Any]) -> bool:
        # Your send logic
        pass
    
    async def listen(self):
        # Your message listening logic
        pass
```

### Step 2: Register the protocol

```python
from gui.protocols import ProtocolFactory
from my_module import MyProtocol

ProtocolFactory.register("myprotocol", MyProtocol)
```

### Step 3: Use it in the GUI

The protocol will automatically appear in the "Protocol:" dropdown in the Connection panel!

## Protocol Examples

See `examples/protocols/custom_protocols_guide.py` for complete examples of:
- **MQTTProtocol**: MQTT broker integration
- **CoAPProtocol**: CoAP protocol support

## Extending the GUI

### Add a new widget

1. Create `gui/ui/my_widget.py`
2. Inherit from `QWidget`
3. Import in `gui/ui/__init__.py`
4. Add tab to `MainWindow.setup_ui()`

### Add custom effect parameters

Edit `gui/ui/effect_panel.py` - the Effect Panel is fully customizable!

## Protocols

The GUI supports multiple communication protocols:

- **WebSocket** (default: localhost:8090) - Real-time bidirectional
- **HTTP/REST** (default: localhost:8090) - Request/response polling
- **MQTT** (default: localhost:1883) - Pub/Sub messaging

### Using MQTT

1. Install broker: `pip install mosquitto`
2. Start broker: `mosquitto -l 127.0.0.1 -p 1883`
3. Launch GUI: `python -m gui.app`
4. Select "mqtt" in Protocol dropdown and connect

### Adding a New Protocol

1. Create `gui/protocols/your_protocol.py` extending `BaseProtocol`
2. Implement: `connect()`, `disconnect()`, `send()`, `listen()`
3. Register in `gui/protocols/protocol_factory.py`
4. (Optional) Create UI panel in `gui/ui/your_connection_panel.py`

See `BaseProtocol` class for required interface.

## Troubleshooting

**"Connection refused" error:**
- Ensure backend server is running: `python examples/server/main.py`
- Check host and port settings (default: localhost:8090)

**"No devices found":**
- Click "Scan Devices" button in Devices tab
- Ensure devices are configured in `config/devices.yaml`

**MQTT not showing in dropdown:**
- Verify `paho-mqtt` is installed: `pip install paho-mqtt`

## Future Enhancements

- [ ] Timeline player UI integration
- [ ] Device simulator mode
- [ ] Multi-connection support
- [ ] Bluetooth protocol support
- [ ] Serial/USB protocol support

## License

MIT - See LICENSE file
