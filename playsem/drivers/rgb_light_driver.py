#!/usr/bin/env python3
"""Reference RGB light driver for Phase 5 hardware-capability flow."""

import logging
from typing import Dict, Any, Optional, List

from .base_driver import BaseDriver

logger = logging.getLogger(__name__)


class RGBLightDriver(BaseDriver):
    """Concrete light driver with RGB + brightness commands."""

    def __init__(self, interface_name: str, max_brightness: int = 255):
        self.interface_name = interface_name
        self.max_brightness = max(1, max_brightness)
        self._connected = False
        self.command_log: List[Dict[str, Any]] = []

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_interface_name(self) -> str:
        return self.interface_name

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self._connected:
            logger.warning("RGBLightDriver send rejected: disconnected")
            return False

        payload = dict(params or {})

        if command == "set_brightness":
            brightness = payload.get("brightness")
            if brightness is None and "intensity" in payload:
                intensity = int(payload["intensity"])
                brightness = int(self.max_brightness * intensity / 100)
            if brightness is None:
                brightness = 0
            payload["brightness"] = max(
                0, min(self.max_brightness, int(brightness))
            )

        if command == "set_color":
            payload["r"] = max(0, min(255, int(payload.get("r", 0))))
            payload["g"] = max(0, min(255, int(payload.get("g", 0))))
            payload["b"] = max(0, min(255, int(payload.get("b", 0))))

        self.command_log.append(
            {
                "device_id": device_id,
                "command": command,
                "params": payload,
            }
        )
        return True

    def get_capabilities(self, device_id: str) -> Optional[Dict[str, Any]]:
        from ..device_capabilities import (
            DeviceCapabilities,
            EffectCapability,
            EffectType,
            ParameterCapability,
            ParameterType,
            create_standard_duration_param,
            create_standard_intensity_param,
        )

        caps = DeviceCapabilities(
            device_id=device_id,
            device_type="RGBLight",
            manufacturer="PythonPlaySEM",
            model="Reference RGB Light",
            driver_type="rgb_light",
            metadata={"max_brightness": self.max_brightness},
        )

        caps.effects.append(
            EffectCapability(
                effect_type=EffectType.LIGHT,
                description="RGB light with brightness and color channels",
                parameters=[
                    create_standard_intensity_param(),
                    create_standard_duration_param(),
                    ParameterCapability(
                        name="brightness",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=self.max_brightness,
                        required=False,
                        default=0,
                        description="Direct brightness value",
                    ),
                    ParameterCapability(
                        name="r",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        required=False,
                        default=255,
                        description="Red channel",
                    ),
                    ParameterCapability(
                        name="g",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        required=False,
                        default=255,
                        description="Green channel",
                    ),
                    ParameterCapability(
                        name="b",
                        type=ParameterType.INTEGER,
                        min_value=0,
                        max_value=255,
                        required=False,
                        default=255,
                        description="Blue channel",
                    ),
                ],
            )
        )

        return caps.to_dict()
