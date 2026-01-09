# Serial Testing Guide

This guide covers how to test serial communication without physical hardware using the Virtual Serial Device Simulator.

## Overview

The Virtual Serial Device Simulator allows you to test the `SerialDriver` and serial communication features without requiring actual Arduino or hardware devices. It creates a software device that responds to serial commands just like real hardware would.

## What You Get

### 1. Virtual Serial Device (`examples/demos/virtual_serial_device.py`)

A Python script that simulates an Arduino-like device:
- ✅ Responds to commands (PING, STATUS, LIGHT, VIBRATE, WIND)
- ✅ Simulates effect durations
- ✅ Sends acknowledgments
- ✅ Logs all activity
- ✅ Supports JSON and text commands

### 2. Enhanced Super Controller (`examples/ui/super_controller.html`)

Completely redesigned controller with:
- 📊 **Real-time Statistics**: Effect count, success rate, latency
- 🎯 **Device Capabilities**: Visual device selection with auto-fetch
- 📜 **Effect History**: Scrollable log of all sent effects
- 🎨 **Visual Feedback**: Animated effects when sending
- 📱 **Responsive Design**: Works on desktop and mobile

### 3. Enhanced Super Receiver (`examples/ui/super_receiver.html`)

Advanced effect visualization:
- 🌊 **Wave Animations**: Ripple effects on receipt
- 💡 **Full-screen Effects**: Background changes for light effects
- 📳 **Vibration Feedback**: Physical vibration (on supported devices)
- 📊 **Live Statistics**: Total received, session count, avg intensity
- 📜 **Effect Log**: Detailed history with timestamps

## Quick Start

### Windows Setup

**Option 1: Using com0com (Recommended for Windows)**

