#!/usr/bin/env python3
"""
Bluetooth BLE Driver Demo.

Demonstrates Bluetooth Low Energy communication with wireless devices.
Shows device scanning, connection management, GATT services, and
characteristic read/write operations.

Prerequisites:
- Install: pip install bleak
- Have BLE device nearby (Arduino Nano 33, ESP32, etc.)

Usage:
  python examples/demos/bluetooth_driver_demo.py
"""

import sys
import asyncio
import logging
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_driver.bluetooth_driver import BluetoothDriver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def demo_scan_devices():
    """Demo 1: Scan for nearby BLE devices."""
    print("\n" + "=" * 60)
    print("Demo 1: Scan for BLE Devices")
    print("=" * 60)

    print("\n🔍 Scanning for 10 seconds...")
    devices = await BluetoothDriver.scan_devices(timeout=10.0)

    if not devices:
        print("\n❌ No BLE devices found")
        print("   Make sure Bluetooth is enabled and a BLE device is nearby")
        return None

    print(f"\n✅ Found {len(devices)} BLE device(s):\n")

    for i, device in enumerate(devices, 1):
        print(f"{i}. {device['name']}")
        print(f"   Address: {device['address']}")
        print(f"   Signal: {device['rssi']} dBm")
        print()

    return devices


async def demo_find_device():
    """Demo 2: Find specific device by name."""
    print("\n" + "=" * 60)
    print("Demo 2: Find Specific Device")
    print("=" * 60)

    # Try to find Arduino
    print("\n🔍 Looking for Arduino...")
    device = await BluetoothDriver.find_device(name="Arduino", timeout=10.0)

    if device:
        print(f"\n✅ Found Arduino!")
        print(f"   Name: {device['name']}")
        print(f"   Address: {device['address']}")
        print(f"   Signal: {device['rssi']} dBm")
        return device

    print("\n❌ No Arduino found")
    return None


async def demo_connect_and_services(address: str):
    """Demo 3: Connect and discover services."""
    print("\n" + "=" * 60)
    print(f"Demo 3: Connect and Discover Services")
    print("=" * 60)

    driver = BluetoothDriver(address=address)

    try:
        print(f"\n🔗 Connecting to {address}...")
        if not await driver.connect():
            print("❌ Connection failed")
            return None

        print("✅ Connected!")

        # Get services
        print("\n📋 GATT Services:")
        services = await driver.get_services()

        if not services:
            print("   No services found")
            return driver

        for service_uuid, service_info in services.items():
            print(f"\n  Service: {service_uuid[:8]}...")
            print(f"  Description: {service_info.get('description', 'N/A')}")

            chars = service_info.get("characteristics", [])
            if chars:
                print(f"  Characteristics ({len(chars)}):")
                for char in chars:
                    props = ", ".join(char.get("properties", []))
                    print(f"    - {char['uuid'][:8]}... ({props})")

        return driver

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


async def demo_write_characteristic(driver: BluetoothDriver, uuid: str):
    """Demo 4: Write to characteristic."""
    print("\n" + "=" * 60)
    print("Demo 4: Write to Characteristic")
    print("=" * 60)

    if not driver or not driver.is_connected:
        print("❌ Not connected")
        return

    print(f"\n📤 Writing to {uuid[:8]}...")

    # Example writes
    commands = [
        (b"\xff\x00\x64", "Binary: Turn on LED (intensity 100)"),
        (b"\x00\x00\x00", "Binary: Turn off LED"),
        ("LED:255\n".encode(), "ASCII: LED full brightness"),
    ]

    for data, description in commands:
        print(f"\n  Sending: {description}")
        print(f"  Data: {data.hex() if isinstance(data, bytes) else data}")

        success = await driver.write_characteristic(uuid, data)
        if success:
            print("  ✅ Write successful")
        else:
            print("  ❌ Write failed")

        await asyncio.sleep(1)


