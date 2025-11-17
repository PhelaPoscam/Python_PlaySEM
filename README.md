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

## 📁 Project Structure

```
PythonPlaySEM/
├── src/                        # Core application code
│   ├── config_loader.py        # XML/YAML configuration parser
│   ├── device_manager.py       # Device communication manager
│   ├── effect_dispatcher.py    # Effect routing logic
│   ├── effect_metadata.py      # Metadata parsing
│   ├── protocol_server.py      # Communication protocols
│   ├── timeline.py             # Timeline scheduler
│   ├── main.py                 # Application entry point
│   └── device_driver/          # Device connectivity drivers
│       ├── mock_driver.py      # Mock devices for testing
│       └── serial_driver.py    # Serial/USB driver (Phase 3)
├── tests/                      # Unit and integration tests
├── examples/
│   ├── demos/                  # Demo applications
│   ├── clients/                # Test client scripts
│   └── web/                    # HTML/web interfaces
├── docs/                       # Documentation
├── config/                     # Configuration files
│   ├── devices.yaml
│   └── effects.yaml
├── .vscode/                    # VS Code settings
├── pyproject.toml              # Modern Python project config
├── requirements.txt            # Dependencies
└── README.md
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

### Basic Example

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

### Demos

Run these from the project root (PowerShell examples):

- **WebSocket server + HTML client** (ws://localhost:8765):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\websocket_server_demo.py
   start examples\web\websocket_client.html
   ```
   Tip: The HTML client includes fields for URL and optional auth token.

- **MQTT public-broker demos** (test.mosquitto.org):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\mqtt_server_demo_public.py
   .\.venv\Scripts\python.exe examples\clients\test_mqtt_client_public.py
   ```

- **CoAP server and client** (coap://localhost:5683):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\coap_server_demo.py
   .\.venv\Scripts\python.exe examples\clients\test_coap_client.py
   ```

- **HTTP REST server** (http://localhost:8080):
   ```powershell
   .\.venv\Scripts\python.exe examples\demos\http_server_demo.py
   # Health
   curl http://localhost:8080/api/status
   # Submit effect
   curl -X POST http://localhost:8080/api/effects ^
     -H "Content-Type: application/json" ^
     -d '{"effect_type":"light","intensity":200,"duration":1000}'
   # Devices (requires API key if enabled)
   curl -H "X-API-Key: your_secret_key" http://localhost:8080/api/devices
   ```

- **UPnP device discovery** (SSDP multicast):
   ```powershell
   # Start UPnP server (advertises on network)
   .\.venv\Scripts\python.exe examples\demos\upnp_server_demo.py
   
   # Discover PlaySEM devices on network
   .\.venv\Scripts\python.exe examples\clients\test_upnp_client.py
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

Detailed guides are available in the `docs/` folder:
- **[ROADMAP.md](docs/ROADMAP.md)**: Project phases and future plans
- **[TESTING.md](docs/TESTING.md)**: Testing strategy and coverage
- **[UPNP_GUIDE.md](docs/UPNP_GUIDE.md)**: UPnP/SSDP implementation details
- **[CONTROL_PANEL_GUIDE.md](docs/CONTROL_PANEL_GUIDE.md)**: WebSocket control panel usage
- **[PHASE2_COMPLETION.md](docs/PHASE2_COMPLETION.md)**: Phase 2 completion report
- **[INTEGRATION_TESTING.md](docs/INTEGRATION_TESTING.md)**: Integration testing guide
 - **[PHASE2_ENHANCEMENTS.md](docs/PHASE2_ENHANCEMENTS.md)**: Auth + HTTP REST details

---

**Note**: This is an active translation project. Many features from the original Java implementation are still being ported to Python. See `docs/ROADMAP.md` for planned features and timeline.
 
Project status: Paused. See `docs/ROADMAP.md` for the latest status and how to resume.
