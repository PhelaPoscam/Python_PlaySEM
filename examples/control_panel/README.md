# 🎮 Control Panel - Quick Start Guide

## Overview

The Control Panel provides a user-friendly web interface for testing and controlling your PythonPlaySEM devices in real-time.

IMPORTANT — canonical PlaySEM flow:
- For **quick end-to-end tests**, use `examples/demos/websocket_server_demo.py` + `examples/web/websocket_client.html` (the client has a "phone mode" for vibration tests). This is the minimal and preferred way to verify PlaySEM.
- `examples/control_panel/*` is a richer control panel (FastAPI server + UI) for device discovery, debug, and advanced workflows; it is not required for quick tests.

---

## 📳 Laptop → Phone via WebSocket (Recommended)

Use the built-in WebSocket demo and the existing web client with "phone mode" to vibrate your phone — no extra bridge files needed.

1) Start the WebSocket server demo (on your laptop):

```powershell
.venv\Scripts\python.exe examples\demos\websocket_server_demo.py
```

2) Serve the web client (so your phone can load it over HTTP):

```powershell
# From the repo root
Set-Location "examples\web"; python -m http.server 8000
```

3) On your phone (same Wi‑Fi):
- Open: `http://<YOUR_PC_IP>:8000/websocket_client.html`
- Check the "Phone mode" box (vibrates on incoming vibration effects)
- Set WebSocket URL to: `ws://<YOUR_PC_IP>:8765`
- Tap "Connect to Server"

4) Send a vibration effect:
- From any connected client (e.g., the laptop control panel or the websocket client on another device), use the "📳 Vibration Effect" controls and click "Send Vibration Effect".
- If you opened the control panel on your phone and enabled Phone mode, the phone will vibrate when the server broadcasts the `effect_executed` event (note that the origin client is excluded from the broadcast).

Tip: You can also open the client on your laptop at `http://localhost:8000/websocket_client.html` and send effects to your phone (which is connected to the same WebSocket server).

---

## 🚀 Quick Start

### 1. Start the Server

```bash
python examples/control_panel/control_panel_server.py
```

The server will start on `http://localhost:8090`

### 2. Open in Browser

**Desktop:** Navigate to http://localhost:8090

**Mobile Phone:** 
- Find your PC's IP address (e.g., `192.168.1.100`)
- Open browser on phone and go to `http://YOUR_PC_IP:8090`

### 3. Test Vibration on Phone

- **Easiest Method (phone vibration check):**
- Use `examples/control_panel/phone_tester.html` only when you want to *quickly* test the Web Vibration API on your phone.
- For full PlaySEM flows use the canonical path above.
- Or navigate to the phone tester through the control panel
- Tap any button to test vibration directly!

---

## 📱 Features

### 🔌 Server Connection
- Connect to the backend server
- WebSocket for real-time updates
- Connection status indicator

### 🔍 Device Discovery
- **Bluetooth (BLE):** Scan for nearby Bluetooth devices
  - Perfect for phones, smartwatches, haptic vests
- **Serial (USB):** Detect connected Arduino/ESP32 devices
  - Automatically lists all COM ports
- **MQTT (Network):** Connect to network devices
  - Requires broker address

### 📱 Connected Devices
- View all connected devices
- Test each device individually
- Disconnect devices

### ⚡ Effect Testing
- Select target device
- Choose effect type (vibration, light, wind, etc.)
- Adjust intensity (0-100%)
- Adjust duration (100-5000ms)
- Quick presets:
  - **Short Buzz:** 20% / 200ms
  - **Medium Pulse:** 50% / 1s
  - **Strong Vibe:** 80% / 2s
  - **Maximum:** 100% / 3s

### 📊 System Statistics
- Total effects sent
- Average latency
- System uptime
- Error count

### 📝 Activity Log
- Real-time event logging
- Connection events
- Effect dispatch results
- Error messages

---

## 🧪 Testing Your Phone

### Method 1: Web Vibration API (Easiest!)

1. **Serve the phone tester:**
   ```bash
   cd examples/web
   python phone_tester_server.py
   ```
2. **On your phone, open:** `http://YOUR_PC_IP:8091/phone_tester.html`
3. **Test immediately** - no setup required!
4. **Available tests:**
   - Quick presets (Short, Medium, Strong, Max)
   - Custom intensity and duration
   - Vibration patterns (S.O.S, Triple Pulse, etc.)

### Method 2: Bluetooth BLE

1. **Install BLE app on phone:**
   - **Android:** nRF Connect for Mobile
   - **iOS:** LightBlue

2. **Set up as BLE peripheral:**
   - Create advertising packet
   - Add service and characteristic
   - Start advertising

3. **From Control Panel:**
   - Select "Bluetooth (BLE)"
   - Click "Scan for Devices"
   - Find your phone
   - Click "Connect"

4. **Send vibration commands!**

See `docs/MOBILE_PHONE_SETUP.md` for detailed instructions.

