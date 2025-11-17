# How to Test PlaySEM Control Panel with Protocol Servers

## What is PlaySEM?

PlaySEM is a **Sensory Effects Renderer (SER)** framework that delivers multi-sensory effects (wind, light, vibration, scent) synchronized with multimedia content. It's the Python port of the Java [PlaySEM framework](https://github.com/PhelaPoscam/PlaySEM).

### Architecture Overview

```
External Client (Video Player, Game, etc.)
         │
         │ sends SEM metadata via protocol
         ▼
Protocol Server (MQTT/CoAP/HTTP/UPnP)
         │
         │ parses effect metadata
         ▼
Effect Dispatcher
         │
         │ routes effects to devices
         ▼
Physical Devices (Fans, LEDs, Vibrators, etc.)
```

## Testing Steps

### 1. Start the Control Panel

```powershell
cd "C:\TUNI - Projects\Python Project\PythonPlaySEM"
.\.venv\Scripts\python.exe examples\control_panel\control_panel_server.py
```

You should see:
```
🌐 Server running at:
   📱 Control Panel: http://localhost:8090
   🔌 WebSocket: ws://localhost:8090/ws
```

### 2. Open Control Panel in Browser

Navigate to: http://localhost:8090

### 3. Connect Mock Devices (for testing without hardware)

In the control panel:
1. **Device Connection Type**: Select "Mock"
2. Click **"Scan Devices"**
3. You should see 3 mock devices appear:
   - Mock Light Device
   - Mock Wind Device  
   - Mock Vibration Device
4. Click **"Connect"** for each device

### 4. Test Effects via Control Panel (Manual Testing)

Try sending effects directly from the control panel:
1. Select a connected device from "Target Device" dropdown
2. Choose effect type (Light, Wind, Vibration)
3. Adjust intensity (0-100) and duration (ms)
4. Click **"Send Effect"**

Watch the **server console** - you should see:
```
[INFO] Mock device 'mock_light_1' received LIGHT command: intensity=80, duration=1000
```

### 5. Start Protocol Servers

Now let's enable external clients to send effects:

In the control panel, go to **"Protocol Servers"** section:
- Click **"Start"** on **MQTT Server** → Wait for "Running" status
- Click **"Start"** on **CoAP Server** → Wait for "Running" status
- Click **"Start"** on **HTTP REST API** → Wait for "Running" status
- Click **"Start"** on **UPnP Discovery** → Wait for "Running" status

## Testing with External Clients

### Option A: Test MQTT (Requires MQTT Broker)

**Step 1: Install and Run MQTT Broker**

Windows (Chocolatey):
```powershell
choco install mosquitto
mosquitto
```

Or use public broker: `test.mosquitto.org`

**Step 2: Send Effects via MQTT**

```powershell
# Send vibration effect
mosquitto_pub -h localhost -p 1883 -t "effects/vibration" -m '{
  "effect_type": "vibration",
  "intensity": 80,
  "duration": 1000,
  "timestamp": 0
}'

# Send light effect
mosquitto_pub -h localhost -p 1883 -t "effects/light" -m '{
  "effect_type": "light",
  "intensity": 100,
  "duration": 2000,
  "timestamp": 0
}'

# Send wind effect
mosquitto_pub -h localhost -p 1883 -t "effects/wind" -m '{
  "effect_type": "wind",
  "intensity": 60,
  "duration": 1500,
  "timestamp": 0
}'
```

**Watch for**:
- Control panel Activity Log shows received effect
- Server console shows mock device executing effect

---

### Option B: Test HTTP REST API (Easiest!)

The HTTP server runs independently on port 8080. No broker needed!

```powershell
# Send vibration effect
curl -X POST http://localhost:8080/api/effects `
  -H "Content-Type: application/json" `
  -d '{
    "effect_type": "vibration",
    "intensity": 80,
    "duration": 1000,
    "timestamp": 0
  }'

# Send light effect
curl -X POST http://localhost:8080/api/effects `
  -H "Content-Type: application/json" `
  -d '{
    "effect_type": "light",
    "intensity": 100,
    "duration": 2000,
    "timestamp": 0
  }'

# Check server status
curl http://localhost:8080/api/status

# Get connected devices
curl http://localhost:8080/api/devices
```

---

### Option C: Test CoAP (IoT Protocol)

**Install CoAP client**:
```powershell
npm install -g coap-cli
```

**Send effects**:
```powershell
# Send vibration effect
echo '{"effect_type":"vibration","intensity":70,"duration":800,"timestamp":0}' | coap post coap://localhost:5683/effects

# Send light effect
echo '{"effect_type":"light","intensity":90,"duration":1500,"timestamp":0}' | coap post coap://localhost:5683/effects
```

---

### Option D: Test WebSocket (Real-time Streaming)

**Note**: PlaySEM has **two separate WebSocket endpoints**:
- **Port 8090** (`/ws`): Control panel UI only (device management, configuration)
- **Port 8765**: WebSocket SEM Server for sending effects from external clients

**JavaScript Client Example**:
```javascript
// Create WebSocket connection to SEM server (not control panel!)
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('Connected to PlaySEM WebSocket server');
    
    // Send vibration effect
    ws.send(JSON.stringify({
        effect_type: "vibration",
        intensity: 80,
        duration: 1000,
        timestamp: 0
    }));
    
    // Send light effect
    ws.send(JSON.stringify({
        effect_type: "light",
        intensity: 100,
        duration: 2000,
        timestamp: 1000
    }));
};

ws.onmessage = (event) => {
    console.log('Received:', event.data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

**Python Client Example**:
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # Send vibration effect
        effect = {
            "effect_type": "vibration",
            "intensity": 80,
            "duration": 1000,
            "timestamp": 0
        }
        
        await websocket.send(json.dumps(effect))
        print(f"Sent: {effect}")
        
        # Wait for response
        response = await websocket.recv()
        print(f"Received: {response}")

# Run the test
asyncio.run(test_websocket())
```

