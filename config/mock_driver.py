import time
import logging

logger = logging.getLogger(__name__)


class MockConnectivity:
    """
    Mock interface for testing connectivity without physical hardware.
    Referenced in devices.yaml as 'device_driver.mock_driver.MockConnectivity'
    """

    def __init__(self, interface_id, properties=None):
        self.interface_id = interface_id
        self.properties = properties or {}
        self.connected = False
        logger.info(f"MockConnectivity initialized: {interface_id}")

    def connect(self):
        self.connected = True
        logger.info(f"MockConnectivity {self.interface_id} connected.")
        return True

    def disconnect(self):
        self.connected = False
        logger.info(f"MockConnectivity {self.interface_id} disconnected.")

    def send(self, data):
        if not self.connected:
            logger.warning(
                f"MockConnectivity {self.interface_id} not connected. Dropping data: {data}"
            )
            return
        logger.info(f"MockConnectivity {self.interface_id} sent: {data}")


class MockDevice:
    """Base class for Mock Devices handling common properties like delay."""

    def __init__(self, device_id, interface, properties=None):
        self.device_id = device_id
        self.interface = interface
        self.properties = properties or {}
        self.delay = self.properties.get("delay", 0)
        logger.info(
            f"Device {device_id} initialized with delay {self.delay}ms"
        )

    def _simulate_delay(self):
        if self.delay > 0:
            time.sleep(self.delay / 1000.0)


class MockLightDevice(MockDevice):
    """
    Mock implementation of a Light Device.
    Handles commands: set_brightness, set_color
    """

    def set_brightness(self, intensity):
        self._simulate_delay()
        logger.info(f"LIGHT {self.device_id}: Set brightness to {intensity}")
        # In a real driver, self.interface.send(command) would go here

    def set_color(self, r, g, b):
        self._simulate_delay()
        logger.info(f"LIGHT {self.device_id}: Set color to R:{r} G:{g} B:{b}")


class MockWindDevice(MockDevice):
    """
    Mock implementation of a Wind/Fan Device.
    Handles commands: set_speed
    """

    def set_speed(self, intensity):
        self._simulate_delay()
        logger.info(f"WIND {self.device_id}: Set speed to {intensity}")


class MockVibrationDevice(MockDevice):
    """
    Mock implementation of a Vibration Device.
    Handles commands: set_intensity
    """

    def set_intensity(self, intensity, duration=None):
        self._simulate_delay()
        msg = f"VIBRATION {self.device_id}: Intensity {intensity}"
        if duration:
            msg += f", Duration {duration}ms"
        logger.info(msg)


class MockScentDevice(MockDevice):
    """
    Mock implementation of a Scent Device.
    Handles commands: set_scent
    """

    def set_scent(self, scent, intensity):
        self._simulate_delay()
        logger.info(
            f"SCENT {self.device_id}: Emitting {scent} at intensity {intensity}"
        )
