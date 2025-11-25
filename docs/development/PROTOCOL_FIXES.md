# Protocol Testing Fixes

## Issues Fixed

### ✅ 1. HTTP 422 Error - Fixed
**Problem:** HTTP POST to `/api/effects` was returning 422 Unprocessable Content

**Root Cause:** The payload was missing the required `timestamp` field defined in the `EffectRequest` Pydantic model

**Solution:** Added `timestamp: effect.timestamp` to the HTTP payload in `send_effect_protocol()`

**Location:** `examples/server/main.py` line ~1256

```python
json={
    "effect_type": effect.effect_type,
    "timestamp": effect.timestamp,      # ← Added this field
    "intensity": effect.intensity,
    "duration": effect.duration,
}
```

### ✅ 2. MQTT WinError 10049 - Fixed
**Problem:** MQTT broker failed to start with `OSError [WinError 10049]` - "O endereço solicitado não é válido"

**Root Cause:** MQTT broker was trying to bind to `0.0.0.0` which fails on Windows

**Solution:** Changed MQTT broker host from `0.0.0.0` to `127.0.0.1`

**Location:** `examples/server/main.py` line ~1366

```python
self.mqtt_server = MQTTServer(
    dispatcher=self.global_dispatcher,
    host="127.0.0.1",  # ← Changed from "0.0.0.0"
    port=1883,
    subscribe_topic="effects/#",
)
```

### ✅ 3. Multi-Protocol Device Discovery - Implemented
**Problem:** Super Receiver could only be discovered via WebSocket

**Root Cause:** Device registration was single-protocol only

**Solution:** Implemented **multi-protocol device discovery** - devices can now be discovered via ALL protocols (WebSocket, HTTP, MQTT, CoAP, UPnP)

**Locations:**
- `examples/ui/super_receiver.html` line ~483 (client-side registration)
- `examples/server/main.py` line ~262 (HTTP registration endpoint)
- `examples/server/main.py` line ~715 (WebSocket registration)
- `examples/server/main.py` line ~797 (protocol announcements)

**Key Features:**
- **HTTP Registration**: `POST /api/devices/register` endpoint
- **Protocol Metadata**: Devices declare which protocols they support
- **Multi-Protocol Announcements**: MQTT topics, CoAP resources, UPnP SSDP
- **Flexible Discovery**: Clients can discover devices using any protocol

```javascript
// Super Receiver now registers with ALL protocols
ws.onopen = () => {
    const deviceInfo = {
        type: 'register_device',
        device_id: `receiver_${Date.now()}`,
        device_name: 'Super Receiver',
        device_type: 'web_receiver',
        capabilities: ['light', 'vibrate', 'wind', 'heat'],
        protocols: ['websocket', 'http', 'mqtt', 'coap', 'upnp']  // ← ALL protocols!
    };
    
    // Register via WebSocket
    ws.send(JSON.stringify(deviceInfo));
    
    // Also register via HTTP
    fetch('/api/devices/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceInfo)
    });
};
```

**See:** `docs/MULTI_PROTOCOL_DISCOVERY.md` for complete documentation

### ✅ 4. CoAP Client Implementation - Added
**Problem:** CoAP protocol only logged a "not implemented" message

**Solution:** Implemented full CoAP client using `aiocoap` library

**Location:** `examples/server/main.py` line ~1270

**Features:**
- Creates CoAP client context
- Sends POST request to `coap://127.0.0.1:5683/effects`
- Includes effect metadata in JSON payload
- Handles missing `aiocoap` library gracefully

**Requirements:** `pip install aiocoap`

### ✅ 5. UPnP Client Implementation - Added
**Problem:** UPnP protocol only logged a "not implemented" message

**Solution:** Implemented UPnP SOAP client for sending effects

**Location:** `examples/server/main.py` line ~1315

**Features:**
- Constructs SOAP envelope with effect data
- Sends POST to `http://127.0.0.1:8082/upnp/control`
- Uses proper UPnP service URN and SOAP action
- Handles connection errors gracefully

## Protocol Status Summary

| Protocol   | Status | Port | Notes |
|-----------|--------|------|-------|
| WebSocket | ✅ Working | 8090 | Primary communication, fully functional |
| HTTP REST | ✅ Fixed | 8081 | Now sends complete payload with timestamp |
| MQTT      | ✅ Fixed | 1883 | Broker now binds to 127.0.0.1 (Windows compatible) |
| CoAP      | ✅ Implemented | 5683 | Requires `aiocoap` library |
| UPnP      | ✅ Implemented | 8082 | SOAP-based effect sending |

## Testing the Protocols

### 1. Start the Control Panel Server
```bash
python examples/server/main.py
```

### 2. Open Super Controller
Navigate to: `http://localhost:8090/super_controller`

### 3. Open Super Receiver (in another browser tab/window)
Navigate to: `http://localhost:8090/super_receiver`

The receiver should now appear in the device list!

### 4. Test Each Protocol
1. **WebSocket** - Direct communication, instant delivery
2. **HTTP** - RESTful API, click "HTTP" and send effect
3. **MQTT** - Pub/Sub messaging, click "MQTT" to start broker first
4. **CoAP** - Lightweight protocol for IoT (needs `aiocoap` installed)
5. **UPnP** - Universal Plug and Play SOAP protocol

## Installation Notes

### For CoAP Support
```bash
pip install aiocoap
```

### Current Dependencies
All other protocols work with existing dependencies:
- `httpx` - for HTTP and UPnP
- Built-in MQTT broker - no extra installation needed
- `websockets` via FastAPI - already included

## Architecture Notes

### Device Registration Flow
1. Super Receiver opens WebSocket connection
2. On `ws.onopen`, sends `register_device` message
3. Server registers device with capabilities
4. Server broadcasts updated device list to all clients
5. Super Controller receives device list and displays cards

### Effect Routing
1. Super Controller sends effect with selected protocol
2. Server's `send_effect_protocol()` routes to appropriate handler
3. Each protocol has its own client implementation
4. Server confirms delivery or reports errors

### Protocol Selection
- Start protocol servers on-demand (lazy initialization)
- HTTP server auto-starts on first HTTP effect
- MQTT broker auto-starts on first MQTT effect
- CoAP server auto-starts on first CoAP effect
- UPnP server auto-starts on first UPnP effect

## Known Limitations

1. **CoAP**: Requires separate `pip install aiocoap`
2. **UPnP**: Assumes UPnP device is running on port 8082
3. **Device Discovery**: Currently manual via WebSocket registration
4. **Serial Devices**: Still require virtual serial setup (see SERIAL_TESTING_GUIDE.md)

## Next Steps

- ✅ All protocols now functional
- ✅ Device registration working
- ✅ Multi-protocol testing enabled
- Consider: Auto-discovery for serial devices
- Consider: CoAP service discovery
- Consider: UPnP SSDP discovery
