# Hardware Integration Guide

How to connect physical hardware (Arduino, ESP32, etc.) to PlaySEM.

## How PlaySEM Talks to Hardware

PlaySEM's `SerialDriver` sends **newline-delimited JSON** over USB Serial at 115200 baud.

When PlaySEM dispatches an effect:

```python
driver.send_command(
    device_id="wind_device",
    command="set_speed",
    params={"speed": 80, "direction": "forward"},
)
```

This exact line is written over USB:

```json
{"device_id": "wind_device", "command": "set_speed", "params": {"speed": 80, "direction": "forward"}}
```

The microcontroller reads lines, parses the JSON, and drives actuators.

## Supported Effect Commands

PlaySEM's default effect mappings send these commands. Your microcontroller
should handle the ones relevant to your hardware:

| Effect | Command | Params |
|--------|---------|--------|
| light | `set_brightness` | `brightness` (0-255) |
| light | `set_color` | `r`, `g`, `b` (0-255 each) |
| wind | `set_speed` | `speed` (0-100) |
| wind | `set_direction` | `direction` ("forward" / "reverse") |
| vibration | `set_intensity` | `intensity` (0-100) |
| vibration | `set_duration` | `duration` (ms) |
| scent | `set_scent` | `scent` (string), `intensity` (0-100) |
| scent | `stop_scent` | (none) |

## Wiring Reference

### PWM Fan (MOSFET / L298N)

```
Arduino Pin 9  ──→  MOSFET Gate / L298N ENA
Arduino GND    ──→  MOSFET Source / L298N GND
Battery +12V   ──→  Fan + (through MOSFET Drain)
Battery GND    ──→  Fan -
```

### RGB LED Strip (common cathode)

```
Arduino Pin 9  ──→  Red channel   (via MOSFET / resistor)
Arduino Pin 10 ──→  Green channel (via MOSFET / resistor)
Arduino Pin 11 ──→  Blue channel  (via MOSFET / resistor)
Arduino GND    ──→  LED common cathode
```

### Vibration Motor

```
Arduino Pin 9  ──→  MOSFET Gate
Arduino GND    ──→  MOSFET Source
Battery +      ──→  Motor + (through MOSFET Drain)
Battery GND    ──→  Motor -
```

## Examples

| File | What it does |
|------|-------------|
| `fan_controller/fan_controller.ino` | Arduino sketch that receives JSON commands and drives a PWM fan |
| `serial_fan_demo.py` | Python script that connects to the Arduino and sends fan commands |

## Platform Notes

- **Windows**: COM port shows as `COM3`, `COM4`, etc. Check Device Manager → Ports.
- **Linux**: Shows as `/dev/ttyUSB0` or `/dev/ttyACM0`. Run `sudo chmod 666 /dev/ttyUSB0` or add your user to the `dialout` group.
- **macOS**: Shows as `/dev/cu.usbmodem*` or `/dev/cu.usbserial*`.

## ESP32 over WiFi (MQTT)

For wireless setups, use PlaySEM's MQTT driver instead of Serial:

```python
from playsem.drivers.mqtt_driver import MQTTDriver

driver = MQTTDriver(
    broker_host="192.168.1.100",
    broker_port=1883,
    client_id="playsem_controller",
)
await driver.connect()

await driver.send_command(
    "light_device", "set_color", {"r": 255, "g": 100, "b": 0}
)
```

On the ESP32, subscribe to the MQTT topic and parse the same JSON format.
The structure is identical — only the transport changes.
