import asyncio
import json
import pytest
import paho.mqtt.client as mqtt
from playsem.effect_metadata import EffectMetadata


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

        # Wait for processing (Network -> Broker -> Internal Client -> Dispatcher -> Manager -> Driver)
        # 1.5s should be plenty for this in-process loop
        await asyncio.sleep(1.5)

        # VERIFICATION:
        # Check the mock_driver's total journal first
        assert len(system.mock_driver.command_history) >= 1

        # Check specific device state
        # The manager mapped "vibration_device" to our mock_driver
        # We need to find the specific device instance assigned to vibration_device
        # In our fixture, we manually mapped it, so we can check the history there

        # Locate the command in history
        found = False
        for entry in system.mock_driver.command_history:
            if (
                entry["device_id"] == "vibration_device"
                and entry["command"] == "set_intensity"
            ):
                if entry["params"].get("intensity") == 85:
                    found = True
                    break

        assert found, (
            "Vibration command not found in journal. "
            f"History: {system.mock_driver.command_history}"
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
        await asyncio.sleep(1.0)
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
        e["params"].get("g") == 255
        for e in history
        if e["device_id"] == "light_device"
    )
    assert green_found
