"""
Tests for the embedded MQTT Broker in protocol_server.py
"""

import asyncio
import socket
import json
import pytest
import logging
from unittest.mock import Mock, MagicMock, AsyncMock

import paho.mqtt.client as mqtt
from playsem.protocol_servers import MQTTServer
from playsem import EffectDispatcher, DeviceManager
from playsem.effect_metadata import EffectMetadata

from tests.wait import wait_until_async

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
    # Allocate a random free port to avoid conflicts across tests
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    server = MQTTServer(dispatcher=effect_dispatcher, host="127.0.0.1", port=free_port)
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
    # Allocate a random free port to avoid conflicts across tests
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    server = MQTTServer(dispatcher=effect_dispatcher, host="127.0.0.1", port=free_port)
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
    effect_dispatcher.async_dispatch_effect_metadata.reset_mock()
    # The mqtt_broker fixture has already started the server

    # Use a standard paho-mqtt client to connect and publish
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="test_client",
    )
    connection_result = {"value": -1}
    message_published = {"done": False}

    def on_connect(client, userdata, flags, reason_code, properties):
        connection_result["value"] = reason_code
        logger.info(f"paho-mqtt client connected with result code: {reason_code}")

    def on_publish(client, userdata, mid, reason_code, properties):
        message_published["done"] = True
        logger.info(f"Message published: {mid}")

    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        # Connect in executor with timeout
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: client.connect("127.0.0.1", mqtt_broker.port, 60)
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

        # Wait for the dispatcher to be called (replaces 1.0s sleep)
        await wait_until_async(
            lambda: effect_dispatcher.async_dispatch_effect_metadata.called,
            timeout=2.0,
            message="dispatcher was not called for MQTT message",
        )

        # Assert that the dispatcher was called
        effect_dispatcher.async_dispatch_effect_metadata.assert_called_once()

        # Check the content of the call
        call_args = effect_dispatcher.async_dispatch_effect_metadata.call_args
        dispatched_effect = call_args[0][0]
        assert isinstance(dispatched_effect, EffectMetadata)
        assert dispatched_effect.effect_type == "vibration"
        assert dispatched_effect.duration == 500
        assert dispatched_effect.intensity == 80
    finally:
        # Clean disconnect
        client.loop_stop()
        client.disconnect()


@pytest.mark.asyncio
async def test_mqtt_identical_payload_without_message_id_is_not_deduped(
    effect_dispatcher,
):
    """Repeated identical effects are valid unless sender provides an id."""
    server = MQTTServer(dispatcher=effect_dispatcher, host="127.0.0.1", port=0)
    server.loop = asyncio.get_running_loop()
    payload = json.dumps(
        {
            "effect_type": "vibration",
            "duration": 100,
            "intensity": 80,
        }
    )
    msg = MagicMock()
    msg.topic = "effects/vibration"
    msg.payload = payload.encode("utf-8")

    server._on_internal_message(None, None, msg)
    server._on_internal_message(None, None, msg)

    await asyncio.sleep(0.1)
    assert effect_dispatcher.async_dispatch_effect_metadata.call_count == 2


@pytest.mark.asyncio
async def test_mqtt_explicit_message_id_is_deduped(effect_dispatcher):
    """Explicit message ids prevent replay without dropping real repeated pulses."""
    server = MQTTServer(dispatcher=effect_dispatcher, host="127.0.0.1", port=0)
    server.loop = asyncio.get_running_loop()
    payload = json.dumps(
        {
            "message_id": "pulse-1",
            "effect_type": "vibration",
            "duration": 100,
            "intensity": 80,
        }
    )
    msg = MagicMock()
    msg.topic = "effects/vibration"
    msg.payload = payload.encode("utf-8")

    server._on_internal_message(None, None, msg)
    server._on_internal_message(None, None, msg)

    await asyncio.sleep(0.1)
    effect_dispatcher.async_dispatch_effect_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_external_broker_configuration(effect_dispatcher):
    """Test that setting use_external_broker avoids starting the embedded broker and connects to external client."""
    from unittest.mock import patch

    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        server = MQTTServer(
            dispatcher=effect_dispatcher,
            use_external_broker=True,
            external_host="192.168.1.50",
            external_port=18833,
        )

        assert not server.is_running()

        server.start()

        assert server.is_running()
        assert not hasattr(server, "thread")  # embedded broker thread not started

        # Verify client was configured and connected
        mock_client_instance.connect.assert_called_once_with("192.168.1.50", 18833, 60)
        mock_client_instance.loop_start.assert_called_once()

        server.stop()

        assert not server.is_running()
        mock_client_instance.loop_stop.assert_called_once()
        mock_client_instance.disconnect.assert_called_once()
