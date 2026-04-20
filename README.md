# PlaySEM - Sensory Effect Media Framework

[![CI](https://github.com/PhelaPoscam/Python_PlaySEM/actions/workflows/ci.yml/badge.svg)](https://github.com/PhelaPoscam/Python_PlaySEM/actions)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PlaySEM** is a Python framework for orchestrating sensory effects across diverse devices and protocols. Control lights, haptics, wind, and scent through a unified, asynchronous API.

---

## ✨ Features

- 🔌 **Universal Protocols**: MQTT, WebSocket, CoAP, UPnP, and Serial.
- 🎯 **Unified Registry**: Cross-protocol device discovery with optional isolation.
- 🧩 **Observational Drivers**: Built-in mock drivers with command journaling for high-fidelity testing.
- 🧪 **System Orchestration**: Unified test fixtures for end-to-end signal verification.
- 🔒 **Concurrence-safe**: Built for high-performance, multi-client scenarios.

## 🚀 Quick Start

### Installation

```bash
# Minimal installation (core only)
pip install -e .

# Full installation (all protocols: MQTT, Bluetooth, CoAP, etc.)
pip install -e ".[all]"
```

### Minimal Example

```python
import asyncio
from playsem import DeviceManager, EffectMetadata
from playsem.config.loader import ConfigLoader

async def main():
    # Load configuration
    loader = ConfigLoader(devices_path="config/devices.yaml")
    manager = DeviceManager(config_loader=loader)
    
    # Unleash a sensory effect
    effect = EffectMetadata(effect_type="vibration", intensity=100)
    manager.send_effect("my-device-id", effect)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📖 Essential Docs

For detailed guides and API references, check out:

- 📘 **[Library Documentation](docs/LIBRARY.md)** — Complete API reference.
- ⚙️ **[Core Usage Guide](docs/guides/core_guide.md)** — Setup, testing, and protocol notes.

---

## 🧪 High-Fidelity Testing

PlaySEM prioritizes "Observational Testing" over complex mocking. Our `playsem_system` fixture boots a full stack (Broker -> Dispatcher -> Manager -> Driver) in-process.

### Run End-to-End Scenarios

```bash
# Run the high-fidelity integration suite
pytest tests/integration/test_system_scenarios.py -v
```

### Verifying Signal Propagation

Instead of mocking function calls, we inspect the "journal" of the mock hardware:

```python
def test_signal(playsem_system):
    # 1. Send an effect via any protocol (e.g., MQTT)
    # 2. Inspect the mock driver's history
    history = playsem_system.mock_driver.command_history
    assert any(cmd["command"] == "set_intensity" for cmd in history)
```

### Protocol-Specific Tests

```bash
# All Protocol Servers
pytest tests/protocols/ -v

# Unit Tests
pytest tests/unit/ -v
```

---

## 🛠 Ecosystem

- **[Platform Server](tools/test_server/)**: A modular REST/WebSocket/MQTT backend for testing external integrations.
- **[Examples](examples/)**: Ready-to-run demonstration scripts for every supported protocol.

---

## 📝 License & Acknowledgments

- **License**: MIT
- **Origins**: Based on the original Java PlaySEM by [Estevão Bissoli](https://github.com/estevaobissoli).

Immersive sensory experiences, simplified. 🌍✨
