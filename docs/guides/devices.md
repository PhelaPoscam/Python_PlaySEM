# Device Management Guide

## Overview

The PythonPlaySEM system supports multiple device types and discovery methods.

---

## Device Types

### 1. Mock Devices (Testing)

Built-in devices for testing without hardware.

**Available Mock Devices**:

| Name | Address | Type | Capabilities |
|------|---------|------|--------------|
| Mock Light Device | `mock_light_1` | Light | Color, intensity (0-100%), duration |
| Mock Vibration Device | `mock_vibration_1` | Vibration | Intensity (0-100%), duration |
| Mock Wind Device | `mock_wind_1` | Wind | Intensity (0-100%), duration |

**How to Use**:
1. Backend automatically serves mock devices
2. GUI → Devices tab → Click "Scan Devices"
3. Mock devices appear in 2-3 seconds
4. Click to select, then send effects

### 2. Real Hardware Devices

Connect actual hardware to your system.

#### Bluetooth Devices

**Requirements**:
- `bleak` library (installed)
- Bluetooth adapter
- Compatible device (sensors, lights, etc.)

**Discovery**:
```
GUI → Devices → Scan Devices
Select Bluetooth driver
Nearby devices appear
```

#### Serial/USB Devices

**Requirements**:
- `pyserial` library (installed)
- USB-to-Serial adapter (if needed)
- Device with serial protocol

**Configuration**:
```yaml
# config/devices.yaml
serial_device:
  name: "Arduino LED Controller"
  driver: serial
  port: "COM3"  # Windows: COM3, Linux: /dev/ttyUSB0
  baudrate: 9600
  payload_format: "json"
```

**Discovery**:
```
GUI → Devices → Scan Devices
Select Serial driver
Available ports appear
```

#### MQTT Devices

**Requirements**:
- MQTT broker (e.g., Mosquitto)
- `paho-mqtt` library (installed)

**Configuration**:
```yaml
# config/devices.yaml
mqtt_device:
  name: "IoT Light Bulb"
  driver: mqtt
  broker: "192.168.1.100"
  port: 1883
  topic: "home/light/1"
  payload_format: "json"
```

**Discovery**:
```
Backend automatically discovers via MQTT subscriptions
Devices appear in GUI device list
```

### 3. HTTP-Registered Devices

Register custom devices via REST API.

**REST Endpoint**:
```bash
POST http://127.0.0.1:8090/api/devices/register
Content-Type: application/json

{
  "device_id": "my_light_1",
  "device_name": "My Custom Light",
  "device_type": "http_client",
  "capabilities": ["Light", "Vibration"],
  "protocols": ["http"],
  "connection_mode": "direct"
}
```

**Response**:
```json
{
  "success": true,
  "device_id": "my_light_1",
  "message": "Registered via HTTP with protocols: ['http']"
}
```

**Using Curl**:
```bash
curl -X POST http://127.0.0.1:8090/api/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "my_device",
    "device_name": "My Device",
    "device_type": "http_client",
    "capabilities": ["Light"],
    "protocols": ["http"],
    "connection_mode": "direct"
  }'
```

---

## Device Lifecycle

### States

```
Discovered (scanning)
    ↓
Selected (in GUI)
    ↓
Connected (has active connection)
    ↓
Active (can receive effects)
    ↓
Disconnected (manual or error)
```

### Operations

#### Scan for Devices
```
Devices Tab → "Scan Devices" button → Wait 2-3 seconds
```

#### Select Device
```
Click device in list → Selected state shows in Effects tab
```

#### Send Effect
```
Effects Tab → Configure parameters → Click "Send Effect"
```

#### Disconnect Device
```
Device Tab → Select device → Connection Tab → "Disconnect"
```

---

## Effect Types & Parameters

### Light Effects

