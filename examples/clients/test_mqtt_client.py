#!/usr/bin/env python3
"""
Simple MQTT effect sender - sends effects to MQTT server for testing.

This script connects as a client and sends test effects to demonstrate
the MQTT server receiving and processing them.

Usage:
1. Start the MQTT server: python examples/mqtt_server_demo.py
2. Run this script: python examples/test_mqtt_client.py
"""

import sys
import time
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    """Callback when connected to broker."""
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        print("\nSubscribing to response topics...")
        client.subscribe("effects/#")
    else:
        print(f"❌ Failed to connect, return code: {rc}")


def on_message(client, userdata, msg):
    """Callback when message received."""
    try:
        if "response" in msg.topic:
            payload = json.loads(msg.payload.decode())
            print(f"📥 Response received: {json.dumps(payload, indent=2)}")
    except:
        pass


def send_test_effects(client):
    """Send a series of test effects."""

    print("\n" + "=" * 60)
    print("Sending Test Effects")
    print("=" * 60 + "\n")

    effects = [
        {
            "topic": "effects/light",
            "payload": {
                "effect_type": "light",
                "timestamp": 0,
                "duration": 1000,
                "intensity": 100,
            },
            "description": "💡 Bright light effect",
        },
        {
            "topic": "effects/wind",
            "payload": {
                "effect_type": "wind",
                "timestamp": 0,
                "duration": 2000,
                "intensity": 75,
            },
            "description": "💨 Strong wind effect",
        },
        {
            "topic": "effects/vibration",
            "payload": {
                "effect_type": "vibration",
                "timestamp": 0,
                "duration": 500,
                "intensity": 80,
            },
            "description": "📳 Vibration effect",
        },
        {
            "topic": "effects/scent",
            "payload": {
                "effect_type": "scent",
                "timestamp": 0,
                "duration": 3000,
                "intensity": 60,
                "parameters": {"type": "lavender"},
            },
            "description": "🌸 Lavender scent effect",
        },
    ]

    for i, effect in enumerate(effects, 1):
        print(f"\n[{i}/{len(effects)}] {effect['description']}")
        print(f"  📤 Publishing to: {effect['topic']}")
        print(f"  📋 Payload: {json.dumps(effect['payload'])}")

        # Publish effect
        client.publish(effect["topic"], json.dumps(effect["payload"]))

        # Wait a bit between effects
        time.sleep(1.5)

    print("\n" + "=" * 60)
    print("✅ All test effects sent!")
    print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("MQTT Effect Sender - Test Client")
    print("=" * 60)
    print("\nMake sure the MQTT server is running:")
    print("  python examples/mqtt_server_demo.py")
    print("\nConnecting to broker at localhost:1883...\n")

    try:
        # Create client
        client = mqtt.Client(client_id="effect_sender")
        client.on_connect = on_connect
        client.on_message = on_message

        # Connect to broker
        client.connect("localhost", 1883, 60)

        # Start network loop
        client.loop_start()

        # Wait for connection
        time.sleep(2)

        # Send test effects
        send_test_effects(client)

        # Wait for responses
        print("\nWaiting for responses (5 seconds)...")
        time.sleep(5)

        # Cleanup
        client.loop_stop()
        client.disconnect()

        print(
            "\n✅ Test complete! Check the server terminal for effect execution logs.\n"
        )

    except ConnectionRefusedError:
        print("\n❌ ERROR: Could not connect to MQTT broker!")
        print("\nPlease ensure:")
        print("1. Mosquitto (or another MQTT broker) is running")
        print("2. The broker is listening on localhost:1883")
        print("\nTo install mosquitto:")
        print("  Windows: choco install mosquitto")
        print("  macOS:   brew install mosquitto")
        print("  Linux:   sudo apt-get install mosquitto\n")
        return 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
