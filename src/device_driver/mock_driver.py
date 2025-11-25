# src/device_driver/mock_driver.py
"""
Mock device drivers for testing without physical hardware.
These drivers log commands to console instead of sending to real devices.
"""

import logging
from typing import Dict, Any, Optional

from .base_driver import BaseDriver

logger = logging.getLogger(__name__)


class MockConnectivityDriver(BaseDriver):
    """Mock connectivity driver for testing without real hardware."""

    def __init__(self):
        self._connected = False
        logger.info("MockConnectivityDriver initialized")
        # Map device_id -> MockDeviceBase instance for forwarding commands
        self._devices = {}

    def connect(self) -> bool:
        logger.info("MockConnectivityDriver: connect()")
        self._connected = True
        return True

    def disconnect(self) -> bool:
        logger.info("MockConnectivityDriver: disconnect()")
        self._connected = False
        return True

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        logger.info(
            f"MockConnectivityDriver: send_command(" 
            f"device_id='{device_id}', command='{command}', params={params})"
        )
        # If we have a registered mock device for this id, forward the command
        if device_id in self._devices:
            try:
                mock_device = self._devices[device_id]
                # MockDeviceBase expects (command, params) without device_id
                mock_device.send_command(command, params or {})
                return True
            except Exception as e:
                logger.warning(f"Error forwarding to mock device {device_id}: {e}")
                return False
        # In a real mock driver, you might want to store the state
        # of mock devices here. For now, just logging is enough.
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_driver_type(self) -> str:
        return "mock"

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get mock device capabilities based on device_id pattern.

        Returns capabilities for light, wind, vibration, or scent devices
        based on the device_id prefix.
        """
        from ..device_capabilities import (
            DeviceCapabilities,
            EffectCapability,
            EffectType,
            ParameterCapability,
            ParameterType,
            create_standard_intensity_param,
            create_standard_duration_param,
        )

        # Determine device type from device_id
        device_id_lower = device_id.lower()

        if "light" in device_id_lower or "led" in device_id_lower:
            # Light device capabilities
            caps = DeviceCapabilities(
                device_id=device_id,
                device_type="MockLightDevice",
                manufacturer="PlaySEM",
                model="Mock Light v1.0",
                driver_type="mock",
            )

            light_effect = EffectCapability(
                effect_type=EffectType.LIGHT,
                description="RGB LED light control",
                parameters=[
                    ParameterCapability(
                        name="brightness",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        default=128,
                        unit="0-255",
                        description="Light brightness level",
                    ),
                    ParameterCapability(
                        name="r",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        default=255,
                        description="Red color component",
                    ),
                    ParameterCapability(
                        name="g",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        default=255,
                        description="Green color component",
                    ),
                    ParameterCapability(
                        name="b",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        default=255,
                        description="Blue color component",
                    ),
                    create_standard_intensity_param(
                        min_val=0, max_val=100, default=50
                    ),
                    create_standard_duration_param(),
                ],
                examples=[
                    {
                        "description": "Set white light at full brightness",
                        "command": {
                            "brightness": 255,
                            "r": 255,
                            "g": 255,
                            "b": 255,
                        },
                    },
                    {
                        "description": "Set red light at 50% intensity",
                        "command": {"r": 255, "g": 0, "b": 0, "intensity": 50},
                    },
                ],
            )
            caps.effects.append(light_effect)

        elif "wind" in device_id_lower or "fan" in device_id_lower:
            # Wind device capabilities
            caps = DeviceCapabilities(
                device_id=device_id,
                device_type="MockWindDevice",
                manufacturer="PlaySEM",
                model="Mock Fan v1.0",
                driver_type="mock",
            )

            wind_effect = EffectCapability(
                effect_type=EffectType.WIND,
                description="Fan/wind generation control",
                parameters=[
                    ParameterCapability(
                        name="speed",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=100,
                        default=50,
                        unit="percent",
                        description="Fan speed percentage",
                    ),
                    ParameterCapability(
                        name="direction",
                        type=ParameterType.ENUM,
                        enum_values=["forward", "reverse"],
                        default="forward",
                        description="Wind direction",
                    ),
                    create_standard_intensity_param(),
                    create_standard_duration_param(),
                ],
                examples=[
                    {
                        "description": "Set fan to 75% speed forward",
                        "command": {"speed": 75, "direction": "forward"},
                    }
                ],
            )
            caps.effects.append(wind_effect)

        elif "vibr" in device_id_lower or "haptic" in device_id_lower:
            # Vibration device capabilities
            caps = DeviceCapabilities(
                device_id=device_id,
                device_type="MockVibrationDevice",
                manufacturer="PlaySEM",
                model="Mock Vibration v1.0",
                driver_type="mock",
            )

            vibration_effect = EffectCapability(
                effect_type=EffectType.VIBRATION,
                description="Vibration/haptic feedback control",
                parameters=[
                    create_standard_intensity_param(),
                    create_standard_duration_param(default=500),
                    ParameterCapability(
                        name="pattern",
                        type=ParameterType.ENUM,
                        enum_values=[
                            "constant",
                            "pulse",
                            "wave",
                            "alert",
                        ],
                        default="constant",
                        description="Vibration pattern",
                    ),
                ],
                examples=[
                    {
                        "description": "Short alert vibration",
                        "command": {
                            "intensity": 80,
                            "duration": 200,
                            "pattern": "alert",
                        },
                    }
                ],
            )
            caps.effects.append(vibration_effect)

        elif "scent" in device_id_lower or "smell" in device_id_lower:
            # Scent device capabilities
            caps = DeviceCapabilities(
                device_id=device_id,
                device_type="MockScentDevice",
                manufacturer="PlaySEM",
                model="Mock Scent v1.0",
                driver_type="mock",
            )

            scent_effect = EffectCapability(
                effect_type=EffectType.SCENT,
                description="Scent/smell diffuser control",
                parameters=[
                    ParameterCapability(
                        name="scent",
                        type=ParameterType.ENUM,
                        enum_values=[
                            "rose",
                            "ocean",
                            "coffee",
                            "pine",
                            "vanilla",
                            "citrus",
                        ],
                        required=True,
                        description="Type of scent to diffuse",
                    ),
                    create_standard_intensity_param(),
                    create_standard_duration_param(default=3000),
                ],
                examples=[
                    {
                        "description": "Release ocean scent",
                        "command": {
                            "scent": "ocean",
                            "intensity": 60,
                            "duration": 5000,
                        },
                    }
                ],
            )
            caps.effects.append(scent_effect)

        else:
            # Generic/unknown device
            caps = DeviceCapabilities(
                device_id=device_id,
                device_type="MockDevice",
                manufacturer="PlaySEM",
                model="Mock Generic v1.0",
                driver_type="mock",
            )

        return caps.to_dict()

    def register_device(self, device_id: str, device_obj: "MockDeviceBase") -> None:
        """Register a MockDevice instance so that send_command can forward to it.

        This is used by test utilities and the example server to connect a
        logical device instance to the mock connectivity driver.
        """
        self._devices[device_id] = device_obj


class MockDeviceBase:
    """Base class for mock sensory effect devices."""

    def __init__(
        self, device_id: str, properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize mock device.

        Args:
            device_id: unique identifier for this device
            properties: device-specific configuration properties
        """
        self.device_id = device_id
        self.properties = properties or {}
        self.delay = int(self.properties.get("delay", 0))
        self.state = {}
        logger.info(
            f"Mock device '{device_id}' initialized " f"(delay={self.delay}ms)"
        )

    def send_command(self, command: str, params: Dict[str, Any]):
        """
        Simulate sending a command to the device.

        Args:
            command: command name (e.g., 'set_brightness', 'set_speed')
            params: command parameters
        """
        logger.info(
            f"[{self.device_id}] Command: {command}, " f"Params: {params}"
        )
        self.state.update(params)

    def reset(self):
        """Reset device to default state."""
        logger.info(f"[{self.device_id}] Reset to default state")
        self.state: Dict[str, Any] = {}

    def get_state(self) -> Dict[str, Any]:
        """Get current device state."""
        return self.state.copy()