1. Download and install [com0com](https://sourceforge.net/projects/com0com/):
   ```powershell
   # After installation, it creates virtual COM port pairs
   # Example: COM3 <-> COM4
   ```

2. Run the virtual device:
   ```powershell
   python examples/demos/virtual_serial_device.py
   ```

3. Select one of the paired ports (e.g., COM3)

4. Connect from another script/terminal:
   ```python
   from playsem.drivers import SerialDriver
   driver = SerialDriver(port="COM4", baudrate=9600)  # Use the other port
   driver.open_connection()
   driver.send_command("PING")
   ```

**Option 2: Manual Port Entry**

If you have a USB-to-Serial adapter:

1. Connect TX to RX (loopback)
2. Run the simulator on that port
3. It will receive its own messages (useful for basic testing)

### Linux/Mac Setup

**Using PTY (Pseudo-Terminal) - Built-in!**

1. Run the simulator:
   ```bash
   python examples/demos/virtual_serial_device.py
   ```

2. It automatically creates a PTY pair:
   ```
   Created PTY pair:
     Master: /dev/ttys002
     Slave: /dev/ttys003
     Use slave port for SerialDriver
   ```

3. Connect to the slave port:
   ```python
   from playsem.drivers import SerialDriver
   driver = SerialDriver(port="/dev/ttys003", baudrate=9600)
   driver.open_connection()
   driver.send_command("PING")
   ```

## Supported Commands

The virtual device understands these commands:

### Simple Commands

```bash
PING                      # Returns: PONG
STATUS                    # Returns: Current device state
LED:ON                    # Turns light on
LED:OFF                   # Turns light off
```

### Effect Commands

```bash
LIGHT:<intensity>:<duration>:[color]
# Example: LIGHT:255:1000:#FF0000
# Response: LIGHT:OK:255:1000

VIBRATE:<intensity>:<duration>
# Example: VIBRATE:128:500
# Response: VIBRATE:OK:128:500

WIND:<speed>:<duration>
# Example: WIND:200:2000
# Response: WIND:OK:200:2000
```

### JSON Commands

```json
{
    "effect_type": "light",
    "intensity": 255,
    "duration": 1000,
    "parameters": {
        "color": "#FF0000"
    }
}
```

## Testing Workflow

### End-to-End Test

1. **Terminal 1**: Start the virtual device
   ```powershell
   python examples/demos/virtual_serial_device.py
   ```

2. **Terminal 2**: Start the control panel server
   ```powershell
   python examples/server/main.py
   ```

3. **Browser**: Open the super controller
   ```
   http://localhost:8090/ui/super_controller
   ```

4. **In Controller UI**:
   - Wait for connection (green dot)
   - If device shows up in device list, select it
   - Otherwise: Configure manually in main controller
   - Send effects and watch the virtual device respond!

5. **Verify**: Check Terminal 1 for received commands
   ```
   📨 Received: LIGHT:255:1000:#FF0000
   💡 LIGHT: intensity=255, duration=1000ms, color=#FF0000
   📤 Sent: LIGHT:OK:255:1000
   ```

### Manual Testing

Use the interactive mode in the serial driver demo:

```powershell
python examples/demos/serial_driver_demo.py
```

Follow the prompts to:
- List available ports
- Select a port
- Choose baudrate
- Send commands manually
- Read responses

## Troubleshooting

### "No serial ports available"

**Windows:**
- Install com0com or use physical hardware
- Check Device Manager for COM ports

**Linux/Mac:**
- The script creates PTY automatically
- If it fails, check permissions: `sudo chmod 666 /dev/ttyS*`

### "Failed to open port"

- Port may be in use by another application
- Close Arduino IDE, serial monitors, or other connections
- On Linux, add user to `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Log out and back in
  ```

### "Device not responding"

- Check baudrate matches (9600 by default)
- Verify correct port is selected
- Check virtual device terminal for errors
- Try sending `PING` to test basic connectivity

### "Permission denied" (Linux/Mac)

```bash
# Give yourself permission
sudo chmod 666 /dev/ttyUSB0  # or your port

# Or add to dialout group (permanent)
sudo usermod -a -G dialout $USER
```

## Advanced Usage

### Custom Response Behavior

Edit `virtual_serial_device.py` to customize:

```python
def _handle_command(self, command: str) -> Optional[str]:
    # Add your custom commands here
    if command.upper().startswith("CUSTOM:"):
        # Do something
        return "CUSTOM:OK"
    
    # ... existing code
```

### Simulating Errors

```python
# Randomly fail some commands
import random

def _handle_command(self, command: str) -> Optional[str]:
    if random.random() < 0.1:  # 10% failure rate
        return "ERROR:Simulated failure"
    
    # ... normal processing
```

### Adding Delays

```python
# Simulate slow hardware
def _handle_command(self, command: str) -> Optional[str]:
    time.sleep(0.5)  # 500ms response delay
    # ... normal processing
```

## Integration with Main Controller

To use the virtual device with the main control panel:

1. Start virtual device on a known port (e.g., COM3)

2. In the control panel UI:
   - Select "Serial (USB)" from driver dropdown
   - Enter the port manually or scan
   - Connect

3. The virtual device will appear as a connected device

4. Send effects from any protocol (HTTP, WebSocket, MQTT)

5. Watch the virtual device terminal for received commands

## Best Practices

### Development Workflow

1. ✅ Start with virtual device for rapid testing
2. ✅ Test all effect types (light, vibration, wind, etc.)
3. ✅ Verify command parsing and responses
4. ✅ Test error handling (invalid commands)
5. ✅ Move to physical hardware when ready

### Testing Checklist

- [ ] Virtual device starts without errors
- [ ] Can connect from SerialDriver
- [ ] PING command works
- [ ] STATUS query returns data
- [ ] Each effect type works
- [ ] JSON commands parse correctly
- [ ] Responses are timely
- [ ] Device handles rapid commands
- [ ] Cleanup works (Ctrl+C stops cleanly)

## Next Steps

Once virtual testing is complete:

1. **Connect Real Hardware**:
   - Arduino with appropriate sketch
   - ESP32 with serial interface
   - Any USB device with serial protocol

2. **Upload Arduino Sketch**:
   ```cpp
   // See docs/arduino_examples/ for sketches
   ```

3. **Configure in Control Panel**:
   - Select correct COM port
   - Set matching baudrate
   - Test with simple effects

4. **Production Deployment**:
   - Document your device's protocol
   - Add device-specific capabilities
   - Test all effect combinations

## Resources

- **Serial Driver Code**: `src/device_driver/serial_driver.py`
- **Virtual Device**: `examples/demos/virtual_serial_device.py`
- **Serial Demo**: `examples/demos/serial_driver_demo.py`
- **Device Testing Checklist**: `docs/DEVICE_TESTING_CHECKLIST.md`

## Support

For issues or questions:
1. Check logs from virtual device terminal
2. Review this guide's troubleshooting section
3. See `docs/DEVICE_TESTING_CHECKLIST.md`
4. Check device driver documentation

---

Happy Testing! 🎉
