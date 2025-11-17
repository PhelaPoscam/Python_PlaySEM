# Testing Guide - PythonPlaySEM

This guide shows you how to test and SEE the MQTT and WebSocket servers working in real-time.

---

## 🧪 Testing WebSocket Server (EASIEST - No Extra Setup!)

The WebSocket server is the **easiest to test** because it requires no external dependencies!

### Step 1: Start the WebSocket Server

Open a terminal and run:

```bash
python examples/websocket_server_demo.py
```

You should see:
```
============================================================
WebSocket Server is starting...
============================================================

Server URL: ws://localhost:8765

To test the server:
1. Open 'examples/websocket_client.html' in your web browser
...
```

### Step 2: Open the HTML Client

Simply **double-click** `examples/websocket_client.html` or open it in your browser:
- **Windows**: Double-click the file in File Explorer
- **macOS**: Double-click in Finder or `open examples/websocket_client.html`
- **Linux**: `xdg-open examples/websocket_client.html`

### Step 3: Connect and Test

1. Click **"Connect to Server"** button
2. You'll see: `✅ Connected to ws://localhost:8080`
3. Use the sliders to adjust intensity and duration
4. Click any effect button (Light, Wind, Vibration)
5. **Watch the terminal** where the server is running - you'll see:
   ```
   ✓ Received effect: light (intensity=80, duration=1000ms)
   ```
6. Check the **Message Log** in the browser - you'll see real-time message flow!

**What You'll See:**

**In the Browser:**
- Green "Connected" status showing `ws://localhost:8765`
- Interactive sliders for each effect
- Real-time message log showing sent/received messages
- Response confirmations

**In the Terminal:**
- `🔗 Client connected: 127.0.0.1:xxxxx`
- `✓ Received effect: light (intensity=80, duration=1000ms)`
- Effect execution logs

---

## 🧪 Testing MQTT Server (Requires Mosquitto)

### Option A: Install Mosquitto Broker (Recommended)

**Windows:**
```powershell
choco install mosquitto
```

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**Linux:**
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### Step 1: Verify Mosquitto is Running

```bash
# Test if broker is accessible
mosquitto_pub -t "test" -m "hello"
```

If this works without errors, you're ready!

### Step 2: Start MQTT Server

Open terminal #1:
```bash
python examples/mqtt_server_demo.py
```

You should see:
```
============================================================
MQTT Server is running!
============================================================

Listening for effects on topics: effects/*
```

### Step 3: Send Test Effects

Open terminal #2:
```bash
python examples/test_mqtt_client.py
```

You'll see effects being sent in terminal #2:
```
[1/4] 💡 Bright light effect
  📤 Publishing to: effects/light
  📋 Payload: {"effect_type":"light","timestamp":0,"duration":1000,"intensity":100}

[2/4] 💨 Strong wind effect
...
```

And effects being received in terminal #1 (server):
```
✓ Received effect: light (intensity=100, duration=1000ms)
✓ Received effect: wind (intensity=75, duration=2000ms)
...
```

### Step 4: Manual Testing with mosquitto_pub

You can also send effects manually:

```bash
# Light effect
mosquitto_pub -t "effects/light" -m '{"effect_type":"light","timestamp":0,"duration":1000,"intensity":100}'

# Wind effect
mosquitto_pub -t "effects/wind" -m '{"effect_type":"wind","timestamp":0,"duration":2000,"intensity":75}'

# Vibration effect
mosquitto_pub -t "effects/vibration" -m '{"effect_type":"vibration","timestamp":0,"duration":500,"intensity":80}'
```

### Option B: Use Public MQTT Broker (No Install Needed)

If you don't want to install Mosquitto, you can use a public test broker:

We provide ready-to-run public-broker demos:

- Server demo (subscribes to `effects/#` on `test.mosquitto.org`):
  ```powershell
  .\.venv\Scripts\python.exe examples\mqtt_server_demo_public.py
  ```

- Client publisher (sends 4 effects to the public broker):
  ```powershell
  .\.venv\Scripts\python.exe examples\test_mqtt_client_public.py
  ```

Or use mosquitto_pub manually:
```powershell
mosquitto_pub -h test.mosquitto.org -t "effects/light" -m '{"effect_type":"light","timestamp":0,"duration":1000,"intensity":100}'
```

⚠️ Public brokers are not secure - use only for testing.

---

## 🧪 Testing CoAP Server (aiocoap)

CoAP is available via `aiocoap` (installed with `requirements.txt`).

### Step 1: Start the CoAP Server

```powershell
.\.venv\Scripts\python.exe examples\coap_server_demo.py
```

Expected output includes:
```
CoAP Server is starting...
Server URL: coap://localhost:5683
```

### Step 2: Send a Test Effect

Use the provided client:
```powershell
.\.venv\Scripts\python.exe examples\test_coap_client.py
```

