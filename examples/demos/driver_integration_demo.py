#!/usr/bin/env python3
"""
Driver Integration Demo - PythonPlaySEM

Demonstrates DeviceManager working with multiple driver types:
- MQTT Driver (network-based)
- Serial Driver (USB/Arduino)
- Bluetooth Driver (BLE wireless)
- Mock Driver (testing)

Shows how the same DeviceManager interface works seamlessly with
different connectivity methods.
"""

import sys
import time
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_manager import DeviceManager
from src.device_driver.mqtt_driver import MQTTDriver
from src.device_driver.serial_driver import SerialDriver
from src.device_driver.bluetooth_driver import BluetoothDriver
from src.device_driver.driver_factory import create_driver, auto_detect_driver


def demo_mqtt_driver():
    """Demo 1: DeviceManager with MQTT Driver."""
    print("\n" + "=" * 60)
    print("Demo 1: DeviceManager with MQTT Driver")
    print("=" * 60)

    # Create MQTT driver
    mqtt_driver = MQTTDriver(broker="localhost", port=1883)

    # Create DeviceManager with MQTT driver
    manager = DeviceManager(connectivity_driver=mqtt_driver)

    print(f"\n✅ Driver: {manager.get_driver_info()}")
    print(f"   Connected: {manager.is_connected()}")

    # Send commands
    print("\n📤 Sending MQTT commands...")
    manager.send_command(
        device_id="devices/light_001",
        command="set_intensity",
        params={"intensity": 255, "duration": 1000},
    )

    manager.send_command(
        device_id="devices/fan_002", command="set_speed", params={"speed": 150}
    )

    print("✅ Commands sent via MQTT")

    # Cleanup
    manager.disconnect()
    print("\n✅ Disconnected")


def demo_serial_driver():
    """Demo 2: DeviceManager with Serial Driver."""
    print("\n" + "=" * 60)
    print("Demo 2: DeviceManager with Serial Driver")
    print("=" * 60)

    # List available serial ports
    ports = SerialDriver.list_ports()
    print(f"\n📍 Available serial ports: {len(ports)}")
    for port_info in ports[:3]:  # Show first 3
        print(f"   - {port_info['device']}: {port_info['description']}")

    if not ports:
        print("   ❌ No serial ports found - skipping serial demo")
        return

    # Create Serial driver (use first available port)
    serial_driver = SerialDriver(port=ports[0]["device"], baudrate=9600)

    # Create DeviceManager with Serial driver
    manager = DeviceManager(connectivity_driver=serial_driver)

    print(f"\n✅ Driver: {manager.get_driver_info()}")
    print(f"   Connected: {manager.is_connected()}")

    # Send commands
    print("\n📤 Sending serial commands...")
    manager.send_command(
        device_id="arduino_001",
        command="SET_LED",
        params={"intensity": 255, "color": "red"},
    )

    manager.send_command(
        device_id="arduino_001", command="SET_MOTOR", params={"speed": 100}
    )

    print("✅ Commands sent via Serial")

    # Cleanup
    manager.disconnect()
    print("\n✅ Disconnected")


def demo_driver_factory():
    """Demo 3: Using Driver Factory."""
    print("\n" + "=" * 60)
    print("Demo 3: Driver Factory - Auto-creation")
    print("=" * 60)

    # Create drivers from configuration dictionaries
    configs = [
        {"type": "mqtt", "broker": "localhost", "port": 1883},
        {"type": "serial", "port": "COM3", "baudrate": 9600},
        {"type": "bluetooth", "address": "AA:BB:CC:DD:EE:FF"},
    ]

    for config in configs:
        print(f"\n📋 Config: {config}")

        try:
            # Create driver from config
            driver_type = config.pop("type")
            driver = create_driver(driver_type, **config)

            if driver:
                # Create DeviceManager
                manager = DeviceManager(connectivity_driver=driver)
                info = manager.get_driver_info()

                print(f"   ✅ Created {info['type']} driver")
                print(f"   Connected: {manager.is_connected()}")

                # Attempt to send test command
                manager.send_command(
                    device_id="test_device", command="ping", params={}
                )

                manager.disconnect()
            else:
                print("   ❌ Driver creation failed")

        except Exception as e:
            print(f"   ⚠️  Error: {e}")


