#!/usr/bin/env python3
"""
Serial Driver for USB/Arduino devices.

Provides connectivity to sensory devices via serial/USB ports using pyserial.
Supports automatic port discovery, connection management, and byte-level
communication with hardware devices.

Example:
    >>> driver = SerialDriver(port="COM3", baudrate=9600)
    >>> driver.open_connection()
    >>> driver.send_bytes(b"\\x01\\xFF\\x00")  # Send command
    >>> driver.close_connection()
"""

import logging
import time
import json
from typing import Optional, List, Callable, Dict, Any
import threading

try:
    import serial
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None

from .base_driver import BaseDriver

logger = logging.getLogger(__name__)


class SerialDriver(BaseDriver):
    """
    Serial port driver for USB and Arduino devices.

    Manages serial communication with connected hardware devices,
    including automatic port discovery, connection lifecycle,
    and data transmission.

    Attributes:
        port: Serial port name (e.g., "COM3", "/dev/ttyUSB0")
        baudrate: Communication speed in bits per second
        timeout: Read timeout in seconds
        is_connected: Connection status

    Example:
        >>> # Manual port specification
        >>> driver = SerialDriver(port="COM3", baudrate=9600)
        >>> driver.open_connection()
        >>> driver.send_bytes(b"\\xFF\\x00\\x01")
        >>> driver.close_connection()

        >>> # Auto-discovery
        >>> driver = SerialDriver.auto_discover(vid=0x2341, pid=0x0043)
        >>> if driver:
        ...     driver.open_connection()
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        on_data_received: Optional[Callable[[bytes], None]] = None,
    ):
        """
        Initialize serial driver.

        Args:
            port: Serial port name (e.g., "COM3" on Windows,
                "/dev/ttyUSB0" on Linux)
            baudrate: Baud rate (default: 9600). Common values:
                9600, 19200, 38400, 57600, 115200
            timeout: Read timeout in seconds (default: 1.0)
            bytesize: Number of data bits (default: 8)
            parity: Parity checking ('N'=None, 'E'=Even, 'O'=Odd)
            stopbits: Number of stop bits (default: 1)
            on_data_received: Optional callback for incoming data

        Raises:
            ImportError: If pyserial is not installed
        """
        if not SERIAL_AVAILABLE:
            raise ImportError(
                "pyserial not installed. Run: pip install pyserial"
            )

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.on_data_received = on_data_received

        self._serial: Optional[serial.Serial] = None
        self._is_connected = False
        self._read_thread: Optional[threading.Thread] = None
        self._stop_reading = threading.Event()

        logger.info(
            f"SerialDriver initialized - port: {port}, "
            f"baudrate: {baudrate}"
        )

    @classmethod
    def list_ports(cls) -> List[dict]:
        """
        List all available serial ports on the system.

        Returns:
            List of dictionaries containing port information:
                - device: Port name (e.g., "COM3")
                - description: Human-readable description
                - hwid: Hardware ID
                - vid: Vendor ID (if available)
                - pid: Product ID (if available)
                - serial_number: Device serial number (if available)

        Example:
            >>> ports = SerialDriver.list_ports()
            >>> for port in ports:
            ...     print(f"{port['device']}: {port['description']}")
            COM3: Arduino Uno (COM3)
            COM4: USB Serial Port (COM4)
        """
        if not SERIAL_AVAILABLE:
            logger.warning("pyserial not available")
            return []

        ports = []
        for port in serial.tools.list_ports.comports():
            port_info = {
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
            }

            # Add USB vendor/product IDs if available
            if hasattr(port, "vid") and port.vid:
                port_info["vid"] = port.vid
            if hasattr(port, "pid") and port.pid:
                port_info["pid"] = port.pid
            if hasattr(port, "serial_number") and port.serial_number:
                port_info["serial_number"] = port.serial_number

            ports.append(port_info)

        logger.info(f"Found {len(ports)} serial ports")
        return ports

    @classmethod
    def auto_discover(
        cls,
        vid: Optional[int] = None,
        pid: Optional[int] = None,
        serial_number: Optional[str] = None,
        description_pattern: Optional[str] = None,
        **kwargs,
    ) -> Optional["SerialDriver"]:
        """
        Automatically discover and create driver for matching device.

        Args:
            vid: USB Vendor ID to match (e.g., 0x2341 for Arduino)
            pid: USB Product ID to match
            serial_number: Device serial number to match
            description_pattern: Pattern to match in description
            **kwargs: Additional arguments passed to SerialDriver()

        Returns:
            SerialDriver instance if device found, None otherwise

        Example:
            >>> # Find Arduino Uno
            >>> driver = SerialDriver.auto_discover(vid=0x2341, pid=0x0043)
            >>>
            >>> # Find any Arduino
            >>> driver = SerialDriver.auto_discover(
            ...     description_pattern="Arduino"
            ... )
        """
        if not SERIAL_AVAILABLE:
            logger.error("pyserial not available for auto-discovery")
            return None

        for port in serial.tools.list_ports.comports():
            # Check vendor/product ID
            if vid is not None and hasattr(port, "vid"):
                if port.vid != vid:
                    continue
            if pid is not None and hasattr(port, "pid"):
                if port.pid != pid:
                    continue

            # Check serial number
            if serial_number is not None:
                if (
                    not hasattr(port, "serial_number")
                    or port.serial_number != serial_number
                ):
                    continue

            # Check description pattern
            if description_pattern is not None:
                if description_pattern.lower() not in port.description.lower():
                    continue

            # Found matching device
            logger.info(
                f"Auto-discovered device: {port.device} "
                f"({port.description})"
            )
            return cls(port=port.device, **kwargs)

        logger.warning("No matching device found for auto-discovery")
        return None

    def open_connection(self) -> bool:
        """
        Open serial port connection.

        Returns:
            True if connection successful, False otherwise

        Raises:
            serial.SerialException: If port cannot be opened

        Example:
            >>> driver = SerialDriver(port="COM3")
            >>> if driver.open_connection():
            ...     print("Connected!")
            ...     driver.send_bytes(b"\\x01")
        """
        if self._is_connected:
            logger.warning(f"Already connected to {self.port}")
            return True

        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
            )

            # Wait for connection to stabilize
            time.sleep(0.1)

            # Flush buffers
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            self._is_connected = True

            # Start read thread if callback provided
            if self.on_data_received:
                self._start_read_thread()

            logger.info(
                f"Serial connection opened: {self.port} @ {self.baudrate}"
            )
            return True

        except serial.SerialException as e:
            logger.error(f"Failed to open {self.port}: {e}")
            self._is_connected = False
            return False

    def close_connection(self):
        """
        Close serial port connection.

        Stops read thread if running and closes the port.

        Example:
            >>> driver.close_connection()
            >>> print(f"Connected: {driver.is_connected}")
            Connected: False
        """
        if not self._is_connected:
            return

        # Stop read thread
        if self._read_thread:
            self._stop_reading.set()
            self._read_thread.join(timeout=2.0)
            self._read_thread = None

        # Close serial port
        if self._serial:
            try:
                self._serial.close()
                logger.info(f"Serial connection closed: {self.port}")
            except Exception as e:
                logger.error(f"Error closing {self.port}: {e}")
            finally:
                self._serial = None

        self._is_connected = False

    def send_bytes(self, data: bytes) -> bool:
        """
        Send raw bytes to device.

        Args:
            data: Bytes to send

        Returns:
            True if send successful, False otherwise

        Example:
            >>> # Send 3-byte command
            >>> driver.send_bytes(b"\\xFF\\x00\\x64")
            True
            >>>
            >>> # Send ASCII command
            >>> driver.send_bytes(b"LED:ON\\n")
            True
        """
        if not self._is_connected or not self._serial:
            logger.error("Cannot send: not connected")
            return False

        try:
            bytes_written = self._serial.write(data)
            self._serial.flush()  # Ensure data is transmitted

            logger.debug(
                f"Sent {bytes_written} bytes to {self.port}: " f"{data.hex()}"
            )
            return bytes_written == len(data)

        except serial.SerialException as e:
            logger.error(f"Error sending to {self.port}: {e}")
            return False

    def send_text(self, command: str, encoding: str = "utf-8") -> bool:
        """
        Send text command to device.

        Args:
            command: Text command to send
            encoding: Text encoding (default: 'utf-8')

        Returns:
            True if send successful, False otherwise

        Example:
            >>> driver.send_text("LED:255")
            True
            >>> driver.send_text("MOTOR:100\\n")
            True
        """
        return self.send_bytes(command.encode(encoding))

    # BaseDriver interface implementation
    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send command to device (BaseDriver interface).

        Implements BaseDriver interface for DeviceManager compatibility.
        Commands are formatted as JSON with parameters or simple text.

        Args:
            device_id: Device identifier
            command: Command string
            params: Optional parameters dictionary

        Returns:
            bool: True if command sent successfully

        Example:
            >>> driver.send_command(
            ...     device_id="arduino_001",
            ...     command="SET_LED",
            ...     params={"intensity": 255}
            ... )
            True
        """
        if not self.is_connected():
            logger.warning("Cannot send command: not connected")
            return False

        try:
            # Build command message
            if params:
                # Send as JSON for structured data
                message = {
                    "command": command,
                    "params": params,
                    "device_id": device_id,
                }
                payload = json.dumps(message) + "\n"
            else:
                # Send as simple text command
                payload = f"{command}\n"

            # Send via serial
            return self.send_bytes(payload.encode("utf-8"))

        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def read_bytes(self, size: int = 1) -> Optional[bytes]:
        """
        Read bytes from device.

        Args:
            size: Number of bytes to read

        Returns:
            Bytes read, or None if error/timeout

        Example:
            >>> response = driver.read_bytes(4)
            >>> if response:
            ...     print(f"Response: {response.hex()}")
            Response: ff0064aa
        """
        if not self._is_connected or not self._serial:
            logger.error("Cannot read: not connected")
            return None

        try:
            data = self._serial.read(size)
            if data:
                logger.debug(f"Read {len(data)} bytes: {data.hex()}")
            return data if data else None

        except serial.SerialException as e:
            logger.error(f"Error reading from {self.port}: {e}")
            return None

    def read_line(self, encoding: str = "utf-8") -> Optional[str]:
        """
        Read one line from device (until newline).

        Args:
            encoding: Text encoding (default: 'utf-8')

        Returns:
            Line as string (without newline), or None if error/timeout

        Example:
            >>> line = driver.read_line()
            >>> if line:
            ...     print(f"Device says: {line}")
            Device says: READY
        """
        if not self._is_connected or not self._serial:
            return None

        try:
            data = self._serial.readline()
            if data:
                return data.decode(encoding).strip()
            return None

        except (serial.SerialException, UnicodeDecodeError) as e:
            logger.error(f"Error reading line from {self.port}: {e}")
            return None

    def _start_read_thread(self):
        """Start background thread for reading incoming data."""
        if self._read_thread:
            return

        self._stop_reading.clear()
        self._read_thread = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._read_thread.start()
        logger.debug("Read thread started")

    def _read_loop(self):
        """Background loop for reading data."""
        while not self._stop_reading.is_set():
            if not self._is_connected or not self._serial:
                break

            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if data and self.on_data_received:
                        self.on_data_received(data)
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                break

            time.sleep(0.01)  # Small delay to prevent CPU spinning

        logger.debug("Read thread stopped")

    def is_connected(self) -> bool:
        """Check if serial port is connected (BaseDriver interface)."""
        return self._is_connected and self._serial is not None

    def reset_device(self, dtr: bool = False, rts: bool = False):
        """
        Reset device using DTR/RTS signals.

        Some Arduino boards reset when DTR or RTS is toggled.

        Args:
            dtr: Toggle DTR (Data Terminal Ready)
            rts: Toggle RTS (Request To Send)

        Example:
            >>> driver.reset_device(dtr=True)  # Reset Arduino
            >>> time.sleep(2)  # Wait for bootloader
        """
        if not self._is_connected or not self._serial:
            logger.error("Cannot reset: not connected")
            return

        try:
            if dtr:
                self._serial.dtr = True
                time.sleep(0.1)
                self._serial.dtr = False
                logger.info("Device reset via DTR")

            if rts:
                self._serial.rts = True
                time.sleep(0.1)
                self._serial.rts = False
                logger.info("Device reset via RTS")

        except Exception as e:
            logger.error(f"Error resetting device: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_connection()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._is_connected else "disconnected"
        return (
            f"SerialDriver(port={self.port}, baudrate={self.baudrate}, "
            f"status={status})"
        )

    # BaseDriver additional methods
    def connect(self) -> bool:
        """Connect to serial device (BaseDriver interface)."""
        return self.open_connection()

    def disconnect(self) -> bool:
        """Disconnect from serial device (BaseDriver interface)."""
        try:
            self.close_connection()
            return True
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False

    def get_driver_info(self) -> Dict[str, Any]:
        """Get serial driver configuration (BaseDriver interface)."""
        return {
            "type": "serial",
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
            "connected": self.is_connected(),
        }

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device capabilities for serial-connected devices.

        Returns generic sensory effect capabilities. For device-specific
        capabilities, the device should respond to a capability query command.
        """
        from ..device_capabilities import (
            DeviceCapabilities,
            EffectCapability,
            EffectType,
            create_standard_intensity_param,
            create_standard_duration_param,
        )

        # Create generic capabilities for serial devices
        # In a real implementation, you might query the device
        caps = DeviceCapabilities(
            device_id=device_id,
            device_type="SerialDevice",
            manufacturer="Unknown",
            model=f"Serial@{self.port}",
            driver_type="serial",
            metadata={
                "port": self.port,
                "baudrate": self.baudrate,
            },
        )

        # Add common effect types that serial devices typically support
        # These are generic - real devices should provide specific capabilities
        for effect_type in [
            EffectType.LIGHT,
            EffectType.WIND,
            EffectType.VIBRATION,
        ]:
            effect = EffectCapability(
                effect_type=effect_type,
                description=f"Generic {effect_type.value} effect support",
                parameters=[
                    create_standard_intensity_param(),
                    create_standard_duration_param(),
                ],
            )
            caps.effects.append(effect)

        return caps.to_dict()