You should see a 2.xx success code and a JSON response payload with `{ "success": true }`.

If you have `aiocoap-client` installed, you can also POST manually:
```powershell
echo '{"effect_type":"light","timestamp":0,"duration":1000,"intensity":80}' > payload.json
aiocoap-client -m POST -e payload.json coap://localhost/effects
```

---

## 📊 What You Should See

### WebSocket Server Output:
```
2025-11-12 14:30:15 - [INFO] WebSocket Server initialized - localhost:8765
2025-11-12 14:30:15 - [INFO] Starting WebSocket server on localhost:8765
2025-11-12 14:30:15 - [INFO] WebSocket Server started on ws://localhost:8765
2025-11-12 14:30:20 - [INFO] 🔗 Client connected: 127.0.0.1:52341
2025-11-12 14:30:20 - [INFO] ✓ Received effect: light (intensity=80, duration=1000ms)
2025-11-12 14:30:22 - [INFO] ✓ Received effect: wind (intensity=60, duration=2000ms)
```

### MQTT Server Output:
### CoAP Server Output:
```
2025-11-12 14:40:01 - [INFO] CoAP Server initialized - localhost:5683
2025-11-12 14:40:01 - [INFO] Starting CoAP server on localhost:5683
2025-11-12 14:40:01 - [INFO] CoAP Server started on coap://localhost:5683
2025-11-12 14:40:05 - [INFO] ✓ Received effect: light (intensity=70, duration=1500ms)
```
```
2025-11-12 14:32:10 - [INFO] MQTT Server initialized - broker: localhost:1883
2025-11-12 14:32:10 - [INFO] Connecting to MQTT broker at localhost:1883
2025-11-12 14:32:10 - [INFO] Connected to MQTT broker, subscribing to effects/#
2025-11-12 14:32:15 - [INFO] ✓ Received effect: light (intensity=100, duration=1000ms)
2025-11-12 14:32:17 - [INFO] ✓ Received effect: wind (intensity=75, duration=2000ms)
```

---

## 🎯 Quick Testing Checklist

- [x] **WebSocket Server**: Start server → Open HTML client → Click connect → Send effects
- [x] **MQTT Server**: Install mosquitto → Start server → Run test client OR use mosquitto_pub

---

## 🔧 Troubleshooting

### WebSocket Issues:

**"Connection refused" in browser:**
- Make sure the Python server is running
- Check the URL is `ws://localhost:8765` (not `http://`)
- If port 8765 is busy, edit both `websocket_server_demo.py` and `websocket_client.html` to use a different port

**No effects showing:**
- Open browser console (F12) to see JavaScript errors
- Check the Message Log in the HTML page

### MQTT Issues:

**"Connection refused" error:**
```bash
# Check if mosquitto is running
ps aux | grep mosquitto  # Linux/Mac
Get-Process mosquitto     # Windows

# Start mosquitto manually
mosquitto                 # Run in terminal
```

**"Broker not found":**
- Install mosquitto (see instructions above)
- Or use public broker: `test.mosquitto.org`

**No messages received:**
- Check broker is on port 1883 (default)
- Verify topics match: `effects/#` pattern
- Check firewall isn't blocking port 1883

---

## 🚀 Next Steps (when resuming)

Once you've verified both servers work:

1. **Integrate with Unity/Unreal**: Use WebSocket client libraries
2. **Connect Real Devices**: Replace mock devices with actual hardware
3. **Add More Effects**: Extend `config/effects.yaml`
4. **Build Dashboards**: Create monitoring interfaces
5. **Deploy to Production**: Use proper MQTT brokers like AWS IoT or Azure IoT Hub

---

## 📚 Additional Resources

- **WebSocket Testing Tools:**
  - Browser DevTools (F12 → Network → WS) - see actual WebSocket frames
  - [Postman](https://www.postman.com/) (supports WebSocket)
  - [websocat](https://github.com/vi/websocat) (CLI tool) - `websocat ws://localhost:8765`

- **MQTT Testing Tools:**
  - [MQTT Explorer](http://mqtt-explorer.com/) (GUI client)
  - [mosquitto_sub](https://mosquitto.org/man/mosquitto_sub-1.html) (subscribe to topics)
  - [MQTT.fx](https://mqttfx.jensd.de/) (another GUI option)

---

---

## 🧪 Running the Test Suite

```powershell
# Unit + integration tests
.\.venv\Scripts\python.exe -m pytest -v

# Only integration tests
.\.venv\Scripts\python.exe -m pytest tests\*integration.py -v

# CoAP integration test only
.\.venv\Scripts\python.exe -m pytest tests\test_coap_server_integration.py -v
```

Note: MQTT integration tests may skip automatically if a local broker isn’t available. CoAP tests require `aiocoap` installed (included in `requirements.txt`).

**Happy Testing! 🎉**
