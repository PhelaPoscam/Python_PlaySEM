# Quick Start - Testing PlaySEM Protocols

## What You're Testing

PlaySEM receives **sensory effect metadata** (like subtitles for your senses) and triggers physical devices. External apps (video players, games) send effects via MQTT/HTTP/CoAP/UPnP.

## 3-Minute Test

### 1. Start Server
```powershell
cd "C:\TUNI - Projects\Python Project\PythonPlaySEM"
.\.venv\Scripts\python.exe examples\control_panel\control_panel_server.py
```

### 2. Open Browser
http://localhost:8090

### 3. Connect Mock Devices
- Device Connection Type: **Mock**
- Click **"Scan Devices"**
- Click **"Connect"** on all 3 devices

### 4. Test HTTP Protocol (Easiest!)

Start HTTP server in control panel, then:

```powershell
# Send vibration effect
curl -X POST http://localhost:8081/api/effects `
  -H "Content-Type: application/json" `
  -d '{"effect_type":"vibration","intensity":80,"duration":1000,"timestamp":0}'
```

**Watch**: Server console shows `Mock device received VIBRATION command`

### 5. Test WebSocket (Real-time Streaming)

Start WebSocket SEM Server in control panel, then run:

```powershell
.\.venv\Scripts\python.exe examples\clients\test_websocket_client.py
```

**Note**: Two WebSocket ports - 8090 (control panel UI), 8765 (SEM effects)

### 6. Test MQTT (Uses Public Broker)

Start MQTT server in control panel (connects to test.mosquitto.org), then:

```powershell
mosquitto_pub -h test.mosquitto.org -p 1883 -t "effects/light" `
  -m '{"effect_type":"light","intensity":100,"duration":2000,"timestamp":0}'
```

**Note**: Using public test broker. For production, install local Mosquitto.

## What's Happening?

```
External Client
    ↓ (sends JSON effect metadata)
Protocol Server (HTTP/MQTT/CoAP/UPnP)
    ↓ (parses effect)
Effect Dispatcher
    ↓ (routes to device)
Mock Device (logs to console)
```

## Effect Format (SEM Metadata)

```json
{
  "effect_type": "vibration",  // or "light", "wind", "scent"
  "intensity": 80,             // 0-100
  "duration": 1000,            // milliseconds
  "timestamp": 0               // when to trigger (0=now)
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| MQTT connection refused | Now uses public test.mosquitto.org (no local install needed) |
| HTTP port conflict | Now uses port 8081 (8080 is for control panel) |
| CoAP bind error | Now uses 127.0.0.1 instead of 0.0.0.0 |
| No mock devices | Select "Mock" type, click "Scan Devices" |

## See Also

- **HOW_TO_TEST.md** - Detailed testing guide
- **PROTOCOL_TESTING.md** - All protocol examples
- **examples/clients/** - Ready-to-use test scripts
