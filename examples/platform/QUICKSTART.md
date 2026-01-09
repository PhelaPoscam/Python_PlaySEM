# Quickstart Guide - Modular Server

Get started with the PlaySEM modular server architecture in 5 minutes.

## 1. Run Basic Server

```bash
# Terminal 1: Start the server
python examples/platform/basic_server.py

# Terminal 2: Test the API
curl http://localhost:8090/health
curl http://localhost:8090/api/devices
```

**Expected Output:**
```json
{"status": "ok"}
{"devices": [], "connected_count": 0}
```

## 2. Connect a Device

```bash
# Connect a mock device
curl -X POST http://localhost:8090/api/devices/connect \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "vibrator_001",
    "driver_type": "mock",
    "config": {}
  }'
```

## 3. Send an Effect

```bash
# Send vibration effect
curl -X POST http://localhost:8090/api/effects/send \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "vibrator_001",
    "effect": "haptic",
    "parameters": {
      "intensity": 0.8,
      "duration": 1000,
      "pattern": "pulse"
    }
  }'
```

## 4. WebSocket Real-Time Updates

```javascript
// In browser console or JavaScript
const ws = new WebSocket('ws://localhost:8090/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Server event:', data);
};

// Send a command
ws.send(JSON.stringify({
  type: 'effect',
  device_id: 'vibrator_001',
  effect: 'haptic',
  parameters: {intensity: 0.5}
}));
```

## 5. Custom Handler (MQTT)

```bash
# Terminal 1: Start MQTT broker
mosquitto -v

# Terminal 2: Start server with MQTT
python examples/platform/custom_handler_server.py

# Terminal 3: Subscribe to device status
mosquitto_sub -t "playsem/devices/+/status"

# Terminal 4: Publish effect command
mosquitto_pub -t "playsem/devices/vibrator_001/effects" \
  -m '{"effect":"haptic","intensity":0.8}'
```

## Architecture at a Glance

```
examples/platform/basic_server.py
    ↓
tools/test_server/app/main.py (create_app factory)
    ↓
┌─────────────────────────────────────┐
│ FastAPI App                         │
├─────────────────────────────────────┤
│ Services (app.state)                │
│  ├─ DeviceService                   │
│  ├─ EffectService                   │
│  ├─ TimelineService                 │
│  └─ ProtocolService                 │
├─────────────────────────────────────┤
│ Routes                              │
│  ├─ /api/devices/* (DeviceRoutes)   │
│  ├─ /api/effects/* (EffectRoutes)   │
│  └─ /ws (UIRoutes)                  │
├─────────────────────────────────────┤
│ Handlers                            │
│  ├─ WebSocketHandler                │
│  └─ MQTTHandler (optional)          │
└─────────────────────────────────────┘
```

## Next Steps

- **Customize**: Edit `ServerConfig` for different ports/hosts
- **Extend**: Add custom handlers (see `custom_handler_server.py`)
- **Production**: Use `production_server.py` template
- **Testing**: Check `tests/integration/` for examples

## Common Issues

**Port already in use:**
```bash
# Change port in ServerConfig or via env var
PLAYSEM_PORT=8091 python examples/platform/basic_server.py
```

**Device not connecting:**
```bash
# Check device_id and driver_type are correct
# Verify config/devices.yaml has the device defined
```

**MQTT not working:**
```bash
# Install mosquitto: sudo apt install mosquitto mosquitto-clients
# Or use Docker: docker run -p 1883:1883 eclipse-mosquitto
```

## Resources

- Full API docs: http://localhost:8090/docs (when server is running)
- Architecture: `README.md` in this directory
- Phase 3D Report: `docs/archive/PHASE_3D_COMPLETE.md`
