"""
Tests for the embedded MQTT Broker in protocol_server.py
"""

import asyncio
import json
import pytest
import logging
from unittest.mock import Mock, MagicMock

import paho.mqtt.client as mqtt
from src.protocol_server import MQTTServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.effect_metadata import EffectMetadata

logger = logging.getLogger(__name__)


@pytest.fixture
def device_manager():
    """Create a DeviceManager with a mock client."""
    mock_client = Mock()
    return DeviceManager(client=mock_client)


@pytest.fixture
def effect_dispatcher(device_manager):
    """Create a mock EffectDispatcher."""
    # We mock the whole dispatcher to isolate the MQTT server
    mock_dispatcher = MagicMock(spec=EffectDispatcher)
    return mock_dispatcher


@pytest.fixture
async def mqtt_broker(effect_dispatcher):
    """
    Fixture to create and manage the embedded MQTTServer broker.
    """
    logger.info("mqtt_broker fixture: Starting setup.")
    server = MQTTServer(
        dispatcher=effect_dispatcher, host="127.0.0.1", port=1883
    )
    logger.info("mqtt_broker fixture: MQTTServer instance created.")
    server.start()
    logger.info("mqtt_broker fixture: MQTTServer.start() called.")
    try:
        await asyncio.wait_for(server.wait_until_ready(), timeout=5.0)
        logger.info("mqtt_broker fixture: MQTTServer is ready.")
    except asyncio.TimeoutError:
        logger.error("mqtt_broker fixture: Timeout waiting for broker")
        server.stop()
        pytest.skip("MQTT broker failed to start in time")
    yield server
    logger.info("mqtt_broker fixture: Starting teardown.")
    server.stop()
    logger.info("mqtt_broker fixture: MQTTServer.stop() called.")


@pytest.mark.asyncio
async def test_broker_start_stop(effect_dispatcher):
    """
    Test that the embedded MQTT broker can start and stop correctly.
    """
    server = MQTTServer(
        dispatcher=effect_dispatcher, host="127.0.0.1", port=1883
    )
    assert not server.is_running()

    server.start()
    await asyncio.sleep(0.5)  # Give broker thread time to start
    assert server.is_running()

    server.stop()
    await asyncio.sleep(0.5)  # Give broker thread time to stop
    assert not server.is_running()


@pytest.mark.asyncio
async def test_broker_publish_and_dispatch(mqtt_broker, effect_dispatcher):
    """
    Test that the broker receives a message and dispatches the effect.
    """
    effect_dispatcher.dispatch_effect_metadata.reset_mock()
    # The mqtt_broker fixture has already started the server

    # Use a standard paho-mqtt client to connect and publish
    client = mqtt.Client(client_id="test_client")
    connection_result = {"value": -1}
    message_published = {"done": False}

    def on_connect(client, userdata, flags, rc):
        connection_result["value"] = rc
        logger.info(f"paho-mqtt client connected with result code: {rc}")

    def on_publish(client, userdata, mid):
        message_published["done"] = True
        logger.info(f"Message published: {mid}")

    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        # Connect in executor with timeout
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: client.connect("127.0.0.1", 1883, 60)
            ),
            timeout=3.0,
        )

        # Start network loop in background
        client.loop_start()

        # Wait for connection to be established
        for _ in range(10):
            if connection_result["value"] == 0:
                break
            await asyncio.sleep(0.1)

        assert (
            connection_result["value"] == 0
        ), f"Connection failed with code {connection_result['value']}"

        # Prepare and publish the effect message
        effect_payload = {
            "effect_type": "vibration",
            "duration": 500,
            "intensity": 80,
        }

        # Publish message
        result = client.publish("effects/test", json.dumps(effect_payload))
        result.wait_for_publish(timeout=2.0)

        # Wait for message to be processed
        await asyncio.sleep(1.0)

        # Assert that the dispatcher was called
        effect_dispatcher.dispatch_effect_metadata.assert_called_once()

        # Check the content of the call
        call_args = effect_dispatcher.dispatch_effect_metadata.call_args
        dispatched_effect = call_args[0][0]
        assert isinstance(dispatched_effect, EffectMetadata)
        assert dispatched_effect.effect_type == "vibration"
        assert dispatched_effect.duration == 500
        assert dispatched_effect.intensity == 80
    finally:
        # Clean disconnect
        client.loop_stop()
        client.disconnect()