---

## 🔧 Workflow for Testing

### Step 1: Scan for Devices

```
1. Select driver type (Bluetooth/Serial/MQTT)
2. Click "Scan for Devices"
3. Wait for devices to appear
4. Click "Connect" on desired device
```

### Step 2: Test Basic Vibration

```
1. Select connected device from dropdown
2. Choose "vibration" effect type
3. Click a preset button (e.g., "Medium Pulse")
4. Feel the vibration on your device!
```

### Step 3: Experiment with Settings

```
1. Adjust intensity slider (0-100%)
2. Adjust duration slider (100-5000ms)
3. Click "Send Effect"
4. Observe response time in log
```

### Step 4: Monitor Performance

```
1. Check "System Statistics" card
2. Note average latency
3. Track effects sent
4. Review activity log for errors
```

---

## 📱 Mobile Phone Testing Scenarios

### Scenario 1: Quick Phone Vibration Test
**Goal:** Verify phone can receive and execute vibration commands

```
1. Open `examples/web/phone_tester.html` on your smartphone
2. Tap "Short Buzz" button
3. Feel vibration immediately
4. Check statistics counter increments
```

### Scenario 2: BLE Integration Test
**Goal:** Test Bluetooth connectivity and effect dispatch

```
1. Set up phone as BLE peripheral (using nRF Connect)
2. From Control Panel, scan for Bluetooth devices
3. Connect to your phone
4. Send vibration effects
5. Measure latency (should be < 100ms)
```

### Scenario 3: Pattern Testing
**Goal:** Test complex vibration patterns

```
1. Use `examples/web/phone_tester.html` on smartphone
2. Try different patterns:
   - S.O.S (short-short-short-long)
   - Triple Pulse
   - Rapid Fire
   - Crescendo
3. Note which patterns feel most distinct
```

### Scenario 4: Latency Measurement
**Goal:** Measure end-to-end response time

```
1. Connect phone via Bluetooth
2. Send test effect from Control Panel
3. Note latency in activity log
4. Typical values:
   - BLE: 50-150ms
   - Serial: 10-50ms
   - MQTT: 20-100ms
```

---

## 🐛 Troubleshooting

### Control Panel won't load
- **Check server is running** - should see "Uvicorn running on..."
- **Check URL** - must be exactly http://localhost:8090
- **Check firewall** - may need to allow port 8090

### Can't connect to devices
- **Bluetooth:** Ensure phone is advertising and not just discoverable
- **Serial:** Check device is plugged in and drivers installed
- **MQTT:** Verify broker is running and address is correct

### Phone not vibrating
- **Check phone not in silent mode**
- **Try examples/web/phone_tester.html first** - proves vibration works
- **Check BLE characteristic write succeeded**
- **Verify vibration permission granted** to BLE app

### High latency
- **Bluetooth:** Normal is 50-150ms
- **Too high?** Check phone not sleeping, BLE app in foreground
- **Serial:** Should be < 50ms, check baudrate matches

---

## 🎯 Next Steps

After successfully testing with control panel:

1. **✅ Verify basic connectivity** - Can you connect to your phone?
2. **✅ Test vibration effects** - Do quick presets work?
3. **✅ Measure latency** - What's the response time?
4. **✅ Try patterns** - Can you create interesting sequences?
5. **⬜ Connect Arduino** - Test with serial devices
6. **⬜ Build custom driver** - Extend to other hardware
7. **⬜ Integrate with app** - Use in your own projects

For canonical protocol and testing instructions, see `PROTOCOL_TESTING.md`.

---

## 📁 File Structure

```
examples/control_panel/
├── control_panel.html          # Main web interface
├── control_panel_server.py     # Backend server (FastAPI + WebSocket)
├── PROTOCOL_TESTING.md         # Advanced protocol testing guide
└── README.md                   # This file

examples/web/
├── phone_tester.html           # Mobile vibration tester
├── phone_tester_server.py      # Simple HTTP server for phone tester
└── websocket_client.html       # WebSocket client UI

docs/
├── MOBILE_PHONE_SETUP.md       # Detailed phone setup guide
└── UNIVERSAL_DRIVER_INTEGRATION.md  # Architecture documentation
```

---

## 🔗 Resources

- **Control Panel:** http://localhost:8090
- **Phone Tester:** `examples/web/phone_tester.html` (via phone_tester_server.py)
- **Setup Guide:** `docs/MOBILE_PHONE_SETUP.md`
- **API Docs:** http://localhost:8090/docs (when server running)

---

## 💡 Pro Tips

1. **Use phone_tester.html for quick tests** - No BLE setup needed!
2. **Check activity log frequently** - Shows detailed error messages
3. **Start with presets** - Fine-tune custom values later
4. **Test latency under load** - Send multiple effects rapidly
5. **Document your findings** - Note which devices/settings work best

---

**Ready to test? Start the server and open http://localhost:8090!** 🚀