class MockLightDevice(MockDeviceBase):
    """Mock light/LED device."""

    def __init__(
        self, device_id: str, properties: Optional[Dict[str, Any]] = None
    ):
        super().__init__(device_id, properties)
        self.state = {"r": 0, "g": 0, "b": 0, "brightness": 0}

    def set_brightness(self, brightness: int):
        """Set light brightness (0-255)."""
        self.state["brightness"] = max(0, min(255, brightness))
        logger.info(
            f"[{self.device_id}] Light brightness: "
            f"{self.state['brightness']}"
        )

    def set_color(self, r: int, g: int, b: int):
        """Set RGB color (0-255 each)."""
        self.state["r"] = max(0, min(255, r))
        self.state["g"] = max(0, min(255, g))
        self.state["b"] = max(0, min(255, b))
        logger.info(
            f"[{self.device_id}] Light color: RGB("
            f"{self.state['r']}, {self.state['g']}, {self.state['b']})"
        )

    def send_command(self, command: str, params: Dict[str, Any]):
        """Handle light-specific commands."""
        if command == "set_brightness":
            self.set_brightness(int(params.get("brightness", 0)))
        elif command == "set_color":
            self.set_color(
                int(params.get("r", 0)),
                int(params.get("g", 0)),
                int(params.get("b", 0)),
            )
        else:
            super().send_command(command, params)


