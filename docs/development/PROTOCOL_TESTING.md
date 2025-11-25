# Protocol Server Testing Guide

This document was moved here from examples/control_panel/PROTOCOL_TESTING.md to consolidate testing documentation under docs/testing/.

Below is the original content preserved in full.

---

# Protocol Server Testing Guide

This guide explains how to test the different protocol servers available in PlaySEM's control panel.

## Overview

The control panel allows you to start/stop protocol servers that external applications can use to send effects to PlaySEM devices. This enables you to test how external clients (mobile apps, web apps, IoT devices) would interact with your PlaySEM system.

## Available Protocol Servers

### 1. MQTT Server (Port 1883)

**Purpose**: Message queue for asynchronous effect delivery

**How to Test**:
1. Click "Start" on MQTT Server in the control panel
2. Use an MQTT client (mosquitto_pub, MQTT Explorer, or Python paho-mqtt)

**Example using mosquitto_pub**:
```bash
# Install mosquitto client (if not installed)
# Windows: Download from https://mosquitto.org/download/
# Linux: sudo apt-get install mosquitto-clients
# Mac: brew install mosquitto

# Send a vibration effect
mosquitto_pub -h localhost -p 1883 -t "playsem/effect" -m '{"effect_type":"vibration","intensity":80,"duration":1000}'

# Send a light effect
mosquitto_pub -h localhost -p 1883 -t "playsem/effect" -m '{"effect_type":"light","intensity":100,"duration":2000}'
```

**Example using Python**:
```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("localhost", 1883, 60)

# Send vibration effect
effect = {
    "effect_type": "vibration",
    "intensity": 80,
    "duration": 1000
}
client.publish("playsem/effect", json.dumps(effect))
client.disconnect()
```

---

### 2. CoAP Server (Port 5683)

**Purpose**: Constrained Application Protocol for IoT devices (lightweight alternative to HTTP)

**How to Test**:
1. Click "Start" on CoAP Server in the control panel
2. Use a CoAP client (coap-cli or Python aiocoap)

**Example using coap-cli**:
```bash
# Install coap-cli
npm install -g coap-cli

# Send a vibration effect
echo '{"effect_type":"vibration","intensity":60,"duration":500}' | coap post coap://localhost/effect

# Send a wind effect
echo '{"effect_type":"wind","intensity":70,"duration":1500}' | coap post coap://localhost/effect
```

**Example using Python**:
```python
import asyncio
from aiocoap import Context, Message, POST
import json

async def send_effect():
    context = await Context.create_client_context()
    
    effect = {
        "effect_type": "vibration",
        "intensity": 60,
        "duration": 500
    }
    
    request = Message(
        code=POST,
        uri='coap://localhost/effect',
        payload=json.dumps(effect).encode('utf-8')
    )
    
    response = await context.request(request).response
    print(f'Response: {response.payload.decode()}')

asyncio.run(send_effect())
```

---

### 3. HTTP REST API (Port 8080)

**Purpose**: Standard HTTP REST API for web applications

**How to Test**:
1. Click "Start" on HTTP REST API in the control panel
2. Use curl, Postman, or any HTTP client

**Example using curl**:
```bash
# Send a vibration effect
curl -X POST http://localhost:8080/api/effect \
  -H "Content-Type: application/json" \
  -d '{"effect_type":"vibration","intensity":80,"duration":1000}'

# Send a light effect
curl -X POST http://localhost:8080/api/effect \
  -H "Content-Type: application/json" \
  -d '{"effect_type":"light","intensity":100,"duration":2000}'

# Get server status
curl http://localhost:8080/api/status
```

**Example using Python**:
```python
import requests
import json

# Send effect
effect = {
    "effect_type": "vibration",
    "intensity": 80,
    "duration": 1000
}

response = requests.post(
    "http://localhost:8080/api/effect",
    json=effect
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

**Example using JavaScript**:
```javascript
// Send effect using fetch
fetch('http://localhost:8080/api/effect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    effect_type: 'vibration',
    intensity: 80,
    duration: 1000
  })
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

---

### 4. UPnP Discovery (SSDP Multicast)

**Purpose**: Universal Plug and Play device discovery for automatic detection on local networks

**How to Test**:
1. Click "Start" on UPnP Discovery in the control panel
2. Use a UPnP discovery tool or Python script

