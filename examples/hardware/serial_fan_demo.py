#!/usr/bin/env python3
"""
Serial Fan Demo — drive a physical Arduino fan/motor from PlaySEM.

Connects to an Arduino running fan_controller.ino over USB Serial and sends
speed commands that map to PWM output on the Arduino's Pin 9.

Usage:
    python examples/hardware/serial_fan_demo.py

    # Or specify the port directly:
    python examples/hardware/serial_fan_demo.py --port COM4

    # List available serial ports:
    python examples/hardware/serial_fan_demo.py --list

Requirements:
    pip install pyserial
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def list_ports() -> list[str]:
    """Return available serial port names, or empty list if pyserial is missing."""
    try:
        import serial.tools.list_ports

        return [p.device for p in serial.tools.list_ports.comports()]
    except ImportError:
        return []


async def demo_ramp(driver, device_id: str = "wind_device") -> None:
    """Ramp fan speed up and down to demonstrate control."""

    print("\n  Ramping fan speed 0 → 100 → 0 ...\n")

    # Ramp up
    for speed in range(0, 101, 10):
        print(f"  speed={speed:3d}%", end="\r")
        await driver.send_command(
            device_id, "set_speed", {"speed": speed, "direction": "forward"}
        )
        await asyncio.sleep(0.15)

    await asyncio.sleep(0.5)

    # Ramp down
    for speed in range(100, -1, -10):
        print(f"  speed={speed:3d}%", end="\r")
        await driver.send_command(
            device_id, "set_speed", {"speed": speed, "direction": "forward"}
        )
        await asyncio.sleep(0.15)

    print("  Done.              ")


async def demo_burst(driver, device_id: str = "wind_device") -> None:
    """Quick burst pattern — simulates a wind gust."""

    print("\n  Gust pattern ...\n")

    gusts = [30, 70, 40, 90, 50, 100, 20, 0]
    for speed in gusts:
        print(f"  speed={speed:3d}%", end="\r")
        await driver.send_command(device_id, "set_speed", {"speed": speed})
        await asyncio.sleep(0.3)

    print("  Done.              ")


async def interactive(driver, device_id: str = "wind_device") -> None:
    """Simple interactive prompt."""

    print("\n  Type a speed 0-100, 'ramp', 'burst', or 'quit'.\n")

    while True:
        try:
            raw = input("  fan> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        if raw.lower() in ("quit", "exit", "q"):
            break
        elif raw.lower() == "ramp":
            await demo_ramp(driver, device_id)
        elif raw.lower() == "burst":
            await demo_burst(driver, device_id)
        else:
            try:
                speed = int(raw)
                await driver.send_command(device_id, "set_speed", {"speed": speed})
                print(f"  -> speed={speed}%")
            except ValueError:
                print("  Enter a number 0-100, 'ramp', 'burst', or 'quit'")


async def main() -> None:
    parser = argparse.ArgumentParser(description="PlaySEM Serial Fan Demo")
    parser.add_argument(
        "--port",
        "-p",
        help="Serial port (e.g. COM3, /dev/ttyUSB0). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--baudrate",
        "-b",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available serial ports and exit",
    )
    parser.add_argument(
        "--device-id",
        "-d",
        default="wind_device",
        help="Device ID to use (default: wind_device)",
    )
    parser.add_argument(
        "--demo",
        choices=["ramp", "burst", "interactive"],
        default="interactive",
        help="Demo mode (default: interactive)",
    )
    args = parser.parse_args()

    if args.list:
        ports = list_ports()
        if ports:
            print("Available serial ports:")
            for p in ports:
                print(f"  {p}")
        else:
            print("No serial ports found (pyserial may not be installed).")
        return

    # Resolve port
    port = args.port
    if port is None:
        ports = list_ports()
        if not ports:
            print(
                "No serial ports detected. Install pyserial and connect a device,\n"
                "or specify one with --port."
            )
            return
        port = ports[0]
        print(f"Auto-detected port: {port}")

    print(f"\n  PlaySEM Serial Fan Demo")
    print(f"  Port:   {port}")
    print(f"  Baud:   {args.baudrate}")
    print(f"  Device: {args.device_id}")

    # Import SerialDriver here — pyserial is optional
    try:
        from playsem.drivers.serial_driver import SerialDriver
    except ImportError:
        print("\n  pyserial is required. Install it with: pip install pyserial")
        return

    driver = SerialDriver(
        port=port,
        baudrate=args.baudrate,
        data_format="json",
    )

    print(f"\n  Connecting to {port} ...")
    connected = await driver.connect()

    if not connected:
        print(f"  Failed to connect to {port}.")
        print(f"  Is the Arduino plugged in and running fan_controller.ino?")
        return

    print(f"  Connected! Waiting for Arduino to boot ...")
    await asyncio.sleep(2.0)

    try:
        # Send a quick off to sync state
        await driver.send_command(args.device_id, "off", {})

        if args.demo == "ramp":
            await demo_ramp(driver, args.device_id)
        elif args.demo == "burst":
            await demo_burst(driver, args.device_id)
        else:
            await interactive(driver, args.device_id)

    finally:
        print("\n  Disconnecting ...")
        await driver.send_command(args.device_id, "off", {})
        await asyncio.sleep(0.1)
        await driver.disconnect()
        print("  Done.\n")


if __name__ == "__main__":
    asyncio.run(main())