class MockWindDevice(MockDeviceBase):
    """Mock wind/fan device."""

    def __init__(
        self, device_id: str, properties: Optional[Dict[str, Any]] = None
    ):
        super().__init__(device_id, properties)
        self.state = {"speed": 0, "direction": "forward"}

    def set_speed(self, speed: int):
        """Set fan speed (0-100)."""
        self.state["speed"] = max(0, min(100, speed))
        logger.info(f"[{self.device_id}] Wind speed: {self.state['speed']}%")

    def set_direction(self, direction: str):
        """Set wind direction ('forward', 'reverse')."""
        self.state["direction"] = direction
        logger.info(
            f"[{self.device_id}] Wind direction: " f"{self.state['direction']}"
        )

    def send_command(self, command: str, params: Dict[str, Any]):
        """Handle wind-specific commands."""
        if command == "set_speed":
            self.set_speed(int(params.get("speed", 0)))
        elif command == "set_direction":
            self.set_direction(params.get("direction", "forward"))
        else:
            super().send_command(command, params)


class MockVibrationDevice(MockDeviceBase):
    """Mock vibration/haptic device."""

    def __init__(
        self, device_id: str, properties: Optional[Dict[str, Any]] = None
    ):
        super().__init__(device_id, properties)
        self.state = {"intensity": 0, "duration": 0}

    def set_intensity(self, intensity: int):
        """Set vibration intensity (0-100)."""
        self.state["intensity"] = max(0, min(100, intensity))
        logger.info(
            f"[{self.device_id}] Vibration intensity: "
            f"{self.state['intensity']}%"
        )

    def set_duration(self, duration: int):
        """Set vibration duration in milliseconds."""
        self.state["duration"] = max(0, duration)
        logger.info(
            f"[{self.device_id}] Vibration duration: "
            f"{self.state['duration']}ms"
        )

    def send_command(self, command: str, params: Dict[str, Any]):
        """Handle vibration-specific commands."""
        if command == "set_intensity":
            self.set_intensity(int(params.get("intensity", 0)))
        elif command == "set_duration":
            self.set_duration(int(params.get("duration", 0)))
        else:
            super().send_command(command, params)


class MockScentDevice(MockDeviceBase):
    """Mock scent/smell diffuser device."""

    def __init__(
        self, device_id: str, properties: Optional[Dict[str, Any]] = None
    ):
        super().__init__(device_id, properties)
        self.state = {"scent": None, "intensity": 0}

    def set_scent(self, scent: str, intensity: int):
        """
        Activate a scent at a given intensity.

        Args:
            scent: scent identifier (e.g., 'rose', 'ocean', 'coffee')
            intensity: scent intensity (0-100)
        """
        self.state["scent"] = scent
        self.state["intensity"] = max(0, min(100, intensity))
        logger.info(
            f"[{self.device_id}] Scent: {self.state['scent']} "
            f"at {self.state['intensity']}% intensity"
        )

    def stop_scent(self):
        """Stop scent diffusion."""
        self.state["scent"] = None
        self.state["intensity"] = 0
        logger.info(f"[{self.device_id}] Scent stopped")

    def send_command(self, command: str, params: Dict[str, Any]):
        """Handle scent-specific commands."""
        if command == "set_scent":
            self.set_scent(
                params.get("scent", "unknown"),
                int(params.get("intensity", 0)),
            )
        elif command == "stop_scent":
            self.stop_scent()
        else:
            super().send_command(command, params)
