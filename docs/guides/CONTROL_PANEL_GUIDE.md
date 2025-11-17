# 🎮 Control Panel Quick Start Guide

## What is this?

A web-based control panel that lets you:
- Choose between WebSocket, MQTT, or CoAP protocols
- Configure server connection settings
- Send sensory effects (light, wind, vibration, scent)
- Adjust intensity and duration with sliders
- See real-time activity logs

## 🚀 Quick Start (WebSocket - Canonical PlaySEM Flow)

Important: This guide describes the *canonical* PlaySEM flow. Use the `examples/demos/*` servers and `examples/web/websocket_client.html` for minimal end-to-end testing. The `examples/control_panel` folder contains a richer FastAPI control panel for advanced device discovery and management — it is not required for basic tests.

### Step 1: Start the canonical server (recommended)
```powershell
& 'C:\TUNI - Projects\Python Project\PythonPlaySEM\.venv\Scripts\python.exe' examples\demos\unified_server_demo.py
```

You should see:
```
============================================================
Servers Running:
============================================================
✅ WebSocket: ws://localhost:8765
⚠️  MQTT:      localhost:1883 (topics: effects/#)
✅ CoAP:      coap://localhost:5683/effects

Control Panel:
   → Open: examples/control_panel.html
```

### Step 2: Open the control panel
```powershell
start examples\web\control_panel.html
```

Or double-click `examples/control_panel.html` in File Explorer.

### Step 3: Connect and test
1. Click **"Connect"** button (WebSocket is selected by default)
2. You should see "✅ Connected to WebSocket server" in the log
3. Click any effect button (💡 Light, 💨 Wind, etc.) — this sends an `effect` JSON object to the server and the server forwards it to any connected DeviceManager/driver.
4. Adjust intensity/duration sliders
5. Watch the server terminal for received effects

## 🎯 Canonical Features & Quick Use

Use these components when you want to test PlaySEM quickly and reliably:

- `examples/demos/websocket_server_demo.py` — Lightweight WebSocket server that integrates with PlaySEM Dispatcher/DeviceManager
- `examples/web/websocket_client.html` — Minimal browser client that connects to WebSocket server and sends effects

For advanced device discovery and live device management, use:

- `examples/control_panel/control_panel_server.py` + `examples/control_panel/control_panel.html` — Full feature FastAPI server and UI for discovery (BLE/Serial/MQTT), connection, and effect testing

Tip: `examples/web/phone_tester.html` is a convenience page for verifying the Web Vibration API on your phone; it is not required to test PlaySEM end-to-end.

### Protocol Selection
- **WebSocket**: Best for browser-based apps (fully supported)
- **MQTT**: For IoT devices (requires broker, not available in browser)
- **CoAP**: For constrained devices (not available in browser)

### Effect Controls
- **4 Effect Types**: Light, Wind, Vibration, Scent
- **Intensity Slider**: 0-100
- **Duration Slider**: 100-5000ms
- **Location**: Optional spatial positioning

### Keyboard Shortcuts (when connected)
- `L` - Trigger Light effect
- `W` - Trigger Wind effect
- `V` - Trigger Vibration effect
- `S` - Trigger Scent effect

### Activity Log
Real-time log showing:
- Connection events
- Sent effects
- Received responses
- Errors and warnings

## 📊 What You'll See

**In the control panel:**
```
[14:30:25] Connecting to ws://localhost:8765...
[14:30:25] ✅ Connected to WebSocket server
[14:30:30] ✅ Sent light effect (intensity: 80, duration: 1000ms)
[14:30:30] Received: {"type":"response","success":true,...}
```

**In the server terminal:**
```
14:30:25 - [INFO] 🔗 Client connected: 127.0.0.1:52341
14:30:30 - [INFO] ✓ Received effect: light (intensity=80, duration=1000ms)
```

## 🔧 Advanced: MQTT Setup

If you want to test MQTT (optional):

1. **Install Mosquitto broker:**
   ```powershell
   choco install mosquitto
   ```

2. **Start broker:**
   ```powershell
   mosquitto
   ```

3. **Restart unified server** - it will detect the broker automatically

Note: MQTT in browser requires a WebSocket bridge, which is complex to set up. The control panel shows this as unavailable.

## 🛠️ Troubleshooting

### "Connection refused" error
- Make sure `unified_server_demo.py` is running
- Check that port 8765 is not blocked by firewall
- Verify the URL is `ws://localhost:8765` (not `http://`)

### Effects not sending
- Ensure you clicked "Connect" first
- Check the activity log for error messages
- Verify server is still running in the terminal

### Page not loading
- Use a modern browser (Chrome, Firefox, Edge)
- Check browser console (F12) for JavaScript errors
- Try refreshing the page

## 📁 Files

 - `examples/control_panel/control_panel.html` - Full-feature UI (FastAPI)
- `examples/demos/unified_server_demo.py` - Server that runs all protocols
- `examples/demos/websocket_server_demo.py` - WebSocket only
- `examples/demos/coap_server_demo.py` - CoAP only
- `examples/demos/mqtt_server_demo_public.py` - MQTT only

## 🎓 Tips

1. **Keep the server terminal visible** - you'll see effects as they arrive
2. **Use keyboard shortcuts** - faster than clicking buttons
3. **Adjust sliders while connected** - changes apply to next effect
4. **Check the activity log** - helpful for debugging
5. **Try different intensities/durations** - see how they affect behavior

## 🚀 Next Steps

- Integrate with Unity/Unreal game engine (use WebSocket protocol)
- Connect real hardware devices (fans, LEDs, etc.)
- Add custom effects in `config/effects.yaml`
- Build your own control interface using the same protocol
- Add timeline/sequence support for complex effect patterns

---

**Enjoy testing your mulsemedia system! 🎉**
