# 📱 Mobile Phone Setup Guide - Vibration Testing

## Overview

This guide helps you connect your smartphone (Android or iOS) to PythonPlaySEM for vibration effect testing via Bluetooth Low Energy (BLE).

---

## 🎯 Quick Start

### Option 1: Using BLE Apps (Recommended)

The easiest way to test vibration on your phone is using a BLE peripheral app that exposes vibration control.

#### For Android:

1. **Install "nRF Connect for Mobile"** (by Nordic Semiconductor)
   - Free app from Google Play Store
   - https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp

2. **Set up as BLE Peripheral:**
   - Open nRF Connect
   - Go to "Advertiser" tab
   - Tap "+" to create new advertising packet
   - Choose "Complete local name" and name it "MyPhone_Vibrator"
   - Start advertising

3. **Enable notifications:**
   - Go to "Server" tab
   - Add a custom service with UUID: `0000180A-0000-1000-8000-00805F9B34FB`
   - Add characteristic with UUID: `00002A56-0000-1000-8000-00805F9B34FB`
   - Set permissions: Read, Write, Notify

4. **Scan from Control Panel:**
   - Open Control Panel (http://localhost:8090)
   - Select "Bluetooth (BLE)" driver
   - Click "Scan for Devices"
   - Look for "MyPhone_Vibrator"
   - Click "Connect"

#### For iOS:

1. **Install "LightBlue"** (by Punch Through)
   - Free app from App Store
   - https://apps.apple.com/app/lightblue/id557428110

2. **Create Virtual Peripheral:**
   - Open LightBlue
   - Tap "Create Virtual Peripheral"
   - Add a service:
     - Service UUID: `180A`
     - Name: "Device Information"
   - Add characteristic:
     - Characteristic UUID: `2A56`
     - Properties: Read, Write, Notify
   - Start Advertising as "MyPhone_Vibrator"

3. **Scan from Control Panel:**
   - Same as Android steps above

---

## 🔧 Option 2: Custom BLE App

For full control, you can create a simple BLE app that actually triggers vibration when receiving commands.

### Android (Using Kotlin):

```kotlin
// Simple BLE Peripheral with Vibration
import android.bluetooth.*
import android.content.Context
import android.os.Vibrator

class VibrationBLEPeripheral(context: Context) {
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter = bluetoothManager.adapter
    private val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    
    // UUIDs
    val SERVICE_UUID = UUID.fromString("0000180A-0000-1000-8000-00805F9B34FB")
    val CHAR_UUID = UUID.fromString("00002A56-0000-1000-8000-00805F9B34FB")
    
    fun startAdvertising() {
        val advertiser = bluetoothAdapter.bluetoothLeAdvertiser
        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_BALANCED)
            .setConnectable(true)
            .build()
        
        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(true)
            .addServiceUuid(ParcelUuid(SERVICE_UUID))
            .build()
        
        advertiser.startAdvertising(settings, data, advertiseCallback)
    }
    
    // When receiving write to characteristic:
    fun onCharacteristicWrite(value: ByteArray) {
        // Parse intensity and duration from value
        val intensity = value[0].toInt()  // 0-100
        val duration = (value[1].toInt() shl 8) or value[2].toInt()  // milliseconds
        
        // Trigger vibration
        vibrator.vibrate(duration.toLong())
    }
}
```

### iOS (Using Swift):

```swift
// Simple BLE Peripheral with Haptic Feedback
import CoreBluetooth
import UIKit

class VibrationBLEPeripheral: NSObject, CBPeripheralManagerDelegate {
    var peripheralManager: CBPeripheralManager!
    let serviceUUID = CBUUID(string: "180A")
    let characteristicUUID = CBUUID(string: "2A56")
    
    func startAdvertising() {
        peripheralManager = CBPeripheralManager(delegate: self, queue: nil)
        
        let characteristic = CBMutableCharacteristic(
            type: characteristicUUID,
            properties: [.read, .write, .notify],
            value: nil,
            permissions: [.readable, .writeable]
        )
        
        let service = CBMutableService(type: serviceUUID, primary: true)
        service.characteristics = [characteristic]
        
        peripheralManager.add(service)
        peripheralManager.startAdvertising([
            CBAdvertisementDataServiceUUIDsKey: [serviceUUID],
            CBAdvertisementDataLocalNameKey: "MyPhone_Vibrator"
        ])
    }
    
    func peripheralManager(_ peripheral: CBPeripheralManager, 
                          didReceiveWrite requests: [CBATTRequest]) {
        for request in requests {
            if let value = request.value {
                // Parse intensity and duration
                let intensity = Int(value[0])  // 0-100
                let duration = Int(value[1]) << 8 | Int(value[2])  // ms
                
                // Trigger haptic feedback
                let generator = UIImpactFeedbackGenerator(style: .heavy)
                generator.impactOccurred()
                
                peripheral.respond(to: request, withResult: .success)
            }
        }
    }
}
```

---

## 🧪 Option 3: Using Python Script on Phone (Termux - Android Only)

If you have Termux installed on Android, you can run a Python script directly:

### Setup:

1. Install Termux from F-Droid (not Play Store version)
2. Install required packages:
```bash
pkg update && pkg upgrade
pkg install python
pip install bleak
```

3. Create vibration server script:
```python
#!/usr/bin/env python3
# phone_vibration_server.py
import asyncio
from bleak import BleakGATTServer, BleakGATTCharacteristic
import subprocess

async def vibrate(duration_ms):
    """Trigger phone vibration using Android API"""
    subprocess.run([
        'termux-vibrate', 
        '-d', str(duration_ms)
    ])

async def on_write(characteristic, value):
    """Handle vibration command"""
    intensity = value[0]
    duration = (value[1] << 8) | value[2]
    print(f"Vibration: {intensity}% for {duration}ms")
    await vibrate(duration)

# Run BLE server
# (Implementation depends on Termux BLE capabilities)
```

---

## 🌐 Option 4: WebSocket Bridge (Easiest!)

The simplest method - use your phone's browser as a bridge:

### Setup:

1. **On your phone, open browser and navigate to:**
   ```
   http://YOUR_PC_IP:8090
   ```
   (Replace YOUR_PC_IP with your computer's local IP, e.g., 192.168.1.100)

2. **Create a simple HTML page for phone:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Phone Vibration Tester</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial;
            padding: 20px;
            background: #f0f0f0;
        }
        .btn {
            width: 100%;
            padding: 20px;
            margin: 10px 0;
            font-size: 18px;
            border: none;
            border-radius: 10px;
            background: #667eea;
            color: white;
        }
        #status {
            padding: 15px;
            background: white;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>📱 Phone Vibration Tester</h1>
    <div id="status">Status: Ready</div>
    
    <button class="btn" onclick="testVibration(200, 20)">Short Buzz</button>
    <button class="btn" onclick="testVibration(1000, 50)">Medium Pulse</button>
    <button class="btn" onclick="testVibration(2000, 80)">Strong Vibe</button>
    <button class="btn" onclick="testVibration(3000, 100)">Maximum</button>
    
    <script>
        function testVibration(duration, intensity) {
            // Use Web Vibration API
            if ("vibrate" in navigator) {
                navigator.vibrate(duration);
                document.getElementById('status').textContent = 
                    `Vibrating: ${intensity}% for ${duration}ms`;
                
                setTimeout(() => {
                    document.getElementById('status').textContent = 'Status: Ready';
                }, duration + 500);
            } else {
                document.getElementById('status').textContent = 
                    'Vibration API not supported';
            }
        }
    </script>
</body>
</html>
```

Save as `phone_vibration_tester.html` and open on your phone's browser!

---

## 📋 Quick Reference: BLE UUIDs

For custom apps, use these standard UUIDs:

| Purpose | UUID |
|---------|------|
| Device Information Service | `0000180A-0000-1000-8000-00805F9B34FB` |
| Vibration Characteristic | `00002A56-0000-1000-8000-00805F9B34FB` |
| Battery Service | `0000180F-0000-1000-8000-00805F9B34FB` |

### Data Format for Vibration Command:

```
Byte 0: Intensity (0-100)
Byte 1-2: Duration in milliseconds (big-endian)

Example: [50, 0x03, 0xE8] = 50% intensity for 1000ms
```

---

## 🐛 Troubleshooting

### Phone not appearing in scan:

1. **Check Bluetooth is enabled** on your phone
2. **Ensure app is advertising** (not just discoverable)
3. **Restart Bluetooth** on both devices
4. **Check permissions** - Location permission required for BLE on Android

### Can't connect to phone:

1. **Stop advertising and restart** the app
2. **Unpair device** from phone's Bluetooth settings if previously paired
3. **Check BLE app logs** for connection errors
4. **Try shorter device name** (some phones have limits)

### Vibration not working:

1. **Check phone is not in silent mode**
2. **Grant vibration permission** to the BLE app
3. **Test vibration manually** in the app first
4. **Check characteristic write succeeded** (no errors in Control Panel log)

---

## 🎯 Recommended Workflow

1. **Start with nRF Connect (Android) or LightBlue (iOS)**
   - Quick setup, no coding required
   - Perfect for initial testing

2. **Use Control Panel to scan and connect**
   - Visual feedback
   - Easy testing with presets

3. **Graduate to custom app if needed**
   - Full vibration control
   - Integration with haptic patterns

4. **Use WebSocket bridge for instant testing**
   - No BLE complexity
   - Works on any phone with browser

---

## 📱 Next Steps

After successfully connecting your phone:

1. **Test basic vibration effects** using presets
2. **Experiment with different intensities and durations**
3. **Measure latency** from control panel to vibration
4. **Try pattern sequences** (multiple effects in succession)
5. **Test with other devices** (Arduino, ESP32, etc.)

---

## 🔗 Resources

- **nRF Connect for Mobile**: https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-mobile
- **LightBlue (iOS)**: https://punchthrough.com/lightblue-features/
- **Bluetooth SIG UUIDs**: https://www.bluetooth.com/specifications/gatt/services/
- **Web Vibration API**: https://developer.mozilla.org/en-US/docs/Web/API/Vibration_API

---

**Ready to start? Run the Control Panel server and open it in your browser!**

```bash
python examples/control_panel/control_panel_server.py
```

Then navigate to: http://localhost:8090
