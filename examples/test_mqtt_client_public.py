#!/usr/bin/env python3
"""
MQTT Test Client - PUBLIC BROKER VERSION

Sends test effects to the public MQTT broker (test.mosquitto.org).
Use this with mqtt_server_demo_public.py for testing.

⚠️ WARNING: Public brokers are NOT secure - use only for testing!

Usage:
1. Start the server: python examples/mqtt_server_demo_public.py
2. Run this client: python examples/test_mqtt_client_public.py
"""

import sys
import time
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import paho.mqtt.client as mqtt


def main():
    print("\n" + "=" * 60)
    print("MQTT Test Client - PUBLIC BROKER")
    print("=" * 60)
    print("\n⚠️  Using public test broker: test.mosquitto.org")
    print("⚠️  NOT secure - for testing only!\n")
    
    # Create MQTT client
    client = mqtt.Client(client_id="test_mqtt_publisher")
    
    try:
        print("Connecting to test.mosquitto.org:1883...")
        client.connect("test.mosquitto.org", 1883, 60)
        client.loop_start()
        
        time.sleep(1)  # Give time to connect
        
        print("✓ Connected!\n")
        print("=" * 60)
        print("Sending Test Effects")
        print("=" * 60)
        
        # Define test effects
        effects = [
            {
                "name": "💡 Bright light effect",
                "topic": "effects/light",
                "payload": {
                    "effect_type": "light",
                    "timestamp": 0,
                    "duration": 1000,
                    "intensity": 100
                }
            },
            {
                "name": "💨 Strong wind effect",
                "topic": "effects/wind",
                "payload": {
                    "effect_type": "wind",
                    "timestamp": 0,
                    "duration": 2000,
                    "intensity": 75
                }
            },
            {
                "name": "📳 Vibration effect",
                "topic": "effects/vibration",
                "payload": {
                    "effect_type": "vibration",
                    "timestamp": 0,
                    "duration": 500,
                    "intensity": 80
                }
            },
            {
                "name": "🌸 Scent effect",
                "topic": "effects/scent",
                "payload": {
                    "effect_type": "scent",
                    "timestamp": 0,
                    "duration": 3000,
                    "intensity": 60
                }
            }
        ]
        
        # Send each effect
        for i, effect in enumerate(effects, 1):
            print(f"\n[{i}/{len(effects)}] {effect['name']}")
            print(f"  📤 Publishing to: {effect['topic']}")
            
            payload_str = json.dumps(effect['payload'])
            print(f"  📋 Payload: {payload_str}")
            
            result = client.publish(effect['topic'], payload_str)
            result.wait_for_publish()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("  ✅ Published successfully!")
            else:
                print(f"  ❌ Publish failed with code: {result.rc}")
            
            time.sleep(1)  # Wait between effects
        
        print("\n" + "=" * 60)
        print("✓ All effects sent!")
        print("=" * 60)
        print("\nCheck the server terminal to see received effects.\n")
        
        # Clean up
        client.loop_stop()
        client.disconnect()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPossible issues:")
        print("  1. No internet connection")
        print("  2. test.mosquitto.org is down")
        print("  3. Firewall blocking port 1883")
        return 1


if __name__ == "__main__":
    sys.exit(main())
