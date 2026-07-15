import asyncio
import json
import pytest
import paho.mqtt.client as mqtt
from playsem.effect_metadata import EffectMetadata

from tests.wait import wait_until_async

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.mark.asyncio
async def test_mqtt_to_vibration_e2e(playsem_system):
    """
    E2E Scenario:
    1. System is running with an internal MQTT broker.
    2. External MQTT client publishes a vibration effect.
    3. Verify the MockVibrationDevice received the command physically.
    """
    system = playsem_system
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    # Connect to the embedded broker started by the fixture
    client.connect("127.0.0.1", system.mqtt_port, 60)
    client.loop_start()

    try:
        # Prepare effect payload
        effect_data = {
            "effect_type": "vibration",
            "intensity": 85,
            "duration": 400,
        }

        # Publish to the default topic the server listens to
        # By default, MQTTServer listens to "effects/#"
        client.publish("effects/vibration_device", json.dumps(effect_data))

        # Wait for the effect to land in the driver command history.
        # Replaces an arbitrary 1.5s sleep with a condition-based wait.
        await wait_until_async(
            lambda: any(
                entry["device_id"] == "vibration_device"
                and entry["command"] == "set_intensity"
                and entry["params"].get("intensity") == 85
                for entry in system.mock_driver.command_history
            ),
            timeout=3.0,
            message="vibration effect did not reach driver via MQTT",
        )

    finally:
        client.loop_stop()
        client.disconnect()


@pytest.mark.asyncio
async def test_cross_protocol_consistency(playsem_system):
    """
    Verify that effects sent via different means result in consistent driver states.
    """
    system = playsem_system

    # 1. Direct Dispatch
    effect = EffectMetadata(
        effect_type="light",
        intensity=50,
        parameters={"r": 255, "g": 0, "b": 0},
    )
    system.dispatcher.dispatch_effect_metadata(effect)

    # 2. MQTT Dispatch
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect("127.0.0.1", system.mqtt_port, 60)
    client.loop_start()
    try:
        client.publish(
            "effects/light_device",
            json.dumps(
                {
                    "effect_type": "light",
                    "intensity": 100,
                    "parameters": {"r": 0, "g": 255, "b": 0},
                }
            ),
        )
        # Wait for the green light command to land in the driver history.
        await wait_until_async(
            lambda: any(
                e["params"].get("g") == 255 and e["device_id"] == "light_device"
                for e in system.mock_driver.command_history
            ),
            timeout=2.0,
            message="green light command did not reach driver",
        )
    finally:
        client.loop_stop()
        client.disconnect()

    # Verify both commands hit the mock driver
    # Command 1: Light (intensity 50, red)
    # Command 2: Light (intensity 100, green)

    history = system.mock_driver.command_history
    assert len(history) >= 2

    # Check Green command (second one)
    green_found = any(
        e["params"].get("g") == 255 for e in history if e["device_id"] == "light_device"
    )
    assert green_found