**Example using Python**:
```python
import socket

# Create UDP socket for SSDP discovery
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# SSDP discovery message
msg = \
    'M-SEARCH * HTTP/1.1\r\n' \
    'HOST:239.255.255.250:1900\r\n' \
    'ST:upnp:rootdevice\r\n' \
    'MX:2\r\n' \
    'MAN:"ssdp:discover"\r\n' \
    '\r\n'

# Send discovery request
sock.sendto(msg.encode(), ('239.255.255.250', 1900))

# Receive responses (timeout after 3 seconds)
sock.settimeout(3)
try:
    while True:
        data, addr = sock.recvfrom(2048)
        print(f"\nReceived from {addr}:")
        print(data.decode())
except socket.timeout:
    print("\nDiscovery complete")
```

---

## Testing Workflow

### Basic Testing Steps:

1. **Start the Control Panel**:
   ```bash
   python examples/control_panel/control_panel_server.py
   ```

2. **Open the Control Panel in Browser**:
   - Navigate to http://localhost:8090

3. **Connect Mock Devices** (for testing without hardware):
   - Select "Mock" from Device Connection Type
   - Click "Scan Devices"
   - Connect to one or more mock devices

4. **Start Protocol Server(s)**:
   - In the "Protocol Servers" section, click "Start" on the protocol you want to test
   - Wait for status to change to "Running"

5. **Send Test Effects**:
   - Use one of the client examples above to send effects via your chosen protocol
   - Watch the Activity Log in the control panel to see effects being received and executed

6. **Verify Effects**:
   - Mock devices will log effect execution to the server console
   - Real devices (Bluetooth/Serial) will execute the actual effect

---

## Troubleshooting

### MQTT Server won't start
- **Error**: Port 1883 already in use
- **Solution**: Stop any existing MQTT broker (Mosquitto, HiveMQ, etc.) or change the port in `control_panel_server.py`

### CoAP Server won't start
- **Error**: Port 5683 requires admin privileges on some systems
- **Solution**: Run the control panel with admin/root privileges or use a port > 1024

### HTTP Server won't start
- **Error**: Port 8080 already in use
- **Solution**: Stop other applications using port 8080 or change the port

### UPnP Discovery not working
- **Issue**: No responses to SSDP discovery
- **Solution**: 
  - Check firewall settings (SSDP uses multicast UDP)
  - Ensure you're on the same network
  - Verify multicast is enabled on your network interface

### Effects not executing
- **Check**: Are devices connected in the control panel?
- **Check**: Is the effect format correct (JSON with effect_type, intensity, duration)?
- **Check**: Are you sending to the correct endpoint/topic?

---

## Protocol Comparison

| Protocol | Use Case | Pros | Cons |
|----------|----------|------|------|
| **MQTT** | Async messaging, pub/sub patterns | Lightweight, QoS levels, persistent connections | Requires broker |
| **CoAP** | IoT devices with limited resources | Very lightweight, UDP-based | Less mature ecosystem |
| **HTTP** | Web apps, standard REST APIs | Universal support, easy to use | More overhead |
| **UPnP** | Auto-discovery on local networks | Zero-config discovery | LAN only |

---

## Advanced: Multi-Protocol Testing

You can run multiple protocol servers simultaneously to test how different types of clients interact with PlaySEM:

1. Start all protocol servers
2. Send effects from different clients (MQTT, HTTP, CoAP)
3. Monitor the Activity Log to see all effects being processed
4. Compare latency and reliability across protocols

**Example Multi-Client Test Script (Python)**:
```python
import asyncio
import requests
import paho.mqtt.client as mqtt
from aiocoap import Context, Message, POST
import json

async def test_all_protocols():
    effect = {
        "effect_type": "vibration",
        "intensity": 70,
        "duration": 800
    }
    
    # Test HTTP
    print("Testing HTTP...")
    response = requests.post("http://localhost:8080/api/effect", json=effect)
    print(f"HTTP: {response.status_code}")
    
    # Test MQTT
    print("Testing MQTT...")
    mqtt_client = mqtt.Client()
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.publish("playsem/effect", json.dumps(effect))
    mqtt_client.disconnect()
    print("MQTT: Published")
    
    # Test CoAP
    print("Testing CoAP...")
    context = await Context.create_client_context()
    request = Message(
        code=POST,
        uri='coap://localhost/effect',
        payload=json.dumps(effect).encode()
    )
    response = await context.request(request).response
    print(f"CoAP: {response.code}")

asyncio.run(test_all_protocols())
```

---

## Next Steps

- **Integrate with Mobile App**: Use MQTT or HTTP to connect mobile apps
- **IoT Integration**: Use CoAP for low-power IoT devices
- **Network Discovery**: Use UPnP to auto-discover PlaySEM on the network
- **Load Testing**: Test how many concurrent effects your system can handle
- **Security**: Add authentication to protocol servers for production use