async def demo_notifications(driver: BluetoothDriver, uuid: str):
    """Demo 5: Subscribe to notifications."""
    print("\n" + "=" * 60)
    print("Demo 5: Receive Notifications")
    print("=" * 60)

    if not driver or not driver.is_connected:
        print("❌ Not connected")
        return

    notification_count = 0

    def notification_handler(sender: int, data: bytearray):
        """Handle incoming notifications."""
        nonlocal notification_count
        notification_count += 1
        print(
            f"  📨 Notification #{notification_count}: {data.hex()} ({bytes(data)})"
        )

    print(f"\n🔔 Subscribing to notifications on {uuid[:8]}...")

    success = await driver.start_notify(uuid, notification_handler)
    if not success:
        print("❌ Failed to start notifications")
        print("   (Characteristic may not support notifications)")
        return

    print("✅ Listening for notifications...")
    print("   Waiting 10 seconds for data...")

    # Wait for notifications
    await asyncio.sleep(10)

    # Stop notifications
    await driver.stop_notify(uuid)
    print(f"\n✅ Received {notification_count} notification(s)")


async def demo_read_write_cycle(driver: BluetoothDriver, uuid: str):
    """Demo 6: Read-Write cycle."""
    print("\n" + "=" * 60)
    print("Demo 6: Read-Write Cycle")
    print("=" * 60)

    if not driver or not driver.is_connected:
        print("❌ Not connected")
        return

    # Write command
    print(f"\n📤 Writing command to {uuid[:8]}...")
    command = b"\xff\x00\x64"
    success = await driver.write_characteristic(uuid, command)

    if success:
        print(f"✅ Wrote: {command.hex()}")
    else:
        print("❌ Write failed")
        return

    # Small delay
    await asyncio.sleep(0.5)

    # Read response
    print(f"\n📥 Reading from {uuid[:8]}...")
    data = await driver.read_characteristic(uuid)

    if data:
        print(f"✅ Read: {data.hex()} ({len(data)} bytes)")
    else:
        print("❌ Read failed (may not be readable)")


async def demo_effect_control(driver: BluetoothDriver, uuid: str):
    """Demo 7: Send sensory effects via BLE."""
    print("\n" + "=" * 60)
    print("Demo 7: BLE Effect Control")
    print("=" * 60)

    if not driver or not driver.is_connected:
        print("❌ Not connected")
        return

    effects = [
        ("LIGHT", 255, 1000),
        ("LIGHT", 128, 500),
        ("VIBRATION", 200, 800),
        ("FAN", 150, 2000),
    ]

    print("\n🎯 Sending sensory effects...")

    for effect_type, intensity, duration in effects:
        # Format: EFFECT:<type>:<intensity>:<duration>\n
        command = f"EFFECT:{effect_type}:{intensity}:{duration}\n"

        print(f"\n  {effect_type}")
        print(f"    Intensity: {intensity}")
        print(f"    Duration: {duration}ms")

        success = await driver.send_command(uuid, command)
        if success:
            print("    ✅ Sent")
        else:
            print("    ❌ Failed")

        await asyncio.sleep(duration / 1000.0 + 0.5)

    print("\n✅ All effects sent")


