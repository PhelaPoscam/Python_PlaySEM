#!/usr/bin/env python3
"""
Device Capabilities System for PythonPlaySEM.

This module provides a comprehensive system for describing device capabilities,
enabling clients to discover what effects and parameters each device supports.

The capability system supports:
- Effect type enumeration (light, wind, vibration, scent, etc.)
- Parameter definitions with ranges, types, and validation
- Metadata about device characteristics
- JSON serialization for API endpoints
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class ParameterType(str, Enum):
    """Types of parameters that devices can accept."""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"


class EffectType(str, Enum):
    """Standard sensory effect types supported by the framework."""

    LIGHT = "light"
    WIND = "wind"
    VIBRATION = "vibration"
    SCENT = "scent"
    TEMPERATURE = "temperature"
    HAPTIC = "haptic"
    AUDIO = "audio"
    MOTION = "motion"
    CUSTOM = "custom"


def _val_err(
    ptype: str,
    val: Any,
    min_v: Any = None,
    max_v: Any = None,
    enum_v: Any = None,
) -> Optional[str]:
    pt = ptype.value if hasattr(ptype, "value") else str(ptype)
    t_map: dict[str, type | tuple[type, ...]] = {
        "integer": int,
        "float": (int, float),
        "boolean": bool,
        "string": str,
    }
    expected = t_map.get(pt)
    if expected is not None:
        if expected in (int, (int, float)) and isinstance(val, bool):
            return f"must be {pt}"
        if not isinstance(val, expected):
            return f"must be {pt}"
    if pt == "enum" and enum_v and val not in enum_v:
        return f"must be one of {enum_v}"
    if (
        pt in ("integer", "float")
        and isinstance(val, (int, float))
        and not isinstance(val, bool)
    ):
        if min_v is not None and val < min_v:
            return f"below min value {min_v}"
        if max_v is not None and val > max_v:
            return f"above max value {max_v}"
    return None


@dataclass
class ParameterCapability:
    """
    Describes a single parameter that a device can accept.

    Attributes:
        name: Parameter name (e.g., "intensity", "color", "speed")
        type: Data type of the parameter
        required: Whether this parameter is required
        default: Default value if not specified
        min_value: Minimum value (for numeric types)
        max_value: Maximum value (for numeric types)
        enum_values: Valid values (for enum type)
        unit: Unit of measurement (e.g., "percent", "rpm", "celsius")
        description: Human-readable description
    """

    name: str
    type: ParameterType
    required: bool = False
    default: Optional[Union[int, float, str, bool]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    enum_values: Optional[List[str]] = None
    unit: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                # Convert enum to string value
                if isinstance(value, ParameterType):
                    result[key] = value.value
                else:
                    result[key] = value
        return result

    def validate(self, value: Any) -> bool:
        """
        Validate a parameter value against this capability.

        Args:
            value: The value to validate

        Returns:
            bool: True if value is valid, False otherwise
        """
        return (
            _val_err(
                self.type,
                value,
                self.min_value,
                self.max_value,
                self.enum_values,
            )
            is None
        )


@dataclass
class EffectCapability:
    """
    Describes a single effect type that a device supports.

    Attributes:
        effect_type: The type of effect (light, wind, etc.)
        parameters: List of parameters this effect accepts
        description: Human-readable description
        examples: Example effect commands
    """

    effect_type: EffectType
    parameters: List[ParameterCapability] = field(default_factory=list)
    description: Optional[str] = None
    examples: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "effect_type": self.effect_type.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "description": self.description,
            "examples": self.examples,
        }

    def get_parameter(self, name: str) -> Optional[ParameterCapability]:
        """Get parameter capability by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a set of parameters against this effect capability.

        Args:
            params: Dictionary of parameter name -> value

        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        errors = []

        # Check required parameters
        for param_cap in self.parameters:
            if param_cap.required and param_cap.name not in params:
                errors.append(f"Required parameter '{param_cap.name}' is missing")

        # Validate provided parameters
        for param_name, param_value in params.items():
            cap = self.get_parameter(param_name)
            if cap is None:
                errors.append(f"Unknown parameter '{param_name}'")
            elif not cap.validate(param_value):
                errors.append(
                    f"Invalid value for parameter " f"'{param_name}': {param_value}"
                )

        return len(errors) == 0, errors