**Install Python websockets library**:
```powershell
pip install websockets
```

---

### Option E: Test UPnP Discovery

**Discover PlaySEM on network**:

```python
# Run this Python script to discover PlaySEM devices
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

msg = 'M-SEARCH * HTTP/1.1\r\n' \
      'HOST:239.255.255.250:1900\r\n' \
      'ST:upnp:rootdevice\r\n' \
      'MX:2\r\n' \
      'MAN:"ssdp:discover"\r\n\r\n'

sock.sendto(msg.encode(), ('239.255.255.250', 1900))
sock.settimeout(3)

try:
    while True:
        data, addr = sock.recvfrom(2048)
        print(f"\nDiscovered device at {addr}:")
        print(data.decode())
except socket.timeout:
    print("\nDiscovery complete")
```

You should see PlaySEM server announce itself!

---

## Using Existing Demo Scripts

The project includes ready-to-use test clients in `examples/clients/`:

### Test HTTP Client
```powershell
.\.venv\Scripts\python.exe examples\clients\test_http_client.py
```

### Test WebSocket Client
```powershell
.\.venv\Scripts\python.exe examples\clients\test_websocket_client.py
```

### Test MQTT Client (requires broker)
```powershell
.\.venv\Scripts\python.exe examples\clients\test_mqtt_client_public.py
```

### Test CoAP Client
```powershell
.\.venv\Scripts\python.exe examples\clients\test_coap_client.py
```

### Test UPnP Discovery
```powershell
.\.venv\Scripts\python.exe examples\clients\test_upnp_client.py
```

---

## Understanding SEM Metadata

Effects are sent as **SEM (Sensory Effect Metadata)** in JSON format:

```json
{
  "effect_type": "vibration",   // or "light", "wind", "scent"
  "intensity": 80,               // 0-100 (percentage)
  "duration": 1000,              // milliseconds
  "timestamp": 0                 // playback time (0 = immediate)
}
```

**YAML format** is also supported:
```yaml
effect_type: vibration
intensity: 80
duration: 1000
timestamp: 0
```

---

## Troubleshooting

### "MQTT server does nothing"
- **Cause**: No MQTT broker running OR wrong broker address
- **Fix**: 
  1. Install mosquitto: `choco install mosquitto`
  2. Run `mosquitto` in separate terminal
  3. OR change broker address in code to `test.mosquitto.org`

### "Mock devices not appearing"
- **Cause**: Device scan failed
- **Fix**: Check server console for errors, try refreshing page

### "Protocol server shows 'Error'"
- **Cause**: Port already in use OR missing dependencies
- **Fix**: 
  - MQTT: Install `pip install paho-mqtt`
  - CoAP: Install `pip install aiocoap`
  - HTTP: Install `pip install fastapi uvicorn`
  - Check if ports 1883, 5683, 8080, 1900 are available

### "Effects not executing"
- **Cause**: No devices connected OR wrong effect format
- **Fix**: 
  1. Connect at least one mock device
  2. Verify JSON format matches SEM metadata structure
  3. Check server console for parsing errors

---

## Real-World Usage Example

Once you've tested with mock devices, you can:

1. **Replace mock devices with real hardware**:
   - Connect Arduino devices via Serial/USB
   - Connect Bluetooth devices (fans, LEDs, etc.)

2. **Integrate with multimedia applications**:
   - Video players can send effects via HTTP REST API
   - Games can send effects via WebSocket or MQTT
   - VR apps can use CoAP for low-latency effects

3. **Create synchronized mulsemedia experiences**:
   - Use `timestamp` field to sync effects with video playback
   - Multiple devices receive same effect simultaneously
   - Timeline-based effect sequences

---

## Next Steps

- **Read `PROTOCOL_TESTING.md`** for detailed protocol examples
- **Check `examples/demos/`** for standalone server examples
- **See original PlaySEM Java version** for comparison: https://github.com/PhelaPoscam/PlaySEM
- **Read research papers** in README.md for mulsemedia background

---

## Quick Test Script

Save this as `quick_test.py` and run it after starting the control panel:

```python
import requests
import time

# Send 3 different effects via HTTP
effects = [
    {"effect_type": "light", "intensity": 100, "duration": 1000, "timestamp": 0},
    {"effect_type": "wind", "intensity": 70, "duration": 1500, "timestamp": 1000},
    {"effect_type": "vibration", "intensity": 80, "duration": 500, "timestamp": 2500}
]

print("Sending effects to PlaySEM...")
for effect in effects:
    print(f"  → {effect['effect_type']} (intensity={effect['intensity']})")
    response = requests.post("http://localhost:8080/api/effects", json=effect)
    print(f"     Status: {response.status_code}")
    time.sleep(0.5)

print("\nDone! Check the control panel Activity Log.")
```

Run with:
```powershell
.\.venv\Scripts\python.exe quick_test.py
```

---

**Remember**: PlaySEM is a framework for delivering sensory effects to multimedia. The control panel lets you test the protocol servers that external applications (video players, games, VR apps) would use to send effects to your sensory devices!
