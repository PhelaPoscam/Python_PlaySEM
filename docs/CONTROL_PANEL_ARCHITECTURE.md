# Control Panel Architecture

## Overview

The PythonPlaySEM Control Panel is a **web-based management interface** for discovering, connecting, and testing sensory effect devices.

## Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser (Client)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        control_panel.html (Frontend UI)             │   │
│  │  - Device discovery UI                              │   │
│  │  - Effect testing controls                          │   │
│  │  - Real-time status display                         │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket (ws://localhost:8090/ws)
                        │ (Fixed - UI always connects via WebSocket)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│            Control Panel Backend (Server)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │    control_panel_server.py (Backend)                │   │
│  │  - WebSocket server for UI connection               │   │
│  │  - Device management                                │   │
│  │  - Effect dispatch                                  │   │
│  └──────────────────┬──────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     │ (Multiple device connection types)
                     ├─────────┬──────────┬──────────┬─────────
                     ▼         ▼          ▼          ▼
              ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────┐
              │Mock      │ │BLE     │ │Serial  │ │MQTT  │
              │Devices   │ │Devices │ │(USB)   │ │Broker│
              └──────────┘ └────────┘ └────────┘ └──────┘
```

## Connection Layers Explained

### Layer 1: Web UI ↔ Control Panel Backend
**Fixed Connection: Always WebSocket**

- The web browser connects to `control_panel_server.py` via WebSocket
- Host/Port: `ws://localhost:8090/ws` (configurable in UI)
- **This connection is NOT configurable by protocol** - it's always WebSocket
- Handles: device discovery requests, effect commands, status updates

### Layer 2: Control Panel Backend ↔ Physical/Virtual Devices
**Variable Connection: Multiple Driver Types**

The control panel backend can connect to devices using different drivers:

1. **Mock Driver** (`mock`)
   - Virtual devices for testing without hardware
   - Logs commands to console
   - Available devices: Light, Wind, Vibration

2. **Bluetooth Driver** (`bluetooth`)
   - Connects to BLE devices (Arduino Nano 33, ESP32, etc.)
   - Scans for nearby devices
   - Wireless connection

3. **Serial Driver** (`serial`)
   - Connects to USB devices (Arduino, ESP32 via USB)
   - Lists available serial ports
   - Wired connection

4. **MQTT Driver** (`mqtt`)
   - Connects PlaySEM to an MQTT broker
   - Allows devices to communicate via MQTT protocol
   - Example: `broker.hivemq.com:1883`

## What Does "Device Connection Type" Mean?

The dropdown in the UI labeled **"Device Connection Type"** selects:
- **HOW PlaySEM connects TO devices**
- **NOT how the web UI connects to PlaySEM**

Examples:
- **Mock**: PlaySEM creates virtual devices (no hardware needed)
- **Bluetooth**: PlaySEM scans for and connects to BLE devices
- **Serial**: PlaySEM connects to USB devices
- **MQTT**: PlaySEM connects to an MQTT broker where devices publish/subscribe

## Protocol Servers (Advanced)

PlaySEM can also act as a **server** that external applications connect TO:

```
External Apps → [MQTT/CoAP/HTTP/UPnP] → PlaySEM → Devices
```

These are configured separately (not in the control panel UI):
- **MQTT Server**: Apps publish effects to MQTT topics
- **CoAP Server**: IoT devices send effects via CoAP
- **HTTP REST API**: Apps POST effects to HTTP endpoints
- **UPnP Server**: Automatic device discovery via SSDP

## Example Workflows

### Workflow 1: Testing with Mock Devices
1. Start: `python examples/control_panel/control_panel_server.py`
2. Open: http://localhost:8090
3. **UI connects** to backend via WebSocket (automatic)
4. Select: **Device Connection Type = Mock**
5. Click: **Scan for Devices**
6. **Backend creates** 3 mock devices (light, wind, vibration)
7. Click: **Connect** on a mock device
8. Send effects - see console logs!

### Workflow 2: Connecting to Real BLE Device
1. Start: `python examples/control_panel/control_panel_server.py`
2. Open: http://localhost:8090
3. **UI connects** to backend via WebSocket (automatic)
4. Select: **Device Connection Type = Bluetooth**
5. Click: **Scan for Devices**
6. **Backend scans** for BLE devices
7. Click: **Connect** on your Arduino/ESP32
8. Send effects - device responds!

### Workflow 3: Connecting to MQTT Broker
1. Start: `python examples/control_panel/control_panel_server.py`
2. Open: http://localhost:8090
3. **UI connects** to backend via WebSocket (automatic)
4. Select: **Device Connection Type = MQTT**
5. Enter broker address (e.g., `broker.hivemq.com`)
6. Click: **Connect**
7. **PlaySEM connects** to MQTT broker
8. Devices on the broker can now receive effects!

## Common Mistakes

❌ **Wrong**: "I want to connect via MQTT protocol"
- This would mean: UI → MQTT → Control Panel (doesn't make sense)

✅ **Correct**: "I want PlaySEM to connect to an MQTT broker"
- This means: UI → WebSocket → Control Panel → MQTT → Broker → Devices

❌ **Wrong**: "Why is the protocol selector still showing after I choose MQTT?"
- The UI **always** uses WebSocket to connect to the control panel backend
- The device connection type is a separate concept

✅ **Correct**: "Device Connection Type selects how PlaySEM connects to devices"
- Mock = virtual devices
- Bluetooth = BLE wireless
- Serial = USB wired
- MQTT = MQTT broker

## Summary

- **Control Panel UI** always connects to **Backend** via **WebSocket**
- **Backend** connects to **Devices** via **different drivers** (Mock, BLE, Serial, MQTT)
- **Device Connection Type** = how backend talks to devices
- **Protocol Servers** (MQTT/CoAP/HTTP/UPnP) = how external apps talk to PlaySEM
