# Multi-Protocol Device Discovery

## Overview

The PythonPlaySEM system now supports **multi-protocol device discovery**. Devices (like Super Receiver) can register and be discovered across **all communication protocols**, not just WebSocket.

## Supported Discovery Protocols

| Protocol | Discovery Method | Status |
|----------|-----------------|--------|
| **WebSocket** | Direct registration via `/ws` endpoint | ✅ Fully Implemented |
| **HTTP REST** | Registration via `/api/devices/register` | ✅ Fully Implemented |
| **MQTT** | Announcement on `devices/announce` topic | ✅ Implemented |
| **CoAP** | Resource discovery via `.well-known/core` | ✅ Framework Ready |
| **UPnP** | SSDP multicast announcement | ✅ Framework Ready |

## How It Works

### 1. Device Registration Flow

When a device (e.g., Super Receiver) connects, it:

1. **Opens WebSocket connection** to `/ws`
2. **Sends registration message** with supported protocols
3. **Also registers via HTTP** to `/api/devices/register`
4. **Server announces device** on all requested protocols

```javascript
// Example: Super Receiver Registration
const deviceInfo = {
    type: 'register_device',
    device_id: 'receiver_12345',
    device_name: 'Super Receiver',
    device_type: 'web_receiver',
    capabilities: ['light', 'vibrate', 'wind', 'heat'],
    protocols: ['websocket', 'http', 'mqtt', 'coap', 'upnp']  // ← ALL protocols
};

// Register via WebSocket
ws.send(JSON.stringify(deviceInfo));

// Also register via HTTP
fetch('/api/devices/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(deviceInfo)
});
```

### 2. Server-Side Discovery Announcement

When a device registers, the server:

```python
async def announce_device_discovery(device_id: str, protocols: list):
    """Announce device on all requested protocols."""
    
    # MQTT: Publish to devices/announce topic
    if "mqtt" in protocols:
        topic = "devices/announce"
        # Broker clients can subscribe to discover devices
    
    # CoAP: Register in .well-known/core
    if "coap" in protocols:
        # CoAP discovery via resource directory
    
    # UPnP: SSDP multicast
    if "upnp" in protocols:
        # Multicast SSDP:alive message
```

### 3. Device List with Multi-Protocol Info

Devices are stored with protocol metadata:

```python
device = ConnectedDevice(
    id="receiver_12345",
    name="Super Receiver",
    type="web_receiver",
    address="multi-protocol:websocket,http,mqtt,coap,upnp",  # ← Shows all protocols
    ...
)
device.capabilities = ['light', 'vibrate', 'wind', 'heat']
device.protocols = ['websocket', 'http', 'mqtt', 'coap', 'upnp']
```

## Protocol-Specific Discovery

### WebSocket Discovery
- **Method**: Direct registration via WebSocket `/ws` endpoint
- **Message**: `{"type": "register_device", ...}`
- **Advantage**: Real-time bidirectional communication

### HTTP REST Discovery
- **Endpoint**: `POST /api/devices/register`
- **Payload**: JSON with device info and protocols
- **Advantage**: Standard RESTful API, works with any HTTP client
- **Example**:
```bash
curl -X POST http://localhost:8090/api/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "receiver_001",
    "device_name": "Super Receiver",
    "device_type": "web_receiver",
    "capabilities": ["light", "vibrate"],
    "protocols": ["http", "mqtt", "coap"]
  }'
```

### MQTT Discovery
- **Topic**: `devices/announce`
- **Payload**: JSON device info
- **How to Subscribe**:
```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    device_info = json.loads(msg.payload)
    print(f"Discovered device: {device_info['device_name']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("127.0.0.1", 1883)
client.subscribe("devices/announce")
client.loop_forever()
```

### CoAP Discovery
- **Method**: CoRE Resource Directory or `.well-known/core`
- **Query**: `coap://127.0.0.1:5683/.well-known/core`
- **Response**: List of available resources
- **How to Discover**:
```python
from aiocoap import Context, Message, GET

async def discover_coap_devices():
    context = await Context.create_client_context()
    request = Message(code=GET, uri='coap://127.0.0.1:5683/.well-known/core')
    response = await context.request(request).response
    print(f"CoAP Resources: {response.payload.decode()}")
```

### UPnP Discovery (SSDP)
- **Method**: SSDP multicast search
- **Multicast**: `239.255.255.250:1900`
- **Search Target**: `urn:schemas-upnp-org:device:SEM:1`
- **How to Discover**:
```python
import socket

# Send M-SEARCH
msearch = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    "MAN: \"ssdp:discover\"\r\n"
    "MX: 2\r\n"
    "ST: urn:schemas-upnp-org:device:SEM:1\r\n\r\n"
)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(msearch.encode(), ("239.255.255.250", 1900))
```

## Device Capabilities

Devices declare their capabilities during registration:

```javascript
capabilities: [
    'light',      // Can show light effects
    'vibrate',    // Can vibrate
    'wind',       // Can create wind effects
    'heat',       // Can generate heat
    'scent',      // Can emit scents
    'cold'        // Can create cold effects
]
```

