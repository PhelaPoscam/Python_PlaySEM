# Mobile Device Client Setup

Turn your smartphone into a sensory effect device that appears in the PythonPlaySEM control panel.

## Quick Start

### 1. Start the Control Panel Server

```powershell
cd "C:\TUNI - Projects\Python Project\PythonPlaySEM"
& .venv\Scripts\Activate.ps1
python -m examples.server.main
```

The server will start on `http://0.0.0.0:8090` by default.

### 2. Connect Your Phone

On your smartphone (connected to the same network):

1. **Find your PC's IP address** (on Windows PowerShell):
   ```powershell
   ipconfig
   ```
   Look for your IPv4 address (e.g., `192.168.1.100`)

2. **Open the mobile client** in your phone's browser:
   ```
   http://192.168.1.100:8090/mobile_device
   ```

3. **Configure and connect**:
   - Device Name: (auto-filled with your device model)
   - Server WebSocket URL: (auto-filled, e.g., `ws://192.168.1.100:8090/ws`)
   - Tap **Connect**

### 3. Test from the Control Panel

1. Open the Super Controller on your PC:
   ```
   http://localhost:8090/super_controller
   ```

2. Your phone will now appear in the **Device** dropdown as something like:
   ```
   web_mobile_abc123 (Android mobile / iPhone mobile)
   ```

3. Select your phone device and send effects:
   - **Light effects**: Screen changes color with specified intensity
   - **Vibration effects**: Phone vibrates (if browser supports Vibration API)
   - **Custom effects**: Screen feedback with visual cues

## Features

### Visual Feedback
- **Light effects**: Full-screen color display with intensity control
- **Vibration effects**: Red pulsing screen + physical vibration
- **Wind effects**: Blue pulsing animation
- **Custom effects**: Gray pulsing for unknown types

### Capabilities
The mobile client reports these capabilities when registering:
- `light` - Screen color display
- `vibration` - Physical vibration (browser-dependent)

### Connection Status
- **Connected (green)**: Device is registered and receiving effects
- **Disconnected (red)**: Not connected to server

### Activity Log
The bottom panel shows recent events:
- Connection status changes
- Effects received
- Errors and warnings

## Testing Effects

### From Super Controller
1. Select your mobile device from the dropdown
2. Choose an effect type (e.g., "light" or "vibration")
3. Adjust intensity (0-255) and duration (milliseconds)
4. For light effects, select a color
5. Click **Send Effect**

### From REST API
```powershell
# Send a light effect with green color
curl -X POST http://localhost:8090/api/effects `
  -H "Content-Type: application/json" `
  -d '{
    "effect_type": "light",
    "intensity": 200,
    "duration": 2000,
    "parameters": {"color": "#00FF00"}
  }'
```

### Via WebSocket (from another client)
```javascript
const ws = new WebSocket('ws://192.168.1.100:8090/ws');

ws.onopen = () => {
  // Send effect to specific device
  ws.send(JSON.stringify({
    type: 'send_effect',
    device_id: 'web_mobile_abc123',
    effect: {
      effect_type: 'vibration',
      intensity: 150,
      duration: 500
    }
  }));
};
```

## Device Registration Protocol

The mobile client sends this registration message when connecting:

```json
{
  "type": "register_device",
  "device_id": "web_mobile_abc123",
  "device_name": "iPhone mobile",
  "device_type": "web_client",
  "capabilities": ["light", "vibration"]
}
```

Server response:
```json
{
  "type": "device_registered",
  "device_id": "web_mobile_abc123",
  "message": "Registered as iPhone mobile"
}
```

## Effect Message Format

When effects are sent to the device, the mobile client receives:

```json
{
  "type": "effect",
  "effect_type": "light",
  "intensity": 200,
  "duration": 2000,
  "parameters": {
    "color": "#FF00FF"
  }
}
```

The client responds with an acknowledgment:
```json
{
  "type": "effect_ack",
  "device_id": "web_mobile_abc123",
  "effect_type": "light",
  "timestamp": 1700000000000
}
```

## Tips

### Keep Screen Active
The mobile client requests a wake lock to prevent the screen from sleeping during use. Grant permission when prompted for best results.

### Network Requirements
- Both PC and phone must be on the same local network
- Firewall must allow incoming connections on port 8090
- Some corporate or public WiFi networks may block WebSocket connections

### Browser Compatibility
- **Vibration API**: Chrome/Edge on Android, limited iOS support
- **Wake Lock**: Modern Chrome/Edge (80+), Safari (partial)
- **WebSocket**: All modern browsers

### Testing Locally
You can also test on the same PC:
```
http://localhost:8090/mobile_device
```

### Multiple Devices
Connect multiple phones simultaneously - each gets a unique device ID and appears in the device list independently.

## Troubleshooting

### Phone doesn't appear in device list
- Check that you clicked "Connect" on the mobile client
- Verify the WebSocket URL is correct
- Check browser console for errors (use remote debugging)

### Effects not displaying
- Ensure device is selected in Super Controller dropdown
- Check the mobile client's log panel for received effects
- Verify the effect type matches capabilities

### Connection drops
- Check WiFi signal strength
- Ensure phone doesn't enter sleep mode
- Re-connect manually if needed

### Can't find PC's IP address
Windows PowerShell:
```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Ethernet*"})[0].IPAddress
```

## Next Steps

- **Add more effect types**: Extend the mobile client to support custom effects
- **Implement feedback**: Send sensor data (accelerometer, light) back to server
- **Create patterns**: Combine multiple effects into sequences
- **Build native apps**: Use the same WebSocket protocol in iOS/Android apps

## Architecture

```
┌─────────────────┐                    ┌──────────────────┐
│   PC Server     │                    │  Mobile Phone    │
│  (port 8090)    │◄──────WebSocket────┤  (Browser)       │
│                 │                    │                  │
│ • Device List   │   register_device  │ • Auto-detect IP │
│ • Effect Router │────────────────────►│ • Visual Display │
│ • REST API      │   effect messages  │ • Vibration API  │
│ • Super Control │────────────────────►│ • Wake Lock      │
└─────────────────┘                    └──────────────────┘
```

The mobile client is a lightweight HTML5 web app with no installation required - just open the URL in your phone's browser!
