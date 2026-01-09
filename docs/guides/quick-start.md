# Getting Started with PythonPlaySEM GUI

## Quick Start (5 minutes)

### Prerequisites
- Python 3.14+
- Virtual environment (`.venv`)
- Backend server running

### Step 1: Start the Backend Server

```powershell
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python -m tools.test_server.main_new
```

**Expected output**:
```
INFO: Started server process [XXXX]
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8090
```

### Step 2: Start the GUI Application

Open a new terminal:

```powershell
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python -m gui.app
```

**Expected output**:
```
14:43:17 - [INFO] __main__ - Starting PythonPlaySEM GUI Application
14:43:18 - [INFO] __main__ - GUI application started successfully
```

A window titled "PythonPlaySEM Control Panel" should appear.

### Step 3: Connect & Test

1. **Connection Tab** → Click "Connect"
   - Status should show "Connected" (green indicator)

2. **Devices Tab** → Click "Scan Devices"
   - 3 mock devices should appear:
     - Mock Light Device
     - Mock Vibration Device
     - Mock Wind Device

3. **Select a Device** → Click "Mock Light Device"

4. **Effects Tab** → Configure and click "Send Effect"
   - Status bar shows: "Sent: Light"

5. **Done!** ✅ Your first effect was sent

---

## Architecture Overview

### Application Layers

```
┌─────────────────────────────────────┐
│   PyQt6 GUI Application             │
│   (gui/ui/main_window.py)           │
├─────────────────────────────────────┤
│   Application Controller            │
│   (gui/app_controller.py)           │
├─────────────────────────────────────┤
│   Protocol Abstraction              │
│   ├── WebSocketProtocol             │
│   └── HTTPProtocol                  │
├─────────────────────────────────────┤
│   Backend Server (FastAPI)          │
│   (tools/test_server/main_new.py)   │
├─────────────────────────────────────┤
│   Device Management                 │
│   (playsem/device_manager.py)       │
└─────────────────────────────────────┘
```

### Supported Protocols

| Protocol | Status | Speed | Best For |
|----------|--------|-------|----------|
| **WebSocket** | ✅ Full | Fast | Real-time communication |
| **HTTP/REST** | ✅ Full | Slower | Fallback, polling |
| **MQTT** | ✅ Backend | Varies | IoT devices |
| **CoAP** | ✅ Backend | Medium | Embedded systems |

### Available Mock Devices

For testing without real hardware:

| Device | Capabilities | Testing |
|--------|--------------|---------|
| **Mock Light Device** | Light effects, color, intensity | Effect colors |
| **Mock Vibration Device** | Vibration effects, intensity | Motor control |
| **Mock Wind Device** | Wind effects, intensity | Air flow |

---

## Common Tasks

### Task 1: Switch Between Protocols

1. Go to **Connection** tab
2. Click **Disconnect**
3. Change protocol dropdown (WebSocket ↔ HTTP ↔ MQTT)
4. Click **Connect**

**MQTT Note**: When selecting MQTT protocol:
- Auto-start feature automatically starts the backend MQTT broker
- You'll see "MQTT requested: Auto-starting backend MQTT broker..." in logs
- Connection proceeds automatically - no manual broker setup needed!
- See `../development/PROTOCOL_TESTING.md` → "GUI MQTT Connection" for details

### Task 2: Send Multiple Effects

1. Keep device selected
2. Go to **Effects** tab
3. Change parameters
4. Click **Send Effect**
5. Repeat as needed

### Task 3: Discover Real Devices

See `DEVICES.md` for:
- Bluetooth device discovery
- Serial port devices
- MQTT device registration
- Custom device creation

### Task 4: Monitor Application

Open terminal to see live logs:
```
14:43:xx - [INFO] gui.app_controller - Connecting via websocket...
14:43:xx - [INFO] gui.protocols.websocket_protocol - WebSocket connected
14:43:xx - [INFO] gui.ui.main_window - Connected to backend
```

---

## Event Loop Integration

**Technical Note**: The GUI uses **qasync** for asyncio/Qt integration.

This means:
- ✅ Non-blocking async operations
- ✅ Responsive UI during network calls
- ✅ Proper async/await in Qt slots
- ✅ Clean shutdown

You don't need to worry about this - it just works!

---

## Troubleshooting

### GUI Won't Start
```powershell
# Check dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.14+

# Try with verbose output
python -m gui.app 2>&1
```

### Can't Connect to Backend
1. **Check backend is running**: See Terminal 1 output
2. **Check port 8090**: 
   ```powershell
   netstat -ano | findstr :8090
   ```
3. **Firewall**: Allow localhost:8090
4. **Try HTTP** if WebSocket fails

### Effects Don't Send
1. Ensure device is **selected** (Devices tab)
2. Check **green status** indicator
3. Look for **error messages** in status bar
4. Check **backend terminal** for errors

### GUI Freezes
- Restart GUI: `python -m gui.app`
- Restart backend: `python examples/server/main.py`
- Check terminal for error messages

### USB/Serial Issues
1. Check device is connected
2. Verify correct COM port
3. See `DEVICES.md` for serial configuration

---

## Next Steps

1. **Complete Manual Testing**: See `TESTING.md`
2. **Create Real Devices**: See `DEVICES.md`
3. **Understand Architecture**: See `../README.md`
4. **Advanced Configuration**: See `development/` folder

---

## Key Files

| File | Purpose |
|------|---------|
| `gui/app.py` | GUI entry point |
| `examples/server/main.py` | Backend server |
| `gui/app_controller.py` | State management |
| `gui/protocols/` | Protocol implementations |
| `gui/ui/` | UI components |
| `src/device_manager.py` | Device handling |

---

## Support

- **GUI Issues**: Check `STATUS.md` and application logs
- **Device Issues**: See `DEVICES.md` troubleshooting
- **Testing Questions**: See `TESTING.md` details
- **Code Examples**: See `guides/` folder

---

*For full project documentation, see the [main README](../README.md)*
