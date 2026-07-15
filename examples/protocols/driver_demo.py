#!/usr/bin/env python3
"""
Serial Driver Demo.

Demonstrates serial/USB communication with Arduino and other devices.
Shows port discovery, connection management, and data transmission.

Prerequisites:
- Install: pip install pyserial
- Connect USB device (Arduino, ESP32, etc.)

Usage:
  python examples/protocols/driver_demo.py
"""

import sys
from pathlib import Path
import asyncio

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging

from playsem.drivers.serial_driver import SerialDriver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def demo_list_ports():
    """Demo 1: List all available serial ports."""
    print("\n" + "=" * 60)
    print("Demo 1: List Available Serial Ports")
    print("=" * 60)

    ports = SerialDriver.list_ports()

    if not ports:
        print("\n[FAIL] No serial ports found")
        print("   Make sure a USB device is connected")
        return None

    print(f"\n[OK] Found {len(ports)} serial port(s):\n")

    for i, port in enumerate(ports, 1):
        print(f"{i}. {port['device']}")
        print(f"   Description: {port['description']}")
        print(f"   Hardware ID: {port['hwid']}")

        if "vid" in port and "pid" in port:
            vid_val = port["vid"]
            pid_val = port["pid"]
            vid_str = f"{vid_val:04x}" if vid_val is not None else "None"
            pid_str = f"{pid_val:04x}" if pid_val is not None else "None"
            print(f"   VID:PID: {vid_str}:{pid_str}")

        if "serial_number" in port:
            print(f"   Serial: {port['serial_number']}")
        print()
    return ports


def demo_auto_discover():
    """Demo 2: Automatically discover Arduino."""
    print("\n" + "=" * 60)
    print("Demo 2: Auto-Discover Arduino")
    print("=" * 60)

    # Try to find Arduino (common VID for Arduino boards)
    driver = SerialDriver.auto_discover(vid=0x2341, baudrate=9600)  # Arduino VID

    if driver:
        print(f"\n[OK] Arduino found on {driver.port}")
        return driver.port

    # Try finding any Arduino by description
    driver = SerialDriver.auto_discover(description_pattern="Arduino", baudrate=9600)

    if driver:
        print(f"\n[OK] Arduino-like device found on {driver.port}")
        return driver.port

    print("\n[FAIL] No Arduino found")
    print("   Connect an Arduino and try again")
    return None


async def demo_manual_connection(port: str):
    """Demo 3: Manual connection and communication."""
    print("\n" + "=" * 60)
    print(f"Demo 3: Manual Connection to {port}")
    print("=" * 60)

    # Create driver with async context manager
    try:
        async with SerialDriver(port=port, baudrate=9600) as driver:
            print(f"\n[OK] Connected to {port}")

            # Send some test commands
            print("\n[SEND] Sending test commands...")

            # Example 1: Send bytes
            await driver.send_bytes(b"\xff\x00\x64")
            print("   Sent: 0xFF 0x00 0x64")
            await asyncio.sleep(0.1)

            # Example 2: Send ASCII command (raw text)
            await driver.send_text("LED:ON\n")
            print("   Sent: LED:ON")
            await asyncio.sleep(0.5)

            # Example 3: Send effect command (raw text)
            await driver.send_text("EFFECT:LIGHT:255:1000\n")
            print("   Sent: EFFECT:LIGHT:255:1000")
            await asyncio.sleep(1.0)

            # Try to read response (if device sends any)
            print("\n[RECV] Checking for response...")
            response = await asyncio.to_thread(driver.read_line)
            if response:
                print(f"   Device response: {response}")
            else:
                print("   No response (timeout)")

            print(f"\n[OK] Connection test complete")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        logger.error(f"Connection failed: {e}")


async def demo_callback_mode(port: str):
    """Demo 4: Asynchronous reading with callbacks."""
    print("\n" + "=" * 60)
    print(f"Demo 4: Callback Mode (Async Reading)")
    print("=" * 60)

    def on_data(data: bytes):
        """Callback for incoming data."""
        print(f"[RECV] Received: {data.hex()} ({data})")

    try:
        driver = SerialDriver(port=port, baudrate=9600, on_data_received=on_data)

        if await asyncio.to_thread(driver.open_connection):
            print(f"\n[OK] Connected with callback mode")
            print("   Listening for incoming data...")

            # Send commands and wait for responses
            for i in range(3):
                await driver.send_text(f"PING:{i}\n")
                print(f"   Sent: PING:{i}")
                await asyncio.sleep(1)

            print("\n[OK] Callback test complete")
            await asyncio.to_thread(driver.close_connection)

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")


