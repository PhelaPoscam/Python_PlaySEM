# PlaySEM - Sensory Effect Media Framework

[![CI](https://github.com/PhelaPoscam/Python_PlaySEM/actions/workflows/ci.yml/badge.svg)](https://github.com/PhelaPoscam/Python_PlaySEM/actions)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**PlaySEM** is a powerful Python framework for orchestrating sensory effects across diverse devices and protocols. Control lights, haptics, wind, and scent through a unified, asynchronous API.

---

## ✨ Features

- 🔌 **Universal Protocols**: MQTT, WebSocket, CoAP, UPnP, and Serial.
- 🎯 **Unified Registry**: Cross-protocol device discovery with optional isolation.
- 🧩 **Extensible drivers**: plug-and-play support for any hardware.
- 🔒 **Concurrence-safe**: Built for high-performance, multi-client scenarios.

## 🚀 Quick Start

### Installation

```bash
pip install -e .
```

### Minimal Example

```python
import asyncio
from playsem import DeviceManager, EffectMetadata

async def main():
    manager = DeviceManager()
    await manager.initialize("config/devices.yaml")
    
    # Unleash a sensory effect
    effect = EffectMetadata(effect_type="vibration", intensity=100)
    await manager.send_effect("my-device-id", effect)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📖 Essential Docs

For detailed guides and API references, check out:

- 📘 **[Library Documentation](docs/LIBRARY.md)** — Complete API reference.
- ⚙️ **[Core Usage Guide](docs/guides/core_guide.md)** — Setup, testing, and protocol notes.

---

## 🧪 Testing the Framework

### Run All Tests

```bash
pytest tests/ -v
```

### Test Individual Protocols

#### WebSocket

```bash
# Terminal 1: Start WebSocket server
python -c "
import asyncio
from playsem import DeviceManager, EffectDispatcher
from playsem.protocol_servers import WebSocketServer

async def main():
    dm = DeviceManager(client=type('Mock', (), {'publish': lambda *a: None})())
    dispatcher = EffectDispatcher(dm)
    server = WebSocketServer(host='127.0.0.1', port=8765, dispatcher=dispatcher)
    await server.start()
    await asyncio.sleep(60)

asyncio.run(main())
"

# Terminal 2: Connect client
python -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://127.0.0.1:8765') as ws:
        await ws.send(json.dumps({'type': 'effect', 'effect_type': 'vibration', 'intensity': 80, 'duration': 500}))
        print(await ws.recv())

asyncio.run(test())
"
```


#### HTTP

```bash
# Start test server
python tools/test_server/main.py

# Test endpoints
curl -X POST http://localhost:8090/api/devices/register -H "Content-Type: application/json" -d '{"device_id":"test","device_type":"vibration","protocols":["http"]}'
curl -X POST http://localhost:8090/api/effects/send -H "Content-Type: application/json" -d '{"device_id":"test","effect":{"effect_type":"vibration","intensity":80}}'
```

#### UPnP

```bash
pytest tests/protocols/test_upnp_server.py -v
```

#### MQTT (External Public Broker)

```bash
python -c "
import paho.mqtt.client as mqtt
import asyncio

def on_message(client, userdata, msg):
    print(f'Topic: {msg.topic} | Payload: {msg.payload}')

client = mqtt.Client()
client.on_message = on_message
client.connect('test.mosquitto.org', 1883)
client.subscribe('playsem/test/#')
client.loop_start()
asyncio.sleep(30)
"
```

#### MQTT (Embedded Broker)

```bash
pytest tests/protocols/test_mqtt_broker.py -v
```

#### All Protocol Tests

```bash
pytest tests/protocols/ -v
```

---


## 🛠 Ecosystem

- **[Platform Server](tools/test_server/)**: A modular REST/WebSocket backend.
- **[PlaySEM GUI](gui/)**: Interactive control panel for real-time orchestration.
- **[Examples](examples/)**: Ready-to-run demonstration scripts.

---

## 📝 License & Acknowledgments

- **License**: MIT
- **Origins**: Based on the original Java PlaySEM by [Estevão Bissoli](https://github.com/estevaobissoli).

Immersive sensory experiences, simplified. 🌍✨
