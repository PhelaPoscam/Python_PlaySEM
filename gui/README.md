# PlaySEM Control Panel (GUI)

The PlaySEM GUI is a desktop application built with PyQt6 and `qasync` to provide a real-time interface for orchestrating sensory effects.

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have the required dependencies installed:

```bash
pip install -e .
pip install PyQt6 qasync
```

### 2. Running the GUI

From the project root, run:

```bash
python gui/app.py
```

## 🎨 Features

- **Connection Panel**: Multi-protocol support (WebSocket, MQTT, HTTP, CoAP).
- **Control Plane**: Start/Stop protocol brokers on the remote server directly from the GUI.
- **Device Management**: Real-time discovery and selection of multi-protocol devices.
- **Effect Generator**: Interactive UI for sending intensities and durations.
- **History Log**: Track recent sensory output events.

## 🛠 Architecture

The GUI follows a Controller-UI pattern:

- `gui/app_controller.py`: Manages the `asyncio` loop and backend communication.
- `gui/ui/`: Contains modular PyQt6 widgets for each panel.
- `gui/protocols/`: Protocol-specific client implementations.