async def demo_arduino_effect_control(port: str):
    """Demo 5: Send sensory effects to Arduino."""
    print("\n" + "=" * 60)
    print(f"Demo 5: Arduino Effect Control")
    print("=" * 60)

    effects = [
        ("LIGHT", 255, 1000),
        ("LIGHT", 128, 500),
        ("VIBRATION", 200, 800),
        ("FAN", 150, 2000),
    ]

    try:
        async with SerialDriver(port=port, baudrate=115200) as driver:
            print(f"\n[OK] Connected to Arduino at 115200 baud")

            for effect_type, intensity, duration in effects:
                # Format: EFFECT:<type>:<intensity>:<duration>\n
                command = f"EFFECT:{effect_type}:{intensity}:{duration}\n"

                print(f"\n[SENDING] Sending: {effect_type}")
                print(f"   Intensity: {intensity}")
                print(f"   Duration: {duration}ms")

                await driver.send_text(command)
                await asyncio.sleep(duration / 1000.0 + 0.5)

            print("\n[OK] All effects sent successfully")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")


async def interactive_mode():
    """Interactive mode for testing."""
    print("\n" + "=" * 60)
    print("Interactive Mode")
    print("=" * 60)

    ports = SerialDriver.list_ports()
    if not ports:
        print("\n[FAIL] No serial ports available")
        return

    # Select port
    print("\nAvailable ports:")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port['device']} - {port['description']}")

    try:
        choice = int(input("\nSelect port (number): "))
        port = ports[choice - 1]["device"]
    except (ValueError, IndexError):
        print("Invalid choice")
        return

    # Select baudrate
    print("\nCommon baud rates:")
    baudrates = [9600, 19200, 38400, 57600, 115200]
    for i, baud in enumerate(baudrates, 1):
        print(f"{i}. {baud}")

    try:
        choice = int(input("\nSelect baud rate (number): "))
        baudrate = baudrates[choice - 1]
    except (ValueError, IndexError):
        baudrate = 9600

    # Connect
    try:
        driver = SerialDriver(port=port, baudrate=baudrate)
        if not await asyncio.to_thread(driver.open_connection):
            print(f"[FAIL] Failed to connect to {port}")
            return

        print(f"\n[OK] Connected to {port} @ {baudrate}")
        print("\nCommands:")
        print("  'send <text>' - Send text")
        print("  'hex <bytes>'  - Send hex bytes (e.g., 'hex FF 00 64')")
        print("  'read'        - Read one line")
        print("  'quit'        - Exit")
        print()

        while True:
            cmd = await asyncio.to_thread(input, "> ")
            cmd = cmd.strip()

            if cmd == "quit":
                break

            elif cmd.startswith("send "):
                text = cmd[5:] + "\n"
                await driver.send_text(text)
                print(f"Sent: {text.strip()}")

            elif cmd.startswith("hex "):
                hex_str = cmd[4:].replace(" ", "")
                try:
                    data = bytes.fromhex(hex_str)
                    await driver.send_bytes(data)
                    print(f"Sent: {data.hex()}")
                except ValueError:
                    print("Invalid hex format")

            elif cmd == "read":
                line = await asyncio.to_thread(driver.read_line)
                if line:
                    print(f"Received: {line}")
                else:
                    print("No data (timeout)")

            else:
                print("Unknown command")

        await asyncio.to_thread(driver.close_connection)
        print("\n[OK] Disconnected")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Serial Driver Demo - PythonPlaySEM")
    print("=" * 60)

    # Demo 1: List ports
    demo_list_ports()

    # Demo 2: Auto-discover Arduino
    port = demo_auto_discover()

    if not port:
        # No Arduino found, try to use first available port
        ports = SerialDriver.list_ports()
        if ports:
            port = ports[0]["device"]
            print(f"\n[INFO] Using first available port: {port}")
        else:
            print("\n[FAIL] No serial ports available for demos")
            print("   Connect a USB device and try again")
            return

    # Demo 3: Manual connection
    await demo_manual_connection(port)

    # Demo 4: Callback mode
    # await demo_callback_mode(port)  # Uncomment if device sends data

    # Demo 5: Arduino effect control
    # await demo_arduino_effect_control(port)  # Uncomment if using Arduino sketch

    # Interactive mode
    print("\n" + "=" * 60)
    if sys.stdin.isatty():
        choice = input("\nEnter interactive mode? (y/n): ").strip().lower()
        if choice == "y":
            await interactive_mode()
    else:
        print("\nSkipping interactive mode (non-terminal)")

    print("\n" + "=" * 60)
    print("[OK] Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[INFO] Demo interrupted")
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
