# Tutorial: Connecting an Arduino Device via Serial

This tutorial will guide you through connecting a custom Arduino device (like scent-emitting fans) to this project using the Serial protocol.

We will cover three parts:
1.  **The Arduino Code:** Programming your Arduino to understand commands from the project.
2.  **Testing with a Python Script:** Verifying that your Arduino works using a simple, standalone Python script.
3.  **Full Project Integration:** Configuring the main application to control your Arduino.

---

## Part 1: The Arduino Code

Your Arduino needs to listen for commands sent over the USB serial connection. The project sends commands as JSON strings, ending with a newline character (`\n`).

A typical command looks like this:
```json
{"command": "set_power", "params": {"power": "on"}, "device_id": "scent_fan_01"}
```

Here is a complete Arduino sketch that can receive and process these commands. It uses the popular `ArduinoJson` library to parse the incoming data.

### Prerequisites

1.  Install the Arduino IDE.
2.  From the Arduino IDE's Library Manager, install the **`ArduinoJson`** library.

### Example Arduino Sketch

This code will turn an LED on or off based on the received command. You can adapt this to control your fan motor or scent dispenser.

```cpp
#include <ArduinoJson.h>

// Use the built-in LED for this example.
// You can change this to any pin to control your fan.
const int fanPin = LED_BUILTIN;

// A buffer to store incoming serial data
String inputString = "";

void setup() {
  // Start the serial connection
  Serial.begin(9600);
  
  // Set the fan pin as an output
  pinMode(fanPin, OUTPUT);
  digitalWrite(fanPin, LOW); // Start with the fan off
  
  // Reserve space for the JSON document.
  // This value depends on the complexity of your JSON.
  // Use the ArduinoJson Assistant to calculate the right size:
  // https://arduinojson.org/v6/assistant/
  inputString.reserve(200);

  Serial.println("Arduino is ready to receive commands.");
}

void loop() {
  // This function will process any incoming serial data
  handleSerial();
}

void handleSerial() {
  // Read any available serial data
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;

    // When a newline character is received, the command is complete.
    if (inChar == '\n') {
      // Allocate a StaticJsonDocument.
      // The size should be adjusted based on your expected JSON payload.
      StaticJsonDocument<192> doc;

      // Attempt to deserialize the JSON document
      DeserializationError error = deserializeJson(doc, inputString);

      // If parsing fails, print an error
      if (error) {
        Serial.print(F("deserializeJson() failed: "));
        Serial.println(error.f_str());
      } else {
        // Parsing was successful, now process the command
        processCommand(doc);
      }
      
      // Clear the string for the next command
      inputString = "";
    }
  }
}

void processCommand(const StaticJsonDocument<192>& doc) {
  // Extract the "command" field from the JSON
  const char* command = doc["command"]; // e.g., "set_power"

  if (command == nullptr) {
    Serial.println("Error: 'command' field not found in JSON.");
    return;
  }

  // --- Handle the "set_power" command ---
  if (strcmp(command, "set_power") == 0) {
    const char* powerState = doc["params"]["power"]; // e.g., "on" or "off"

    if (powerState != nullptr) {
      if (strcmp(powerState, "on") == 0) {
        Serial.println("Turning fan ON");
        digitalWrite(fanPin, HIGH);
      } else if (strcmp(powerState, "off") == 0) {
        Serial.println("Turning fan OFF");
        digitalWrite(fanPin, LOW);
      }
    }
  }
  // --- Handle the "set_speed" command ---
  else if (strcmp(command, "set_speed") == 0) {
    // This assumes your fan pin is a PWM pin (like ~3, ~5, ~6, ~9, ~10, ~11 on an Uno)
    int speed = doc["params"]["speed"]; // e.g., 128
    Serial.print("Setting fan speed to: ");
    Serial.println(speed);
    analogWrite(fanPin, speed); // speed should be 0-255
  }
  // --- Add more commands here ---
  else {
    Serial.print("Unknown command: ");
    Serial.println(command);
  }
}
```

**Upload this sketch to your Arduino.** Keep the Arduino connected to your computer via USB. You can open the Arduino IDE's Serial Monitor to see the debug messages.

---

## Part 2: Testing with a Python Script

Now, let's send a command from your computer to the Arduino. The project includes a tool perfect for this.

### Steps:

1.  **Find your Arduino's Serial Port:**
    *   **Windows:** Open Device Manager, look under "Ports (COM & LPT)". Your Arduino will be listed as a "USB Serial Device" or similar, with a COM port next to it (e.g., `COM3`).
    *   **macOS / Linux:** Open a terminal and run `ls /dev/tty.*`. Your Arduino will likely be `/dev/tty.usbmodem...` or `/dev/ttyACM...`.

2.  **Run the Test Script:**
    Open a terminal in the project directory and run the following command, replacing `YOUR_COM_PORT` with the port you found.

    ```bash
    # For Windows
    python tools/serial/driver_demo.py YOUR_COM_PORT
    
    # For macOS/Linux
    python tools/serial/driver_demo.py 'YOUR_COM_PORT'
    ```

    This script (`tools/serial/driver_demo.py`) will automatically find the `SerialDriver`, connect to your Arduino, and send a pre-defined test command (`{"command": "set_power", "params": {"power": "on"}}`).

    If everything is correct, you should see the LED on your Arduino turn on, and you'll see "Turning fan ON" in your Arduino's Serial Monitor.

    You can modify `tools/serial/driver_demo.py` to send different commands, like `set_speed`, to test all your device's functions.

---

## Part 3: Full Project Integration

After testing, you can integrate your device into the main application. This requires two steps: defining your device in the configuration and modifying the main application to load it.

### Step 3.1: Configure Your Device

Open the `config/devices.yaml` file and add your Arduino fan to the list of devices.

```yaml
# config/devices.yaml

# ... (other configurations)

devices:
  # ... (other devices)
  
  - deviceId: "scent_fan_01"
    deviceClass: "Fan"
    label: "Scent-emitting Fan"
    protocol: "serial"
    connectivityInterface: "serial_interface_0"
    capabilities:
      - "power"
      # Add "speed" if your fan supports it
      - "speed"

connectivityInterfaces:
  # ... (other interfaces)

  - name: "serial_interface_0"
    protocol: "serial"
    # IMPORTANT: Change this to your Arduino's COM port
    port: "COM3" 
    baudrate: 9600
```

### Step 3.2: Modify the Main Application (Required Fix)

As of now, the main application (`src/main.py`) is hardcoded to only use the MQTT protocol. You need to modify it to load the devices from your `devices.yaml` file.

**Open `src/main.py` and replace its content with the following:**

This corrected version reads the YAML file, finds all defined devices and interfaces, and starts the correct driver for each one.

```python
import asyncio
import logging
from config_loader import ConfigLoader
from device_manager import DeviceManager
from device_driver.driver_factory import DriverFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Main entry point for the application.
    Initializes and starts the device manager and protocol servers.
    """
    logging.info("Starting application")

    # Load configurations
    config_loader = ConfigLoader(
        'config/devices.yaml',
        'config/effects.yaml',
        'config/protocols.yaml'
    )
    
    try:
        devices_config = config_loader.load_devices_config()
        # effects_config is loaded but not directly used here, handled by EffectDispatcher
        # protocols_config is loaded but not directly used here, handled by ProtocolServer
        logging.info("Configuration loaded successfully.")
    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}")
        return
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return

    # Create a list to hold all our driver instances
    drivers = []
    
    # Create drivers for each connectivity interface defined in the config
    for interface_config in devices_config.get('connectivityInterfaces', []):
        try:
            logging.info(f"Creating driver for interface: {interface_config.get('name')}")
            driver = DriverFactory.create_driver(interface_config)
            if driver:
                drivers.append(driver)
        except Exception as e:
            logging.error(f"Failed to create driver for interface {interface_config.get('name')}: {e}")

    if not drivers:
        logging.warning("No drivers were created. Please check your config/devices.yaml.")
        return

    # Initialize the DeviceManager with all the created drivers
    device_manager = DeviceManager(drivers, config_loader)

    logging.info("DeviceManager initialized.")
    logging.info("Application running. Press Ctrl+C to exit.")

    # Keep the application running
    try:
        while True:
            await asyncio.sleep(3600)  # Keep running, sleep for an hour
    except asyncio.CancelledError:
        logging.info("Application shutting down.")
    finally:
        # Perform any cleanup if necessary
        pass

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")

```

### Step 3.3: Run the Main Application

Now you can run the main application. Any other part of the system that sends a command to `scent_fan_01` will now correctly route that command through the `SerialDriver` to your Arduino.

```bash
python src/main.py
```

Your Arduino device is now fully integrated with your project!

```