def demo_auto_detect():
    """Demo 4: Auto-detect driver from parameters."""
    print("\n" + "=" * 60)
    print("Demo 4: Auto-detect Driver")
    print("=" * 60)

    # Find available serial port
    ports = SerialDriver.list_ports()
    serial_port = ports[0]["device"] if ports else None

    # Auto-detect will prioritize: MQTT > Serial > Bluetooth
    print("\n🔍 Auto-detecting driver...")

    driver = auto_detect_driver(
        mqtt_broker="localhost",
        serial_port=serial_port,
        bluetooth_address=None,
    )

    if driver:
        manager = DeviceManager(connectivity_driver=driver)
        info = manager.get_driver_info()

        print(f"   ✅ Auto-detected: {info['type']} driver")
        print(f"   Configuration: {info}")
        print(f"   Connected: {manager.is_connected()}")

        manager.disconnect()
    else:
        print("   ❌ No driver could be auto-detected")


def demo_backward_compatibility():
    """Demo 5: Backward compatibility with old API."""
    print("\n" + "=" * 60)
    print("Demo 5: Backward Compatibility (Old API)")
    print("=" * 60)

    # Old way: create DeviceManager with broker_address
    print("\n📜 Using legacy API (broker_address parameter)...")

    manager = DeviceManager(broker_address="localhost")

    info = manager.get_driver_info()
    print(f"   ✅ Created via legacy API: {info['type']} driver")
    print(f"   Broker: {info.get('broker')}")
    print(f"   Connected: {manager.is_connected()}")

    # Old send_command still works
    manager.send_command(
        device_id="devices/test",
        command="ping",
        params={"timestamp": time.time()},
    )

    print("   ✅ Old API still functional!")

    manager.disconnect()


def demo_multiple_managers():
    """Demo 6: Multiple DeviceManagers with different drivers."""
    print("\n" + "=" * 60)
    print("Demo 6: Multiple Managers - Different Drivers")
    print("=" * 60)

    # Create multiple managers for different device types
    managers = []

    # MQTT manager for network devices
    print("\n1️⃣  Creating MQTT manager...")
    mqtt_mgr = DeviceManager(broker_address="localhost")
    managers.append(("MQTT", mqtt_mgr))

    # Serial manager for USB devices
    ports = SerialDriver.list_ports()
    if ports:
        print("2️⃣  Creating Serial manager...")
        serial_driver = SerialDriver(port=ports[0]["device"])
        serial_mgr = DeviceManager(connectivity_driver=serial_driver)
        managers.append(("Serial", serial_mgr))

    # Display all managers
    print(f"\n✅ Created {len(managers)} device managers:")
    for name, mgr in managers:
        info = mgr.get_driver_info()
        print(f"   - {name}: {info['type']} (connected: {info['connected']})")

    # Send commands through different managers
    print("\n📤 Sending commands through each manager...")
    for name, mgr in managers:
        mgr.send_command(
            device_id=f"{name.lower()}_device",
            command="test",
            params={"source": name},
        )
        print(f"   ✅ {name} command sent")

    # Cleanup
    print("\n🧹 Cleanup...")
    for name, mgr in managers:
        mgr.disconnect()

    print("✅ All managers disconnected")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("🔌 Driver Integration Demo - PythonPlaySEM")
    print("=" * 60)

    demos = [
        ("MQTT Driver", demo_mqtt_driver, True),
        ("Serial Driver", demo_serial_driver, True),
        ("Driver Factory", demo_driver_factory, True),
        ("Auto-detect", demo_auto_detect, True),
        ("Backward Compatibility", demo_backward_compatibility, True),
        ("Multiple Managers", demo_multiple_managers, True),
    ]

    for name, demo_func, enabled in demos:
        if enabled:
            try:
                demo_func()
            except KeyboardInterrupt:
                print("\n\n⚠️  Demo interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ {name} demo error: {e}")
                import traceback

                traceback.print_exc()

            # Small delay between demos
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print("✅ All demos complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