**Parameters**:
- **Type**: "Light"
- **Intensity**: 0-100% (brightness)
- **Duration**: 0-60000ms
- **Color**: RGB (e.g., #FF0000 for red)

**Example**:
```json
{
  "device_id": "mock_light_1",
  "effect_type": "Light",
  "intensity": 75,
  "duration": 2000,
  "color": "#FF5733"
}
```

### Vibration Effects

**Parameters**:
- **Type**: "Vibration"
- **Intensity**: 0-100% (strength)
- **Duration**: 0-60000ms
- **Pattern**: Optional (e.g., "pulse", "continuous")

**Example**:
```json
{
  "device_id": "mock_vibration_1",
  "effect_type": "Vibration",
  "intensity": 80,
  "duration": 1500
}
```

### Wind Effects

**Parameters**:
- **Type**: "Wind"
- **Intensity**: 0-100% (speed)
- **Duration**: 0-60000ms
- **Direction**: Optional (e.g., "left", "right", "forward")

**Example**:
```json
{
  "device_id": "mock_wind_1",
  "effect_type": "Wind",
  "intensity": 60,
  "duration": 3000
}
```

---

## Testing Workflow

### Quick Test (1 minute)
```
1. Scan devices
2. Select Mock Light Device
3. Set intensity 75%, duration 2000ms
4. Click Send Effect
5. Watch status bar: "Sent: Light"
```

### Protocol Test (2 minutes)
```
1. Connect via WebSocket
2. Send effect
3. Disconnect
4. Switch to HTTP protocol
5. Connect and send another effect
6. Verify both work
```

### Stability Test (5 minutes)
```
1. Connect to backend
2. Rapidly switch protocols
3. Send multiple effects
4. Disconnect and reconnect
5. Verify no crashes
```

---

## Troubleshooting

### Devices Don't Appear After Scan

**Problem**: Click "Scan Devices" but nothing appears

**Solutions**:
1. ✅ Backend is running: `python examples/server/main.py`
2. ✅ Status is green (connected)
3. ✅ Wait 3 seconds (takes time to scan)
4. ✅ Check terminal for errors
5. ✅ Try scanning again

### Serial Device Not Found

**Problem**: Serial port doesn't appear during scan

**Solutions**:
1. ✅ Device is plugged in
2. ✅ Drivers installed (CH340, FTDI, etc.)
3. ✅ Check Device Manager (Windows) for COM ports
4. ✅ Try different USB cable/port
5. ✅ Restart device and scan again

**Find COM Port**:
```powershell
# PowerShell
[System.IO.Ports.SerialPort]::GetPortNames()

# Or use Device Manager
# Ports (COM & LPT) → Look for your device
```

### Bluetooth Device Not Discovered

**Problem**: Bluetooth device doesn't appear in scan

**Solutions**:
1. ✅ Device is powered on
2. ✅ Device is in pairing mode
3. ✅ Bluetooth adapter enabled on PC
4. ✅ Within Bluetooth range (typically 10m)
5. ✅ Not paired with another device
6. ✅ Try scanning again

### Effect Send Fails

**Problem**: "Send Effect" shows error

**Solutions**:
1. ✅ Device is **selected** (highlighted in list)
2. ✅ Status is **green** (connected)
3. ✅ Backend is **running**
4. ✅ Check **terminal output** for errors
5. ✅ Try sending again

### MQTT Device Not Connecting

**Problem**: MQTT device not discovered

**Solutions**:
1. ✅ MQTT broker is running
2. ✅ Broker address is correct
3. ✅ Port 1883 is accessible
4. ✅ Topic names match configuration
5. ✅ Check firewall rules
6. ✅ Check terminal for MQTT errors

---

## Configuration Files

### Device Configuration

**File**: `config/devices.yaml`

```yaml
# Example device configuration
devices:
  light_1:
    name: "Main Light"
    driver: serial
    port: COM3
    baudrate: 9600
    
  vibration_1:
    name: "Haptic Motor"
    driver: mqtt
    broker: localhost
    topic: "haptic/motor1"
```

### Driver Selection

Drivers are auto-detected during scanning. Priority:
1. Bluetooth devices
2. Serial ports
3. MQTT topics
4. Mock devices (fallback)

---

## Advanced: Custom Devices

### Creating a Custom Mock Device

**File**: `src/device_driver/mock_driver.py`

```python
class MockCustomDevice:
    def __init__(self, address):
        self.address = address
        self.device_type = "custom"
        
    async def send_effect(self, effect):
        print(f"Custom device received: {effect}")
```

### Registering Custom Device

1. Add to `scan_mock()` in backend
2. Update device list
3. Test with GUI

---

## Integration Examples

### Example 1: Light + Vibration Sequence

```python
effects = [
    {"effect_type": "Light", "intensity": 100, "duration": 1000},
    {"effect_type": "Vibration", "intensity": 75, "duration": 1000},
    {"effect_type": "Light", "intensity": 50, "duration": 1000},
]

for effect in effects:
    await send_effect(device_id, effect)
    await asyncio.sleep(1.1)  # Wait for effect to complete
```

### Example 2: Multi-Device Effect

```python
devices = ["mock_light_1", "mock_vibration_1", "mock_wind_1"]

effect = {
    "effect_type": "Light",
    "intensity": 80,
    "duration": 2000
}

for device_id in devices:
    await send_effect(device_id, effect)
```

---

## Best Practices

✅ **Do**:
- Test with mock devices first
- Verify connectivity before sending effects
- Check logs for errors
- Use appropriate intensities (avoid 100% constantly)
- Disconnect cleanly when done

❌ **Don't**:
- Leave backend running indefinitely
- Send overlapping effects to same device
- Use invalid COM ports
- Force close GUI (let it exit cleanly)
- Ignore error messages

---

## See Also

- `GETTING_STARTED.md` - Quick start guide
- `TESTING.md` - Manual testing checklist
- `STATUS.md` - Current application status
- `../README.md` - Full project documentation

---

*Device Management Guide - Last updated: December 9, 2025*
