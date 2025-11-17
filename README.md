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

## 🚀 Current Status (Paused)

This project is paused as of November 12, 2025. The repo is in a stable state with runnable demos and tests for the core communication services.

### ✅ Implemented
- Configuration Loader: XML and YAML parsers (`config_loader.py`)
- Device Manager: MQTT-based device communication
- Effect Dispatcher: Maps high-level effects to device commands
- Effect Metadata: JSON/YAML parsing to typed dataclass
- WebSocket Server: Async server + HTML client demo
- MQTT Server: Subscribes to `effects/#`; public-broker demos included
- CoAP Server: aiocoap-based `POST /effects` endpoint + client demo
- Tests: Unit + integration tests (WebSocket, MQTT, CoAP)

### �️ Next When Resumed
- UPnP discovery (Phase 2 final step)
- Serial/Bluetooth drivers (Phase 3)
- Timeline scheduler, delay compensation, MPEG-V XML parser

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
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

- WebSocket server + HTML client (ws://localhost:8765):
   ```powershell
   .\.venv\Scripts\python.exe examples\websocket_server_demo.py
   start examples\websocket_client.html
   ```

- MQTT public-broker demos (test.mosquitto.org):
   ```powershell
   .\.venv\Scripts\python.exe examples\mqtt_server_demo_public.py
   .\.venv\Scripts\python.exe examples\test_mqtt_client_public.py
   ```

- CoAP server and client (coap://localhost:5683):
   ```powershell
   .\.venv\Scripts\python.exe examples\coap_server_demo.py
   .\.venv\Scripts\python.exe examples\test_coap_client.py
   ```

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

## 📄 License

[Specify your license here - consider matching the original PlaySEM license]

## 🙏 Acknowledgments

This project is based on the PlaySEM Sensory Effects Renderer framework developed by the LPRM research group. Special thanks to the original authors for their groundbreaking work in mulsemedia systems.

## 📧 Contact

[Your contact information or project maintainer details]

---

**Note**: This is an active translation project. Many features from the original Java implementation are still being ported to Python. See the roadmap in issues for planned features and timeline.
 
Project status: Paused. See `ROADMAP.md` for the latest status and how to resume.
