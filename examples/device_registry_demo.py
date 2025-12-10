"""
Example: Using Device Registry with Multiple Protocols

Demonstrates how the Device Registry solves protocol isolation by
allowing devices from ANY protocol to be visible to ALL protocols.

This example simulates:
1. MQTT device announcing itself
2. WebSocket client querying for devices
3. Seeing the MQTT device from WebSocket (previously impossible!)
"""

import asyncio
from playsem import DeviceRegistry


def main():
    print("=" * 60)
    print("Device Registry Example: Cross-Protocol Device Discovery")
    print("=" * 60)
    print()

    # Create the central device registry
    registry = DeviceRegistry()

    # Add a listener to monitor device events
    def on_device_event(event_type: str, device):
        print(f"📢 Event: {event_type} - {device.name} ({device.id})")

    registry.add_listener(on_device_event)

    print("✅ Device Registry initialized\n")

    # Simulate MQTT device announcing itself
    print("--- Scenario 1: MQTT Device Announces ---")
    mqtt_device_announcement = {
        "id": "mqtt_light_001",
        "name": "Smart Living Room Light",
        "type": "light",
        "address": "192.168.1.100",
        "protocols": ["mqtt"],
        "capabilities": ["light", "color", "brightness"],
        "connection_mode": "isolated",
        "metadata": {
            "mqtt_topic": "devices/light_001",
            "firmware_version": "1.2.3",
        },
    }

    device = registry.register_device(
        mqtt_device_announcement, source_protocol="mqtt"
    )
    print(f"✅ MQTT device registered: {device.name}")
    print(f"   ID: {device.id}")
    print(f"   Protocols: {device.protocols}")
    print(f"   Capabilities: {device.capabilities}\n")

    # Simulate WebSocket device connecting
    print("--- Scenario 2: WebSocket Device Connects ---")
    websocket_device = {
        "id": "ws_vibration_001",
        "name": "Haptic Vest",
        "type": "vibration",
        "address": "COM3",
        "protocols": ["websocket", "serial"],
        "capabilities": ["vibration", "intensity_control"],
        "connection_mode": "direct",
    }

    device = registry.register_device(
        websocket_device, source_protocol="websocket"
    )
    print(f"✅ WebSocket device registered: {device.name}")
    print(f"   ID: {device.id}")
    print(f"   Protocols: {device.protocols}\n")

    # Now the magic: Query ALL devices regardless of protocol
    print("--- Scenario 3: Cross-Protocol Device Discovery ---")
    print("📡 WebSocket client asks: 'What devices are available?'\n")

    all_devices = registry.get_all_devices()
    print(f"Found {len(all_devices)} devices in registry:")
    for dev in all_devices:
        print(f"  • {dev.name} ({dev.type}) - via {dev.source_protocol}")
        print(f"    Supports protocols: {', '.join(dev.protocols)}")

    print("\n🎉 SUCCESS! WebSocket client can now see MQTT device!")
    print("   (Previously impossible due to protocol isolation)\n")

    # Query by specific protocol
    print("--- Scenario 4: Protocol-Specific Queries ---")
    mqtt_devices = registry.get_devices_by_protocol("mqtt")
    print(f"Devices supporting MQTT: {len(mqtt_devices)}")
    for dev in mqtt_devices:
        print(f"  • {dev.name}")

    ws_devices = registry.get_devices_by_protocol("websocket")
    print(f"\nDevices supporting WebSocket: {len(ws_devices)}")
    for dev in ws_devices:
        print(f"  • {dev.name}")

    # Query by device type
    print("\n--- Scenario 5: Query by Device Type ---")
    light_devices = registry.get_devices_by_type("light")
    print(f"Light devices: {len(light_devices)}")
    for dev in light_devices:
        print(f"  • {dev.name} - {dev.address}")

    # Query by capability
    print("\n--- Scenario 6: Query by Capability ---")
    vibration_capable = registry.get_devices_by_capability("vibration")
    print(f"Devices with vibration capability: {len(vibration_capable)}")
    for dev in vibration_capable:
        print(f"  • {dev.name}")

    # Show statistics
    print("\n--- Registry Statistics ---")
    stats = registry.get_stats()
    print(f"Total devices: {stats['total_devices']}")
    print(
        f"Protocol isolation: {'ENABLED' if stats['protocol_isolation_enabled'] else 'DISABLED'}"
    )
    print(f"Protocols in use: {', '.join(stats['protocols'])}")
    print("Devices by protocol:")
    for protocol, count in stats["devices_by_protocol"].items():
        print(f"  • {protocol}: {count}")
    print("Devices by type:")
    for device_type, count in stats["devices_by_type"].items():
        print(f"  • {device_type}: {count}")

    # Demonstrate protocol isolation mode
    print("\n" + "=" * 60)
    print("--- Scenario 7: Protocol Isolation Mode ---")
    print("=" * 60)
    print(
        "\n🔒 Enabling protocol isolation (like Super Controller Device Simulator)..."
    )
    registry.set_protocol_isolation(True)

    print("\n📡 WebSocket client asks: 'What devices are available?'")
    ws_visible_devices = registry.get_all_devices(
        requesting_protocol="websocket"
    )
    print(f"WebSocket client sees {len(ws_visible_devices)} device(s):")
    for dev in ws_visible_devices:
        print(f"  • {dev.name} ({dev.type})")

    print("\n📡 MQTT client asks: 'What devices are available?'")
    mqtt_visible_devices = registry.get_all_devices(requesting_protocol="mqtt")
    print(f"MQTT client sees {len(mqtt_visible_devices)} device(s):")
    for dev in mqtt_visible_devices:
        print(f"  • {dev.name} ({dev.type})")

    print(
        "\n✅ Protocol isolation working! Each protocol only sees its own devices."
    )

    print("\n🔓 Disabling protocol isolation (shared mode)...")
    registry.set_protocol_isolation(False)

    print("\n📡 WebSocket client asks again: 'What devices are available?'")
    ws_visible_devices = registry.get_all_devices(
        requesting_protocol="websocket"
    )
    print(f"WebSocket client now sees {len(ws_visible_devices)} device(s):")
    for dev in ws_visible_devices:
        print(f"  • {dev.name} ({dev.type})")

    print("\n✅ Shared mode active! All devices visible to all protocols.")

    print("\n" + "=" * 60)
    print("Key Benefits of Device Registry:")
    print("=" * 60)
    print("✅ Protocol-agnostic: Devices from ANY protocol visible to ALL")
    print(
        "✅ Protocol isolation: Optional isolation mode like Super Controller"
    )
    print("✅ Thread-safe: Multiple protocols can access concurrently")
    print("✅ Flexible queries: By protocol, type, capability, etc.")
    print("✅ Event notifications: Listen for device changes")
    print("✅ Automatic merging: Same device via multiple protocols")
    print()


if __name__ == "__main__":
    main()
