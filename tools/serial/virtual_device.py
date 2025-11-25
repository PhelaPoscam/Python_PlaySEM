#!/usr/bin/env python3
"""
Virtual Serial Device Simulator.

Simulates an Arduino or other serial device for testing without hardware.
Creates a pair of connected virtual serial ports - one acts as the "device"
and the other can be used by the SerialDriver.

This allows you to test serial communication without physical hardware.

Prerequisites:
    Windows: pip install pyserial com0com (or use built-in loop mode)
    Linux/Mac: Uses PTY (pseudo-terminal) - no extra dependencies

Usage:
    # Run the simulator
    python examples/demos/virtual_serial_device.py

    # In another terminal/script, connect to the displayed port
    # Example: SerialDriver(port="COM4")  # or /dev/pts/X on Linux
"""

import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional
import platform

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import serial
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("❌ pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class VirtualSerialDevice:
    """
    Virtual serial device that responds to commands.

    Simulates an Arduino-like device with support for:
    - Light effects (LED control)
    - Vibration effects (motor control)
    - Wind effects (fan control)
    - Status queries
    """

    def __init__(self, port: str, baudrate: int = 9600):
        """
        Initialize virtual device.

        Args:
            port: Serial port to listen on
            baudrate: Communication speed
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.running = False
        self.read_thread: Optional[threading.Thread] = None

        # Device state
        self.light_intensity = 0
        self.light_color = "#FFFFFF"
        self.vibration_intensity = 0
        self.wind_speed = 0

    def start(self):
        """Start the virtual device."""
        try:
            self.serial = serial.Serial(
                port=self.port, baudrate=self.baudrate, timeout=0.1
            )

            logger.info(f"✅ Virtual device started on {self.port}")
            logger.info(f"   Baudrate: {self.baudrate}")
            logger.info(f"   Ready to receive commands!")

            self.running = True
            self.read_thread = threading.Thread(
                target=self._read_loop, daemon=True
            )
            self.read_thread.start()

            return True

        except serial.SerialException as e:
            logger.error(f"❌ Failed to start virtual device: {e}")
            logger.error(f"   Port {self.port} may not exist or is in use")
            return False

    def stop(self):
        """Stop the virtual device."""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2.0)
        if self.serial:
            self.serial.close()
        logger.info("Virtual device stopped")

    def _read_loop(self):
        """Main loop for reading commands."""
        logger.info("Listening for commands...")

        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    # Read incoming data
                    data = self.serial.readline()
                    if data:
                        self._process_command(data)
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    logger.error(f"Error in read loop: {e}")
                    time.sleep(0.1)

    def _process_command(self, data: bytes):
        """Process incoming command from serial port."""
        try:
            # Try to decode as text
            command = data.decode("utf-8", errors="ignore").strip()
            logger.info(f"📨 Received: {command}")

            # Parse command
            response = self._handle_command(command)

            # Send response
            if response:
                self._send_response(response)

        except Exception as e:
            logger.error(f"Error processing command: {e}")

    def _handle_command(self, command: str) -> Optional[str]:
        """
        Handle specific command and return response.

        Supported commands:
        - PING -> PONG
        - STATUS -> Current device state
        - LIGHT:<intensity>:<duration>:[color] -> Set light
        - VIBRATE:<intensity>:<duration> -> Set vibration
        - WIND:<speed>:<duration> -> Set wind
        - LED:ON / LED:OFF -> Simple LED control
        """
        cmd_upper = command.upper()

        # PING command
        if cmd_upper == "PING":
            return "PONG"

        # STATUS query
        if cmd_upper == "STATUS":
            status = {
                "light": self.light_intensity,
                "color": self.light_color,
                "vibration": self.vibration_intensity,
                "wind": self.wind_speed,
            }
            return f"STATUS:{status}"

        # Simple LED control
        if cmd_upper.startswith("LED:"):
            state = cmd_upper.split(":", 1)[1]
            if state == "ON":
                self.light_intensity = 255
                logger.info("💡 LED turned ON")
                return "LED:OK"
            elif state == "OFF":
                self.light_intensity = 0
                logger.info("💡 LED turned OFF")
                return "LED:OK"

        # LIGHT effect
        if cmd_upper.startswith("LIGHT:"):
            parts = command.split(":")
            if len(parts) >= 3:
                try:
                    intensity = int(parts[1])
                    duration = int(parts[2])
                    color = parts[3] if len(parts) > 3 else "#FFFFFF"

                    self.light_intensity = intensity
                    self.light_color = color

                    logger.info(
                        f"💡 LIGHT: intensity={intensity}, "
                        f"duration={duration}ms, color={color}"
                    )

                    # Simulate effect duration
                    threading.Thread(
                        target=self._fade_light,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()

                    return f"LIGHT:OK:{intensity}:{duration}"
                except ValueError as e:
                    return f"ERROR:Invalid light parameters"

        # VIBRATION effect
        if cmd_upper.startswith("VIBRATE:") or cmd_upper.startswith(
            "VIBRATION:"
        ):
            parts = command.split(":")
            if len(parts) >= 3:
                try:
                    intensity = int(parts[1])
                    duration = int(parts[2])

                    self.vibration_intensity = intensity

                    logger.info(
                        f"📳 VIBRATION: intensity={intensity}, "
                        f"duration={duration}ms"
                    )

                    # Simulate effect duration
                    threading.Thread(
                        target=self._stop_vibration,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()

                    return f"VIBRATE:OK:{intensity}:{duration}"
                except ValueError:
                    return "ERROR:Invalid vibration parameters"

        # WIND effect
        if cmd_upper.startswith("WIND:"):
            parts = command.split(":")
            if len(parts) >= 3:
                try:
                    speed = int(parts[1])
                    duration = int(parts[2])

                    self.wind_speed = speed

                    logger.info(
                        f"💨 WIND: speed={speed}, duration={duration}ms"
                    )

                    # Simulate effect duration
                    threading.Thread(
                        target=self._stop_wind,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()

                    return f"WIND:OK:{speed}:{duration}"
                except ValueError:
                    return "ERROR:Invalid wind parameters"

        # JSON-style command (from EffectMetadata)
        if command.startswith("{"):
            try:
                import json

                effect = json.loads(command)
                effect_type = effect.get("effect_type", "unknown")
                intensity = effect.get("intensity", 0)
                duration = effect.get("duration", 1000)

                logger.info(
                    f"📦 JSON Effect: type={effect_type}, "
                    f"intensity={intensity}, duration={duration}ms"
                )

                if effect_type == "light":
                    self.light_intensity = intensity
                    threading.Thread(
                        target=self._fade_light,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()
                elif effect_type == "vibration":
                    self.vibration_intensity = intensity
                    threading.Thread(
                        target=self._stop_vibration,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()
                elif effect_type == "wind":
                    self.wind_speed = intensity
                    threading.Thread(
                        target=self._stop_wind,
                        args=(duration / 1000,),
                        daemon=True,
                    ).start()

                return f"JSON:OK"
            except json.JSONDecodeError:
                pass

        # Unknown command
        logger.warning(f"⚠️  Unknown command: {command}")
        return f"ERROR:Unknown command"

    def _send_response(self, response: str):
        """Send response back to host."""
        try:
            if self.serial:
                self.serial.write((response + "\n").encode("utf-8"))
                logger.debug(f"📤 Sent: {response}")
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    def _fade_light(self, duration: float):
        """Simulate light fading out after duration."""
        time.sleep(duration)
        self.light_intensity = 0
        logger.debug("💡 Light faded out")

    def _stop_vibration(self, duration: float):
        """Stop vibration after duration."""
        time.sleep(duration)
        self.vibration_intensity = 0
        logger.debug("📳 Vibration stopped")

    def _stop_wind(self, duration: float):
        """Stop wind after duration."""
        time.sleep(duration)
        self.wind_speed = 0
        logger.debug("💨 Wind stopped")


def find_virtual_port_pair():
    """
    Try to find a virtual serial port pair.

    Returns tuple of (device_port, host_port) or (None, None)
    """
    # On Windows, look for com0com or similar virtual ports
    if platform.system() == "Windows":
        ports = serial.tools.list_ports.comports()

        # Look for common virtual port patterns
        virtual_patterns = ["com0com", "virtual", "null-modem", "loop"]

        for port in ports:
            desc_lower = port.description.lower()
            for pattern in virtual_patterns:
                if pattern in desc_lower:
                    logger.info(f"Found potential virtual port: {port.device}")
                    return port.device, None  # Single port for loopback

        logger.warning("No virtual serial ports found")
        logger.info("💡 Install com0com: https://com0com.sourceforge.net/")
        logger.info("💡 Or use physical loopback: Connect TX to RX")

    return None, None


def create_pty_pair():
    """
    Create a pseudo-terminal pair on Unix-like systems.

    Returns tuple of (master, slave) file descriptors
    """
    if platform.system() in ["Linux", "Darwin"]:  # Darwin = macOS
        import pty
        import os

        master, slave = pty.openpty()
        master_name = os.ttyname(master)
        slave_name = os.ttyname(slave)

        logger.info(f"Created PTY pair:")
        logger.info(f"  Master: {master_name}")
        logger.info(f"  Slave: {slave_name}")
        logger.info(f"  Use slave port for SerialDriver")

        return master, slave, slave_name

    return None, None, None


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🔌 Virtual Serial Device Simulator")
    print("=" * 60)

    # Detect platform
    system = platform.system()
    logger.info(f"Platform: {system}")

    device_port = None

    # Try to find or create virtual ports
    if system == "Windows":
        print("\n📍 Windows detected")
        print("\n⚠️  IMPORTANT: For testing without hardware:")
        print("   You need a virtual COM port pair (like com0com)")
        print("   Or you can use this with the MockDriver instead")
        print("\nOptions:")
        print("1. Install com0com (recommended)")
        print("   Download: https://com0com.sourceforge.net/")
        print("   Creates paired ports like COM3<->COM4")
        print("2. Use physical loopback (connect TX to RX)")
        print("3. Try any available port (may not work)")

        # List available ports
        ports = serial.tools.list_ports.comports()
        if ports:
            print(f"\nAvailable serial ports ({len(ports)}):")
            for i, port in enumerate(ports, 1):
                print(f"{i}. {port.device} - {port.description}")

            print(f"\n{len(ports) + 1}. Enter custom COM port")

            choice = input(
                "\nSelect option (1-{}) or press Enter to skip: ".format(
                    len(ports) + 1
                )
            ).strip()

            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(ports):
                    device_port = ports[choice_num - 1].device
                elif choice_num == len(ports) + 1:
                    device_port = (
                        input("Enter COM port (e.g., COM4): ").strip().upper()
                    )
                    if not device_port.startswith("COM"):
                        device_port = "COM" + device_port
        else:
            print("\n⚠️  No serial ports detected")
            device_port = (
                input("Enter COM port manually (e.g., COM4): ").strip().upper()
            )
            if not device_port.startswith("COM"):
                device_port = "COM" + device_port

    elif system in ["Linux", "Darwin"]:
        print(f"\n📍 {system} detected - using PTY (pseudo-terminal)")
        try:
            master, slave, slave_name = create_pty_pair()
            if slave_name:
                device_port = slave_name
                print(f"\n✅ Virtual port created: {slave_name}")
                print(f"   Connect your SerialDriver to: {slave_name}")
        except Exception as e:
            logger.error(f"Failed to create PTY: {e}")

    else:
        print(f"\n⚠️  Unknown platform: {system}")

    if not device_port:
        print("\n❌ No virtual port available")
        print("\nAlternatives:")
        print("1. Use MockDriver for testing without serial")
        print("2. Get USB-to-serial adapter with loopback")
        return

    # Create and start virtual device
    print(f"\n🚀 Starting virtual device on {device_port}")
    print(f"   Baudrate: 9600")
    print(f"   Commands: PING, STATUS, LIGHT:intensity:duration")
    print(f"             VIBRATE:intensity:duration, WIND:speed:duration")
    print(f"   Press Ctrl+C to stop\n")

    device = VirtualSerialDevice(port=device_port, baudrate=9600)

    if not device.start():
        print("\n❌ Failed to start virtual device")
        print(f"   Make sure {device_port} exists and is not in use")
        return

    print("\n" + "=" * 60)
    print("Virtual device is running!")
    print("=" * 60)
    print(f"\nConnect from another terminal/script:")
    print(f"  from src.device_driver import SerialDriver")
    print(f"  driver = SerialDriver(port='{device_port}', baudrate=9600)")
    print(f"  driver.open_connection()")
    print(f"  driver.send_command('PING')")
    print("\n" + "=" * 60)

    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping virtual device...")
        device.stop()
        print("✅ Stopped")


if __name__ == "__main__":
    main()
