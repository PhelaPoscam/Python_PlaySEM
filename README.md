# PythonPlaySEM - Sensory Effect Media Framework

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

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

```bash
pip install -r requirements.txt
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

## Contributing

Contributions are welcome! Please see the `docs/CONVENTIONS.md` for coding standards and refer to the `docs/ROADMAP.md` for planned features and future development goals.