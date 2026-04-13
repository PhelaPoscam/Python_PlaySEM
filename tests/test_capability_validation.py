from unittest.mock import MagicMock

import pytest

from playsem.device_capabilities import (
    validate_capability_contract,
    validate_effect_parameters,
)
from playsem.effect_dispatcher import EffectDispatcher


def test_capability_contract_validation_minimal_schema():
    caps = {
        "device_id": "d1",
        "device_type": "RGBLight",
        "driver_type": "rgb_light",
        "effects": [
            {
                "effect_type": "light",
                "parameters": [
                    {
                        "name": "intensity",
                        "type": "integer",
                        "min_value": 0,
                        "max_value": 100,
                    }
                ],
            }
        ],
    }
    assert validate_capability_contract(caps)


def test_effect_parameter_validation_rejects_out_of_range():
    caps = {
        "device_id": "d1",
        "device_type": "RGBLight",
        "driver_type": "rgb_light",
        "effects": [
            {
                "effect_type": "light",
                "parameters": [
                    {
                        "name": "intensity",
                        "type": "integer",
                        "min_value": 0,
                        "max_value": 100,
                    }
                ],
            }
        ],
    }

    ok, errors = validate_effect_parameters(caps, "light", {"intensity": 101})
    assert not ok
    assert any("above max" in error for error in errors)


def test_dispatcher_capability_validation_blocks_invalid_params():
    manager = MagicMock()
    manager.get_device_capabilities.return_value = {
        "device_id": "light_1",
        "device_type": "RGBLight",
        "driver_type": "rgb_light",
        "effects": [
            {
                "effect_type": "light",
                "parameters": [
                    {
                        "name": "intensity",
                        "type": "integer",
                        "min_value": 0,
                        "max_value": 100,
                    }
                ],
            }
        ],
    }

    dispatcher = EffectDispatcher(manager, validate_capabilities=True)
    dispatcher.effects_config = {
        "effects": {
            "light": {
                "device": "light_1",
                "command": "set_brightness",
            }
        }
    }

    with pytest.raises(ValueError, match="Capability validation failed"):
        dispatcher.dispatch_effect("light", {"intensity": 130})