async def interactive_mode():
    """Interactive mode for testing."""
    print("\n" + "=" * 60)
    print("Interactive Mode")
    print("=" * 60)

    # Scan for devices
    print("\n🔍 Scanning for devices...")
    devices = await BluetoothDriver.scan_devices(timeout=5.0)

    if not devices:
        print("❌ No devices found")
        return

    # Select device
    print("\nAvailable devices:")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device['name']} ({device['address']})")

    try:
        choice = int(input("\nSelect device (number): "))
        device = devices[choice - 1]
    except (ValueError, IndexError):
        print("Invalid choice")
        return

    # Connect
    driver = BluetoothDriver(address=device["address"])

    try:
        print(f"\n🔗 Connecting to {device['name']}...")
        if not await driver.connect():
            print("❌ Connection failed")
            return

        print("✅ Connected!")

        # Show services
        services = await driver.get_services()
        print("\nAvailable characteristics:")

        char_list = []
        idx = 1
        for service in services.values():
            for char in service.get("characteristics", []):
                char_list.append(char["uuid"])
                props = ", ".join(char.get("properties", []))
                print(f"{idx}. {char['uuid'][:8]}... ({props})")
                idx += 1

        if not char_list:
            print("No characteristics found")
            await driver.disconnect()
            return

        # Select characteristic
        try:
            choice = int(input("\nSelect characteristic (number): "))
            uuid = char_list[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice")
            await driver.disconnect()
            return

        print(f"\nUsing characteristic: {uuid}")
        print("\nCommands:")
        print("  'write <hex>' - Write hex bytes (e.g., 'write FF 00 64')")
        print("  'send <text>'  - Send text")
        print("  'read'        - Read characteristic")
        print("  'notify'      - Start notifications")
        print("  'quit'        - Exit")
        print()

        notify_active = False

        def notify_handler(sender, data):
            print(f"📨 Notification: {bytes(data).hex()}")

        while True:
            cmd = input("> ").strip()

            if cmd == "quit":
                break

            elif cmd.startswith("write "):
                hex_str = cmd[6:].replace(" ", "")
                try:
                    data = bytes.fromhex(hex_str)
                    success = await driver.write_characteristic(uuid, data)
                    if success:
                        print(f"✅ Wrote: {data.hex()}")
                    else:
                        print("❌ Write failed")
                except ValueError:
                    print("Invalid hex format")

            elif cmd.startswith("send "):
                text = cmd[5:]
                success = await driver.send_command(uuid, text + "\n")
                if success:
                    print(f"✅ Sent: {text}")
                else:
                    print("❌ Send failed")

            elif cmd == "read":
                data = await driver.read_characteristic(uuid)
                if data:
                    print(f"✅ Read: {data.hex()}")
                else:
                    print("❌ Read failed")

            elif cmd == "notify":
                if not notify_active:
                    success = await driver.start_notify(uuid, notify_handler)
                    if success:
                        print("✅ Notifications started (will auto-print)")
                        notify_active = True
                    else:
                        print("❌ Failed to start notifications")
                else:
                    await driver.stop_notify(uuid)
                    print("✅ Notifications stopped")
                    notify_active = False

            else:
                print("Unknown command")

        await driver.disconnect()
        print("\n✅ Disconnected")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Interactive mode error: {e}", exc_info=True)


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("📱 Bluetooth BLE Driver Demo - PythonPlaySEM")
    print("=" * 60)

    # Demo 1: Scan for devices
    devices = await demo_scan_devices()

    if not devices:
        print("\n❌ No BLE devices found")
        print("   Make sure Bluetooth is enabled and devices are nearby")
        return

    # Demo 2: Find specific device
    arduino = await demo_find_device()

    # Select device for connection demos
    target_device = arduino if arduino else devices[0]
    address = target_device["address"]

    print(f"\n💡 Using device: {target_device['name']} ({address})")

    # Demo 3: Connect and discover services
    driver = await demo_connect_and_services(address)

    if not driver or not driver.is_connected:
        print("\n❌ Could not connect to device")
        return

    # Get first writable characteristic
    services = await driver.get_services()
    writable_uuid = None

    for service in services.values():
        for char in service.get("characteristics", []):
            if "write" in char.get("properties", []):
                writable_uuid = char["uuid"]
                break
        if writable_uuid:
            break

    if writable_uuid:
        print(f"\n💡 Found writable characteristic: {writable_uuid[:8]}...")

        # Demo 4: Write to characteristic
        await demo_write_characteristic(driver, writable_uuid)

        # Demo 5: Notifications (if supported)
        # await demo_notifications(driver, writable_uuid)

        # Demo 6: Read-Write cycle
        # await demo_read_write_cycle(driver, writable_uuid)

        # Demo 7: Effect control
        # await demo_effect_control(driver, writable_uuid)
    else:
        print("\n⚠️  No writable characteristics found")

    # Disconnect
    await driver.disconnect()

    # Interactive mode
    print("\n" + "=" * 60)
    choice = input("\nEnter interactive mode? (y/n): ").strip().lower()
    if choice == "y":
        await interactive_mode()

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
