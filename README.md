# PythonPlaySEM - Sensory Effect Media Framework

![CI](https://github.com/PhelaPoscam/Python_PlaySEM/workflows/CI/badge.svg)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PythonPlaySEM** is a versatile and extensible Python framework for orchestrating sensory effects across a wide range of devices and protocols. It provides a unified system for receiving, dispatching, and rendering effects like light, wind, vibration, and scent, making it ideal for immersive media, simulations, and interactive experiences.

This version is a Python-based implementation and expansion of the original Java-based PlaySEM framework developed by [Estevão Bissoli](https://github.com/estevaobissoli).

---

## ✨ Key Features & Recent Improvements

-   **Flexible Configuration**: Configure your devices using `.yaml`, `.json`, or even the original `.xml` format from the Java PlaySEM project.
-   **Flexible Device Payloads**: Communicate with devices using either **JSON** (recommended) or **XML** payloads, configurable per device.
-   **Multi-Driver Architecture**: Run multiple communication protocols (e.g., Serial, MQTT, Mock) simultaneously. The system automatically routes commands to the correct device.
-   **Extensible by Design**: A plug-and-play system for device communication. Easily add new hardware by creating a new driver.
-   **Protocol Ingestion**: The example server shows how to ingest effect commands from various protocols, including WebSocket, HTTP/REST, MQTT, CoAP, and UPnP.

> ### 📝 Connecting a New Device?
>
> For a step-by-step guide on connecting a new piece of hardware (like an Arduino), see the **[TUTORIAL.md](TUTORIAL.md)** file.

---

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

```bash
pip install -r requirements.txt
```
For development, you may also want to install development-specific tools:
```bash
pip install -r requirements-dev.txt
```

**4. Run the Core Application**

The main, refactored application entry point is `src/main.py`.

```bash
# This will run the application using the default config/devices.yaml
python src/main.py
```

The application will start, connect to all devices defined in your configuration file, and await commands from other parts of the system.

---

## Configuration

The application's device setup is highly flexible.

### Command-Line Configuration

You can specify which device configuration file to use via the command line. This is useful for testing or switching between setups.

```bash
# Run with the default YAML config
python src/main.py

# Run with a JSON config file
python src/main.py --devices-config config/my_devices.json

# Run with the original Java PlaySEM XML config
# The loader will automatically transform it for you.
python src/main.py --devices-config config/SERenderer.xml
```

### Device Configuration (`devices.yaml`)

This is the primary file for defining your devices and how to connect to them. It is split into two main sections: `devices` and `connectivityInterfaces`.

-   **`devices`**: A list of your hardware, giving each a unique `deviceId`.
-   **`connectivityInterfaces`**: Defines the communication channels (e.g., a specific serial port or MQTT broker).

#### Example: JSON vs. XML Payloads

You can control the data format sent to each device using the `dataFormat` field in the interface definition.

```yaml
devices:
  # This fan will receive JSON commands
  - deviceId: "json_fan"
    protocol: "serial"
    connectivityInterface: "serial_json_interface"

  # This fan will receive XML commands
  - deviceId: "xml_fan"
    protocol: "serial"
    connectivityInterface: "serial_xml_interface"

connectivityInterfaces:
  - name: "serial_json_interface"
    protocol: "serial"
    port: "COM3"
    baudrate: 9600
    dataFormat: "json"  # Explicitly JSON

  - name: "serial_xml_interface"
    protocol: "serial"
    port: "COM4"
    baudrate: 9600
    dataFormat: "xml"   # This interface will send XML
```

---

## How It Works

The framework follows a clean, decoupled data flow.

```
[Client] -> [Protocol Server] -> [Effect Dispatcher] -> [Device Manager] -> [Device Driver] -> [Hardware]
```

1.  **Configuration Loader**: At startup, `ConfigLoader` reads a configuration file (YAML, JSON, or XML) and creates a unified dictionary of all devices and interfaces.
2.  **Driver Factory**: `DriverFactory` creates instances of the necessary drivers (`SerialDriver`, `MQTTDriver`, etc.) based on the loaded configuration.
3.  **Device Manager**: This central component holds all active drivers. It knows which device is connected to which driver.
4.  **Effect Dispatcher & Protocol Servers**: Higher-level components (like those in the `examples` folder) can receive commands from the outside world (via HTTP, WebSockets, etc.) and use the `DeviceManager` to send a command to a specific `deviceId`, without needing to know how that device is connected.
5.  **Device Drivers**: The final layer that implements the specific logic to format the payload (JSON/XML) and communicate with the hardware.


## Examples and UI

The `examples/` directory contains a separate, more feature-rich server that includes a web-based UI, protocol servers, and more. To run it:

```bash
# Install the project in editable mode first
pip install -e .

# Run the example server
python examples/server/main.py
```
This will start a web server at `http://localhost:8090` which provides a control panel for managing the system. The features described below, such as the capabilities endpoint and mobile client, relate to this example server.

### Device Capabilities

Devices can advertise what effects they support. The example server exposes this via an endpoint.

-   **Endpoint**: `GET /api/capabilities/{device_id}` returns a JSON description.
-   **Test**: `curl http://localhost:8080/api/capabilities/mock_light_1 | jq .`

### Mobile Device Client

The example server can turn your smartphone into a sensory device.

1.  Find your PC's IP address.
2.  Start the example server: `python examples/server/main.py`.
3.  On your phone's browser, navigate to: `http://YOUR_PC_IP:8090/mobile_device`.
4.  Tap "Connect" - your phone will now appear in the device list!

See `docs/guides/MOBILE_PHONE_SETUP.md` for detailed setup.


## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=src --cov-report=html
```

### Testing Notes

- `tools/test_server` uses an ephemeral HTTP port for its REST API to avoid conflicts on Windows/CI. When the control server starts the HTTP protocol, it picks a free port automatically and logs it. Client calls inside the tests automatically discover and target the active port.
- CoAP on Windows: a small readiness delay is applied after binding to ensure the UDP socket is available before sending requests. This improves stability of CoAP smoke tests on Windows.

## License

This project is licensed under the MIT License.
