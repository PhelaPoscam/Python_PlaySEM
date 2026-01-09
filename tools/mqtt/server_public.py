#!/usr/bin/env python3
"""
MQTT Server demo using PUBLIC test broker - NO local installation needed!

This example uses test.mosquitto.org public broker for testing.

⚠️ WARNING: Public brokers are NOT secure - use only for testing!

To test:
1. Run this script: python examples/mqtt_server_demo_public.py
2. Run the test client: python examples/test_mqtt_client_public.py
   OR use mosquitto_pub directly:

   mosquitto_pub -h test.mosquitto.org -t "effects/light" -m '{"effect_type":"light","timestamp":0,"duration":1000,"intensity":100}'
"""

import time
import logging

from playsem import DeviceManager, EffectDispatcher
from playsem.protocol_servers import MQTTServer

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
    print("PythonPlaySEM MQTT Server Demo - PUBLIC BROKER")
    print("=" * 60)
    print("\n⚠️  Using public test broker: test.mosquitto.org")
    print("⚠️  NOT secure - for testing only!")
    print()

    # Create components
    logger.info("Initializing components...")

    # Use mock client for demo
    mock_client = type("MockClient", (), {"publish": lambda *args: None})()
    device_manager = DeviceManager(client=mock_client)

    # Create dispatcher
    dispatcher = EffectDispatcher(device_manager)

    # Create MQTT server using PUBLIC broker
    server = None
    try:
        server = MQTTServer(
            broker_address="test.mosquitto.org",  # Public test broker
            dispatcher=dispatcher,
            subscribe_topic="effects/#",
            port=1883,
            on_effect_received=on_effect_received,
        )

        logger.info("Connecting to public MQTT broker...")
        server.start()

        print("\n" + "=" * 60)
        print("MQTT Server is running!")
        print("=" * 60)
        print("\nConnected to: test.mosquitto.org:1883")
        print("Listening for effects on topics: effects/*")
        print("\nTo send test effects:")
        print("\n  Option 1: Run the test client")
        print("    python examples/test_mqtt_client_public.py")
        print("\n  Option 2: Use mosquitto_pub directly")
        print("    mosquitto_pub -h test.mosquitto.org \\")
        print('      -t "effects/light" -m \'{"effect_type":"light",...}\'')
        print("\nPress Ctrl+C to stop the server.\n")

        # Keep server running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n\nShutting down server...")
        if server:
            server.stop()
        logger.info("Server stopped. Goodbye!")
        return 0

    except Exception as e:
        logger.error(f"\n❌ Error connecting to public broker: {e}")
        logger.error("\nPossible issues:")
        logger.error("  1. No internet connection")
        logger.error("  2. test.mosquitto.org is down")
        logger.error("  3. Firewall blocking port 1883")
        if server:
            server.stop()
        return 1


if __name__ == "__main__":
    sys.exit(main())
