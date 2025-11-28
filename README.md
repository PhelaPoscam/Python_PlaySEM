# PythonPlaySEM - Sensory Effect Media Framework

![CI](https://github.com/PhelaPoscam/Python_PlaySEM/workflows/CI/badge.svg)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PythonPlaySEM** is a versatile and extensible Python framework for orchestrating sensory effects across a wide range of devices and protocols. It provides a unified system for receiving, dispatching, and rendering effects like light, wind, vibration, and scent, making it ideal for immersive media, simulations, and interactive experiences.

This version is a Python-based implementation and expansion of the original Java-based PlaySEM framework developed by [Estevão Bissoli](https://github.com/estevaobissoli).

## Core Features

-   **Multi-Protocol Support**: Ingests effect commands from a variety of standard protocols, including:
    -   **WebSocket**: For low-latency, real-time web applications.
    -   **HTTP/REST**: For simple integration with web services.
    -   **MQTT**: For robust IoT and distributed system communication.
    -   **CoAP**: For lightweight, constrained-device networks.
    -   **UPnP/SSDP**: For automatic discovery and control on local networks.
-   **Extensible Driver Architecture**: A plug-and-play system for device communication. Easily add new hardware by creating a new driver.
    -   **Built-in Drivers**: Includes drivers for **Serial (Arduino, etc.)**, **Bluetooth Low Energy (BLE)**, **MQTT**, and a **Mock Driver** for testing.
-   **Advanced Timeline & Synchronization**: A precise, multi-threaded scheduler for playing back complex sequences of effects synchronized with media like video or audio. Supports play, pause, resume, and seek operations.
-   **Web-Based Control Panel**: A powerful, out-of-the-box web interface for managing the entire system. Features include:
    -   Live device scanning (Bluetooth, Serial) and connection management.
    -   Starting and stopping all protocol servers.
    -   Manually triggering effects on connected devices.
    -   Uploading and controlling effect timelines (XML, JSON, YAML).
-   **Configuration-Driven**: Easily map effects to devices and define custom parameters using simple YAML configuration files.

## Project Structure

The project is organized into several key directories:

-   `src/`: Contains the core framework source code.
-   `examples/`: Contains example code and applications.
    -   `server/`: The main server application.
    -   `ui/`: HTML files for the web-based user interfaces.
    -   `clients/`: Example client scripts for various protocols.
    -   `demos/`: Standalone scripts for demonstrating specific features.
    -   `docs/`: Documentation related to the examples.
    -   `data/`: Sample data files.
-   `docs/`: Project-level documentation.
-   `tests/`: Unit and integration tests.

## Getting Started

**1. Clone the Repository**

```bash
git clone <your-repo-url>
cd PythonPlaySEM
```

**2. Create and Activate a Virtual Environment**

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**

For production/running the application:
```bash
pip install -r requirements.txt
```

For development (includes testing, linting, and formatting tools):
```bash
pip install -r requirements-dev.txt
```

**4. Install the Project in Editable Mode**

This crucial step makes the `src` package available to the rest of the project, including examples and tests.

```bash
pip install -e .
```

**5. Run the Server**

```bash
python examples/server/main.py
```

Now, open your web browser and navigate to **`http://localhost:8090`**. This will open the main controller interface.

## How It Works

The framework follows a clean, decoupled data flow, making it easy to understand, extend, and maintain.

```
[Client] -> [Protocol Server] -> [Effect Dispatcher] -> [Device Manager] -> [Device Driver] -> [Hardware]
```

1.  **Protocol Servers**: Listen for incoming effect requests via various protocols (e.g., WebSocket, MQTT).
2.  **Effect Dispatcher**: Receives a standardized `EffectMetadata` object and uses `effects.yaml` to determine which device should handle the effect.
3.  **Device Manager**: Abstracts the hardware by holding a reference to the active `Device Driver`. It forwards the command to the driver.
4.  **Device Drivers**: The final layer that implements the specific logic to communicate with the hardware (e.g., writing to a serial port, sending a BLE packet).

### Supported Protocols

The system can be controlled via any of the following protocols, which can be enabled from the Control Panel UI:

| Protocol    | Default Port | Description                               |
| :---------- | :----------- | :---------------------------------------- |
| WebSocket   | 8765         | Real-time effect streaming                |
| HTTP/REST   | 8081         | Standard REST API for effects             |
| MQTT        | 1883         | Embedded broker for IoT integration       |
| CoAP        | 5683         | Lightweight protocol for constrained devices |
| UPnP        | 1900 (SSDP)  | LAN device discovery and control          |

### Device Drivers

Device drivers are the bridge to the physical hardware. The following drivers are included:

-   **`SerialDriver`**: For devices connected via a serial/COM port (e.g., Arduino).
-   **`BluetoothDriver`**: For connecting to Bluetooth Low Energy (BLE) devices.
-   **`MQTTDriver`**: For controlling devices that are themselves MQTT clients.
-   **`MockDriver`**: A software-only driver for testing and development without hardware.

## Examples

The `examples/` directory is structured to provide a clear separation of concerns:

-   **`server/`**: Contains the main server application (`main.py`) that runs the web interface and protocol servers.
-   **`ui/`**: Holds the HTML files for the web-based interfaces, including the main controller and receiver pages.
-   **`clients/`**: A collection of Python scripts demonstrating how to send effects to the server using different protocols.
-   **`demos/`**: Standalone scripts that showcase specific functionalities, such as individual drivers or servers.
-   **`docs/`**: Documentation specific to the examples.
-   **`data/`**: Sample data, such as the `sample_timeline.xml` for the timeline player.

## Device Capabilities

Devices advertise what effects and parameters they support so clients can adapt at runtime.

- Endpoint: `GET /api/capabilities/{device_id}` returns a JSON description.
- UI: Open `/ui/capabilities` to pick a device and view its capabilities.

Example response (abridged):

```json
{
    "device_id": "mock_light_1",
    "effects": [
        {
            "effect_type": "light",
            "parameters": [
                {"name": "intensity", "type": "int", "min": 0, "max": 255, "default": 128},
                {"name": "duration", "type": "int", "min": 1, "max": 60000, "default": 1000},
                {"name": "color", "type": "string", "format": "#RRGGBB", "default": "#FFFFFF"}
            ]
        }
    ]
}
```

Quick test:

```bash
curl http://localhost:8080/api/capabilities/mock_light_1 | jq .
```

## Mobile Device Client

Turn your smartphone into a sensory device that appears in the control panel!

**Quick Start:**

1. Find your PC's IP address (Windows):
   ```powershell
   ipconfig
   ```

2. Add firewall rule (run PowerShell as Administrator):
   ```powershell
   netsh advfirewall firewall add rule name="PythonPlaySEM" dir=in action=allow protocol=TCP localport=8090
   ```

3. Start the server:
   ```powershell
   python examples/server/main.py
   ```

4. On your phone's browser, navigate to:
   ```
   http://YOUR_PC_IP:8090/mobile_device
   ```

5. Tap "Connect" - your phone appears in the device list!

**Features:**
- 📱 Visual feedback for light effects (full-screen color display)
- 📳 Physical vibration for vibration effects
- 🔄 Real-time WebSocket communication
- 📊 Activity log and connection status
- 🔋 Wake lock to prevent screen sleep
- ✅ No app installation needed - just a web browser

See `docs/mobile_device_setup.md` for detailed setup and troubleshooting.

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=src --cov-report=html
```

All 76 tests should pass, validating:
- Device drivers (Serial, Bluetooth, MQTT, Mock)
- Protocol servers (HTTP, WebSocket, MQTT, CoAP, UPnP)
- Effect dispatching and routing
- Timeline synchronization
- Device capabilities
- Web client registration

## Configuration

### TODO
- Add automated smoke tests for `api/connect` and `api/effect` and integrate them into CI as lightweight checks; see `tests/test_smoke_protocols.py` (smoke tests) for a starting reference.

Configuration files are in the `config/` directory:

- `devices.yaml`: Device addresses and connection settings
- `effects.yaml`: Effect-to-device routing rules

Example device configuration:

```yaml
devices:
  light_strip:
    driver: serial
    port: COM5
    baud_rate: 115200
  
  phone_vibrator:
    driver: bluetooth
    address: "AA:BB:CC:DD:EE:FF"
```

## Architecture

The framework is built on several key principles:

1. **Protocol Agnostic**: Effects can be triggered from any protocol
2. **Device Agnostic**: Any device can be added via a driver
3. **Timeline Support**: Complex sequences with precise timing
4. **Real-time Capable**: Low-latency WebSocket for live effects
5. **Web-First**: Modern web UI for control and monitoring

For detailed architecture documentation, see `docs/CONTROL_PANEL_ARCHITECTURE.md`.

## Contributing

Contributions are welcome! Please see:
- `docs/CONVENTIONS.md` for coding standards
- `docs/ROADMAP.md` for planned features
- `docs/DEVICE_TESTING_CHECKLIST.md` for testing guidelines

## License

This project is licensed under the MIT License.

## Acknowledgments

Based on the original [PlaySEM framework](https://github.com/estevaobissoli) by Estevão Bissoli.