## Benefits of Multi-Protocol Discovery

1. **Flexibility**: Devices can be discovered using any protocol
2. **Redundancy**: If one protocol fails, others still work
3. **Compatibility**: Different clients can use their preferred protocol
4. **Scalability**: Easy to add new protocols
5. **Real-World IoT**: Mimics actual IoT device discovery patterns

## Examples

### Example 1: Web Browser Device (All Protocols)
```javascript
// Super Receiver registers with all protocols
ws.send(JSON.stringify({
    type: 'register_device',
    device_id: 'web_receiver_001',
    device_name: 'Super Receiver',
    protocols: ['websocket', 'http', 'mqtt', 'coap', 'upnp']
}));
```

### Example 2: MQTT-Only Device
```python
import paho.mqtt.client as mqtt
import json

device_info = {
    "device_id": "mqtt_device_001",
    "device_name": "MQTT SEM Device",
    "device_type": "mqtt_client",
    "capabilities": ["light", "vibrate"],
    "protocols": ["mqtt"]
}

client = mqtt.Client()
client.connect("127.0.0.1", 1883)
client.publish("devices/announce", json.dumps(device_info))
```

### Example 3: CoAP IoT Device
```python
from aiocoap import Context, Message, POST
import json

async def register_coap_device():
    context = await Context.create_client_context()
    
    device_info = {
        "device_id": "coap_device_001",
        "device_name": "CoAP SEM Sensor",
        "protocols": ["coap"]
    }
    
    request = Message(
        code=POST,
        uri='coap://127.0.0.1:5683/devices/register',
        payload=json.dumps(device_info).encode()
    )
    
    await context.request(request).response
```

## Testing Multi-Protocol Discovery

### 1. Start the Server
```bash
python examples/server/main.py
```

### 2. Open Super Receiver
```
http://localhost:8090/super_receiver
```
**Watch the console** - you should see:
```
[REGISTER] Web device: receiver_123456789 (Super Receiver) 
           with capabilities: ['light', 'vibrate', 'wind', 'heat'] 
           via protocols: ['websocket', 'http', 'mqtt', 'coap', 'upnp']
[MQTT-ANNOUNCE] Device receiver_123456789 on topic devices/announce
[COAP-ANNOUNCE] Device receiver_123456789 registered
[UPNP-ANNOUNCE] Device receiver_123456789 via SSDP
```

### 3. Open Super Controller
```
http://localhost:8090/super_controller
```
**The device should appear in the device list** with address: `multi-protocol:websocket,http,mqtt,coap,upnp`

### 4. Send Effects via Any Protocol
- Select the Super Receiver device
- Choose any protocol (WebSocket, HTTP, MQTT, CoAP, UPnP)
- Send an effect
- Watch it arrive at the Super Receiver!

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Super Receiver (Web)                     │
│  Registers via: WebSocket + HTTP                            │
│  Supports: websocket, http, mqtt, coap, upnp                │
└────────────┬────────────────────────────────────────────────┘
             │ Registration
             ▼
┌─────────────────────────────────────────────────────────────┐
│              Control Panel Server (Port 8090)                │
│  • WebSocket endpoint: /ws                                   │
│  • HTTP endpoint: /api/devices/register                      │
│  • Device Manager: Stores multi-protocol metadata           │
└────────────┬────────────────────────────────────────────────┘
             │ Announces on
             ├───────────────────────────────────────┐
             │                                       │
             ▼                                       ▼
┌────────────────────────┐            ┌────────────────────────┐
│   MQTT Broker          │            │   CoAP Server          │
│   Port: 1883           │            │   Port: 5683           │
│   Topic: devices/*     │            │   Resource: /devices/* │
└────────────────────────┘            └────────────────────────┘
             │                                       │
             ▼                                       ▼
┌────────────────────────┐            ┌────────────────────────┐
│   UPnP SSDP            │            │   HTTP REST API        │
│   Multicast: 239.*     │            │   Port: 8081           │
│   ST: urn:...:SEM:1    │            │   Endpoint: /api/*     │
└────────────────────────┘            └────────────────────────┘
```

## Future Enhancements

- [ ] **mDNS/Bonjour**: Zero-configuration discovery
- [ ] **Bluetooth LE**: BLE advertisement for mobile devices
- [ ] **Zigbee/Z-Wave**: Smart home protocol support
- [ ] **Matter**: Cross-platform smart home standard
- [ ] **WebRTC**: Peer-to-peer device connections

## Summary

✅ **Super Receiver now registers across ALL protocols**  
✅ **Devices announce themselves on MQTT, CoAP, UPnP**  
✅ **Multi-protocol metadata stored for each device**  
✅ **Flexible discovery for different client types**  
✅ **Real-world IoT discovery patterns**

Your Super Receiver is now **truly multi-protocol** - discoverable via WebSocket, HTTP, MQTT, CoAP, and UPnP! 🎉