@dataclass
class DeviceCapabilities:
    """
    Complete capability description for a device.

    Attributes:
        device_id: Unique identifier for the device
        device_type: Type/model of device (e.g., "Arduino_LED", "ESP32_Wind")
        effects: List of effects this device supports
        manufacturer: Device manufacturer
        model: Device model name
        firmware_version: Device firmware version
        driver_type: Type of driver (serial, bluetooth, mqtt, mock)
        metadata: Additional device-specific metadata
    """

    device_id: str
    device_type: str
    effects: List[EffectCapability] = field(default_factory=list)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    driver_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "effects": [e.to_dict() for e in self.effects],
            "driver_type": self.driver_type,
        }

        # Add optional fields if present
        if self.manufacturer:
            result["manufacturer"] = self.manufacturer
        if self.model:
            result["model"] = self.model
        if self.firmware_version:
            result["firmware_version"] = self.firmware_version
        if self.metadata:
            result["metadata"] = self.metadata  # type: ignore

        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def supports_effect(self, effect_type: Union[str, EffectType]) -> bool:
        """Check if device supports a specific effect type."""
        if isinstance(effect_type, str):
            effect_type = EffectType(effect_type)

        return any(e.effect_type == effect_type for e in self.effects)

    def get_effect_capability(
        self, effect_type: Union[str, EffectType]
    ) -> Optional[EffectCapability]:
        """Get capability info for a specific effect type."""
        if isinstance(effect_type, str):
            effect_type = EffectType(effect_type)

        for effect in self.effects:
            if effect.effect_type == effect_type:
                return effect
        return None


def create_standard_intensity_param(
    min_val: int = 0,
    max_val: int = 100,
    default: int = 50,
    required: bool = False,
) -> ParameterCapability:
    """Helper to create a standard intensity parameter (0-100)."""
    return ParameterCapability(
        name="intensity",
        type=ParameterType.INTEGER,
        required=required,
        default=default,
        min_value=min_val,
        max_value=max_val,
        unit="percent",
        description="Effect intensity as a percentage",
    )


def create_standard_duration_param(
    min_val: int = 0,
    max_val: Optional[int] = None,
    default: int = 1000,
    required: bool = False,
) -> ParameterCapability:
    """Helper to create a standard duration parameter (milliseconds)."""
    return ParameterCapability(
        name="duration",
        type=ParameterType.INTEGER,
        required=required,
        default=default,
        min_value=min_val,
        max_value=max_val,
        unit="milliseconds",
        description="Effect duration in milliseconds",
    )


def create_color_param(
    required: bool = False, default: str = "#FFFFFF"
) -> ParameterCapability:
    """Helper to create a color parameter (hex string)."""
    return ParameterCapability(
        name="color",
        type=ParameterType.STRING,
        required=required,
        default=default,
        description="Color in hex format (e.g., #FF0000 for red)",
    )


def validate_capability_contract(capabilities: Dict[str, Any]) -> bool:
    """Validate minimal schema for capability dictionaries."""
    if not isinstance(capabilities, dict):
        return False

    required = ["device_id", "device_type", "effects", "driver_type"]
    if any(key not in capabilities for key in required):
        return False

    effects = capabilities.get("effects")
    if not isinstance(effects, list):
        return False

    for effect in effects:
        if not isinstance(effect, dict):
            return False
        if "effect_type" not in effect:
            return False
        params = effect.get("parameters", [])
        if not isinstance(params, list):
            return False
        for param in params:
            if not isinstance(param, dict):
                return False
            if "name" not in param or "type" not in param:
                return False

    return True


def validate_effect_parameters(
    capabilities: Dict[str, Any], effect_type: str, params: Dict[str, Any]
) -> tuple[bool, List[str]]:
    """Validate effect parameters against a capabilities dictionary."""
    if not validate_capability_contract(capabilities):
        return False, ["Invalid capability contract"]

    effects = capabilities.get("effects", [])
    matched = next(
        (
            e
            for e in effects
            if str(e.get("effect_type", "")).lower() == effect_type.lower()
        ),
        None,
    )
    if matched is None:
        return False, [f"Effect '{effect_type}' is not supported"]

    param_defs = {p.get("name"): p for p in matched.get("parameters", [])}
    errors: List[str] = []

    for name, definition in param_defs.items():
        if definition.get("required") and name not in params:
            errors.append(f"Required parameter '{name}' is missing")

    for name, value in params.items():
        definition = param_defs.get(name)
        if definition is None:
            errors.append(f"Unknown parameter '{name}'")
            continue

        err = _val_err(
            definition.get("type"),
            value,
            definition.get("min_value"),
            definition.get("max_value"),
            definition.get("enum_values"),
        )
        if err:
            errors.append(f"Parameter '{name}' {err}")

    return len(errors) == 0, errors
