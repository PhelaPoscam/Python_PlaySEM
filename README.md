# PythonPlaySEM

**Python port of PlaySEM Sensory Effects Renderer (SER)**

A framework for delivering sensory effects (wind, light, vibration, scent) to heterogeneous mulsemedia systems. This is a Python implementation inspired by the original [PlaySEM SER](https://github.com/PhelaPoscam/PlaySEM) Java framework.

## 🎯 Project Goals

PythonPlaySEM aims to provide:
- **Multi-sensory effect rendering** for multimedia applications (video players, games, VR)
- **Flexible communication protocols** (MQTT, WebSocket, CoAP, UPnP)
- **Multiple device connectivity options** (Serial/USB, Bluetooth, Wi-Fi, Ethernet)
- **Extensible architecture** for custom devices and metadata parsers
- **Timeline-based and event-based** effect triggering

## 🚀 Current Status

**Phase 2 Complete!** (November 17, 2025) All communication protocols implemented and tested.

### ✅ Phase 2 Complete - Communication Services + Security
- **MQTT Server**: Subscribes to `effects/#`; username/password + TLS/SSL + auto-reconnect
- **WebSocket Server**: Async real-time server + HTML control panel; token auth + WSS (secure)
- **HTTP REST API**: FastAPI server with `/api/effects`, `/api/status`, `/api/devices`; API key + CORS
- **CoAP Server**: Lightweight IoT protocol with `POST /effects` endpoint
- **UPnP Server**: SSDP device discovery and network advertisement
- **Security**: All protocols support authentication and encryption (TLS/SSL)
- Configuration Loader: XML and YAML parsers
- Device Manager: MQTT-based device communication
- Effect Dispatcher: Maps high-level effects to device commands
- Effect Metadata: JSON/YAML parsing to typed dataclass
- Timeline Scheduler: Event-based and time-based effect triggering
- Tests: 57 unit + integration tests (all passing!)

### 🔜 Phase 3 - Device Connectivity (Next)
- Serial/USB drivers for Arduino devices
- Bluetooth/BLE drivers for wireless devices
- Driver integration with DeviceManager
- Delay compensation and timing precision

### ✨ Future Enhancements
- **Service Discovery**: Implement UPnP or mDNS-based service discovery for the WebSocket server to allow clients to automatically find the server on the network.

## 📁 Project Structure

```
d:\TUNI\Python\Python_PlaySEM\
├───.gitignore
├───pyproject.toml
├───README.md
├───requirements.txt
├───run_tests.py
├───.git\
├───.pytest_cache\
│   └───v\
├───.qodo\
│   ├───agents\
│   └───workflows\
├───.vscode\
├───config\
│   ├───devices.yaml
│   └───effects.yaml
├───docs\
│   ├───CONTROL_PANEL_ARCHITECTURE.md
│   ├───CONVENTIONS.md
│   ├───DEVICE_TESTING_CHECKLIST.md
│   ├───mqtt_broker_plan.md
│   ├───README.md
│   ├───ROADMAP.md
│   ├───UNIVERSAL_DRIVER_INTEGRATION.md
│   ├───archive\
│   │   ├───INTEGRATION_TESTING.md
│   │   ├───PHASE2_COMPLETION.md
│   │   ├───PHASE2_ENHANCEMENTS.md
│   │   ├───README.md
│   │   └───TESTING.md
│   ├───guides\
│   │   ├───CONTROL_PANEL_GUIDE.md
│   │   ├───MOBILE_PHONE_SETUP.md
│   │   └───UPNP_GUIDE.md
│   ├───reference\
│   │   └───TIMELINE_PLAYER.md
│   └───testing\
│       └───PROTOCOL_TESTING.md
├───examples\
│   ├───README.md
│   ├───clients\
│   │   ├───test_coap_client.py
│   │   ├───test_http_client.py
│   │   ├───test_mqtt_client_public.py
│   │   ├───test_mqtt_client.py
│   │   ├───test_upnp_client.py
│   │   └───test_websocket_client.py
│   ├───control_panel\
│   │   ├───control_panel_server.py
│   │   ├───control_panel.html
│   │   ├───PROTOCOL_TESTING.md
│   │   ├───README.md
│   │   ├───sample_timeline.xml
│   │   └───TIMELINE_PLAYER.md
│   ├───demos\
│   │   ├───bluetooth_driver_demo.py
│   │   ├───coap_server_demo.py
│   │   ├───driver_integration_demo.py
│   │   ├───end_to_end_integration_demo.py
│   │   ├───http_server_demo.py
│   │   ├───mock_device_demo.py
│   │   ├───mqtt_server_demo_public.py
│   │   ├───mqtt_server_demo.py
│   │   ├───serial_driver_demo.py
│   │   ├───timeline_demo.py
│   │   ├───unified_server_demo.py
│   │   ├───upnp_server_demo.py
│   │   ├───websocket_control_server.py
│   │   └───websocket_server_demo.py
│   └───web\
│       ├───phone_tester_server.py
│       ├───phone_tester.html
│       └───websocket_client.html
├───src\
│   ├───config_loader.py
│   ├───device_manager.py
│   ├───effect_dispatcher.py
│   ├───effect_metadata.py
│   ├───main.py
│   ├───protocol_server.py
│   ├───timeline.py
│   └───device_driver\
│       ├───__init__.py
│       ├───base_driver.py
│       ├───bluetooth_driver.py
│       ├───driver_factory.py
│       ├───mock_driver.py
│       ├───mqtt_driver.py
│       └───serial_driver.py
├───tests\
│   ├───conftest.py
│   ├───test_coap_server_integration.py
│   ├───test_config_loader.py
│   ├───test_device_manager.py
│   ├───test_effect_dispatcher.py
│   ├───test_effect_metadata.py
│   ├───test_mqtt_broker.py
│   ├───test_timeline.py
│   ├───test_upnp_server.py
│   └───test_websocket_server.py
└───venv\
```

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/PhelaPoscam/Python_PlaySEM.git
   cd PythonPlaySEM
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or for development:
   pip install -e ".[dev]"
   ```

## 🎮 Usage

The `examples` directory contains a variety of scripts to demonstrate the features of PythonPlaySEM.

### Standalone Server Demos (`examples/demos/`)
These scripts show how to run each protocol server in isolation. They are great for understanding how each component works.

- **WebSocket server + HTML client** (ws://localhost:8765):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\websocket_server_demo.py
   ```
   *This will generate a QR code to easily connect from your phone.*

- **HTTP REST server** (http://localhost:8080):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\http_server_demo.py
   ```

- **MQTT public-broker demo** (test.mosquitto.org):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\mqtt_server_demo_public.py
   ```

- **CoAP server** (coap://localhost:5683):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\coap_server_demo.py
   ```

- **UPnP device discovery** (SSDP multicast):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\upnp_server_demo.py
   ```

### Protocol Test Clients (`examples/clients/`)
Use these simple test scripts to send effects to the servers and verify that they are working correctly.

- **HTTP REST client:**
  ```powershell
  # Submit effect
  curl -X POST http://localhost:8080/api/effects \
    -H "Content-Type: application/json" \
    -d '{"effect_type":"light","intensity":200,"duration":1000}'
  ```

- **MQTT client:**
  ```powershell
  .\.venv\Scripts\python.exe examples\clients\test_mqtt_client_public.py
  ```

- **CoAP client:**
  ```powershell
  .\.venv\Scripts\python.exe examples\clients\test_coap_client.py
  ```

- **UPnP client:**
  ```powershell
  .\.venv\Scripts\python.exe examples\clients\test_upnp_client.py
  ```

### Web Control Panel (`examples/control_panel/`)
This is the recommended way to test the full capabilities of PythonPlaySEM. It provides a full-featured web interface for device management, effect testing, and real-time logging.

```powershell
python examples\control_panel\control_panel_server.py
```
Then open `http://localhost:8090` in your browser.
For more details, see the **[Comprehensive Control Panel Guide](docs/guides/CONTROL_PANEL_GUIDE.md)**.

### Basic Example (programmatic usage)

```python
from src.config_loader import load_config
from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher

# Load configuration
config = load_config("config.xml")

# Create device manager (MQTT broker)
device_manager = DeviceManager(broker_address="localhost")

# Create effect dispatcher
effect_dispatcher = EffectDispatcher(device_manager=device_manager)

# Dispatch a light effect
effect_dispatcher.dispatch_effect("light", {"intensity": "high"})
```

### 🔒 Security Features

**MQTT Security:**
```python
server = MQTTServer(
    broker_address="mqtt.example.com",
    port=8883,  # TLS port
    username="admin",
    password="secret123",
    use_tls=True,
    tls_ca_certs="/path/to/ca.crt",
    dispatcher=dispatcher
)
```

**WebSocket Security:**
```python
server = WebSocketServer(
    host="0.0.0.0",
    port=8765,
    auth_token="secret_token_123",
    use_ssl=True,
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem",
    dispatcher=dispatcher
)
```

**HTTP Security:**
```python
server = HTTPServer(
    host="0.0.0.0",
    port=8080,
    api_key="your_secret_api_key",
    cors_origins=["https://example.com"],
    dispatcher=dispatcher
)
```

See `docs/` folder for detailed guides on each protocol.

### Running Tests

```bash
pytest
```

For verbose output:
```bash
pytest -v
```

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              (Video Player, Game, VR App)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Protocol Servers                            │
│          (MQTT, WebSocket, CoAP, UPnP)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Effect Dispatcher                               │
│        Maps effects → device commands                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Device Manager                                  │
│      Sends commands via connectivity drivers                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
   ┌────────┐   ┌─────────┐   ┌──────────┐   ┌──────┐
   │ Serial │   │ MQTT    │   │Bluetooth │   │ Mock │
   │ Driver │   │ Client  │   │  Driver  │   │Driver│
   └────┬───┘   └────┬────┘   └─────┬────┘   └───┬──┘
        │            │              │            │
        ▼            ▼              ▼            ▼
   ┌────────────────────────────────────────────────┐
   │          Physical Devices                      │
   │   (Fans, LEDs, Vibrators, Scent Diffusers)   │
   └────────────────────────────────────────────────┘
```

### Key Modules

- **`config_loader.py`**: Parses XML/YAML configuration files
- **`device_manager.py`**: Manages device communication
- **`effect_dispatcher.py`**: Routes effects to appropriate devices
- **`effect_metadata.py`**: Parses sensory effect metadata (MPEG-V, JSON)
- **`protocol_server.py`**: Implements communication protocols
- **`device_driver/`**: Device connectivity drivers (Serial, Bluetooth, Mock)

## ⚙️ Configuration

### XML Configuration (SERenderer.xml)

```xml
<SERendererConfig>
  <communicationServiceBroker>mqttService</communicationServiceBroker>
  <metadataParser>mpegvParser</metadataParser>
  <lightDevice>mockLight</lightDevice>
  <windDevice>mockWind</windDevice>
  <vibrationDevice>mockVibration</vibrationDevice>
  <scentDevice>mockScent</scentDevice>

  <devices>
    <device>
      <id>mockLight</id>
      <deviceClass>device_driver.mock_driver.MockLightDevice</deviceClass>
      <connectivityInterface>mockInterface</connectivityInterface>
      <properties>
        <delay>800</delay>
      </properties>
    </device>
  </devices>
</SERendererConfig>
```

### YAML Configuration

YAML support is available in `config/devices.yaml` and `config/effects.yaml` and is used by the dispatcher and integration tests.

## 🧪 Testing

All tests use mocks and fixtures to avoid requiring real hardware or network services.

Run specific test files:
```bash
pytest tests/test_config_loader.py
pytest tests/test_device_manager.py
pytest tests/test_effect_dispatcher.py
```

## 🤝 Contributing

This project is a translation/port of the original PlaySEM framework. Contributions are welcome!

### Development Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8
   ```

2. Run tests with coverage:
   ```bash
   pytest --cov=src tests/
   ```

3. Format code:
   ```bash
   black src/ tests/
   ```

## 📚 Related Projects & Papers

### Original PlaySEM
- **Repository**: [PhelaPoscam/PlaySEM](https://github.com/PhelaPoscam/PlaySEM)
- **Java Version**: PlaySEM SER 2.0.0 (requires Java 21+)

### Research Papers
- Saleme et al., "A Mulsemedia Framework for Delivering Sensory Effects to Heterogeneous Systems", *Multimedia Systems*, Springer, 2019. [DOI: 10.1007/s00530-019-00618-8](https://doi.org/10.1007/s00530-019-00618-8)
- Saleme et al., "Mulsemedia DIY: A Survey of Devices and a Tutorial for Building your own Mulsemedia Environment", *ACM Computing Surveys*, 2019. [DOI: 10.1145/3319853](https://doi.org/10.1145/3319853)
- Saleme et al., "Coping with the Challenges of Delivering Multiple Sensorial Media", *IEEE MultiMedia*, 2019. [DOI: 10.1109/MMUL.2018.2873565](https://doi.org/10.1109/MMUL.2018.2873565)

### Compatible Applications
- **PlaySEM SE Video Player**: [estevaosaleme/PlaySEM_SEVideoPlayer](https://github.com/estevaosaleme/PlaySEM_SEVideoPlayer)


## 🙏 Acknowledgments

This project is based on the PlaySEM Sensory Effects Renderer framework developed by the LPRM research group. Special thanks to the original authors for their groundbreaking work in mulsemedia systems.


## 📖 Documentation

Start here: [docs/README.md](docs/README.md) — centralized index of all guides, reference, testing, and roadmap documents.

Key entries:
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- Control Panel Guide: [docs/guides/CONTROL_PANEL_GUIDE.md](docs/guides/CONTROL_PANEL_GUIDE.md)
- UPnP Guide: [docs/guides/UPNP_GUIDE.md](docs/guides/UPNP_GUIDE.md)
- Protocol Testing: [docs/testing/PROTOCOL_TESTING.md](docs/testing/PROTOCOL_TESTING.md)

---

Note: This is an active translation project. Many features from the original Java implementation are still being ported to Python. See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features and timeline.

Project status: Paused. See [docs/ROADMAP.md](docs/ROADMAP.md) for the latest status and how to resume.