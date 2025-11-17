#!/usr/bin/env python3
"""
MQTT Server demo - demonstrates receiving and processing effects via MQTT.

This example shows how to:
1. Start an MQTT server that listens for effect requests
2. Process incoming JSON/YAML effect metadata
3. Dispatch effects to mock devices
4. Publish responses back to clients

Prerequisites:
- MQTT broker running (e.g., mosquitto on localhost:1883)
- Install: pip install paho-mqtt

To test:
1. Run this script: python examples/mqtt_server_demo.py
2. In another terminal, publish effects:
   
   mosquitto_pub -t "effects/light" -m \\
     '{"effect_type":"light","timestamp":0,"duration":1000,\\
      "intensity":100}'
   mosquitto_pub -t "effects/wind" -m \\
     '{"effect_type":"wind","timestamp":0,"duration":2000,\\
      "intensity":75}'
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher
from src.protocol_server import MQTTServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def on_effect_received(effect):
    """Callback when effect is received."""
    logger.info(
        f"✓ Received effect: {effect.effect_type} "
        f"(intensity={effect.intensity}, duration={effect.duration}ms)"
    )


def main():
    print("\n" + "=" * 60)
    print("PythonPlaySEM MQTT Server Demo")
    print("=" * 60)

    # Create components
    logger.info("Initializing components...")

    # Use mock client for demo (in production, use real DeviceManager)
    mock_client = type("MockClient", (), {"publish": lambda *args: None})()
    device_manager = DeviceManager(client=mock_client)

    # Create dispatcher
    dispatcher = EffectDispatcher(device_manager)

    # Create MQTT server
    # Change "localhost" to your MQTT broker address
    server = None
    try:
        server = MQTTServer(
            broker_address="localhost",
            dispatcher=dispatcher,
            subscribe_topic="effects/#",
            port=1883,
            on_effect_received=on_effect_received,
        )

        logger.info("Starting MQTT server...")
        server.start()

        print("\n" + "=" * 60)
        print("MQTT Server is running!")
        print("=" * 60)
        print("\nListening for effects on topics: effects/*")
        print("\nTo send test effects, use mosquitto_pub:")
        print("\n  # Light effect")
        print(
            '  mosquitto_pub -t "effects/light" -m \'{"effect_type":"light",'
            '"timestamp":0,"duration":1000,"intensity":100}\''
        )
        print("\n  # Wind effect")
        print(
            '  mosquitto_pub -t "effects/wind" -m \'{"effect_type":"wind",'
            '"timestamp":0,"duration":2000,"intensity":75}\''
        )
        print("\n  # YAML format also supported!")
        print(
            '  mosquitto_pub -t "effects/vibration" -m '
            '"effect_type: vibration'
        )
        print("timestamp: 0")
        print("duration: 500")
        print('intensity: 80"')
        print("\nPress Ctrl+C to stop the server.\n")

        # Keep server running
        while True:
            time.sleep(1)

    except ConnectionRefusedError:
        logger.error("\n❌ Could not connect to MQTT broker!")
        logger.error("Make sure mosquitto or another MQTT broker is running.")
        logger.error("\nInstall mosquitto:")
        logger.error("  - Windows: choco install mosquitto")
        logger.error("  - macOS: brew install mosquitto")
        logger.error("  - Linux: sudo apt-get install mosquitto")
        logger.error(
            "\nOr use a public broker (not recommended for production):"
        )
        logger.error('  Change broker_address to "test.mosquitto.org"')
        return 1
    except KeyboardInterrupt:
        logger.info("\n\nShutting down server...")
        if server:
            server.stop()
        logger.info("Server stopped. Goodbye!")
        return 0
        return 0

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
