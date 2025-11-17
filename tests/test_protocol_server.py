"""Tests for protocol_server.py"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, call

from src.protocol_server import MQTTServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.effect_metadata import create_effect


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    client = MagicMock()
    client.connect = Mock()
    client.subscribe = Mock()
    client.publish = Mock()
    client.loop_start = Mock()
    client.loop_stop = Mock()
    client.disconnect = Mock()
    return client


@pytest.fixture
def device_manager():
    """Create a DeviceManager with mock client."""
    mock_client = Mock()
    mock_client.publish = Mock()
    return DeviceManager(client=mock_client)


@pytest.fixture
def effect_dispatcher(device_manager):
    """Create an EffectDispatcher."""
    return EffectDispatcher(device_manager)


@pytest.fixture
def mqtt_server(effect_dispatcher, mock_mqtt_client):
    """Create an MQTT server with mocked client."""
    with patch('src.protocol_server.mqtt.Client', return_value=mock_mqtt_client):
        server = MQTTServer(
            broker_address="localhost",
            dispatcher=effect_dispatcher,
            subscribe_topic="effects/#",
            port=1883
        )
        # Replace the client with our mock after initialization
        server.client = mock_mqtt_client
        return server


def test_mqtt_server_initialization(effect_dispatcher):
    """Test MQTT server initializes correctly."""
    with patch('src.protocol_server.mqtt.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        server = MQTTServer(
            broker_address="test.broker.com",
            dispatcher=effect_dispatcher,
            subscribe_topic="test/topic",
            port=1883
        )
        
        assert server.broker_address == "test.broker.com"
        assert server.port == 1883
        assert server.subscribe_topic == "test/topic"
        assert server.dispatcher == effect_dispatcher
        assert not server.is_running()


def test_mqtt_server_start(mqtt_server, mock_mqtt_client):
    """Test MQTT server starts correctly."""
    mqtt_server.start()
    
    # Verify connection and loop started
    mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
    mock_mqtt_client.loop_start.assert_called_once()
    assert mqtt_server.is_running()


def test_mqtt_server_stop(mqtt_server, mock_mqtt_client):
    """Test MQTT server stops correctly."""
    # Start first
    mqtt_server.start()
    
    # Then stop
    mqtt_server.stop()
    
    # Verify loop stopped and disconnected
    mock_mqtt_client.loop_stop.assert_called_once()
    mock_mqtt_client.disconnect.assert_called_once()
    assert not mqtt_server.is_running()


def test_mqtt_server_on_connect(mqtt_server, mock_mqtt_client):
    """Test MQTT on_connect callback."""
    # Simulate successful connection (rc=0)
    mqtt_server._on_connect(mock_mqtt_client, None, None, 0)
    
    # Should subscribe to topic and publish status
    mock_mqtt_client.subscribe.assert_called_once_with("effects/#")
    
    # Check status message was published
    publish_calls = mock_mqtt_client.publish.call_args_list
    status_published = any(
        call[0][0] == "status" for call in publish_calls
    )
    assert status_published


def test_mqtt_server_parse_effect_json(mqtt_server):
    """Test parsing effect from JSON payload."""
    payload = json.dumps({
        "effect_type": "light",
        "timestamp": 0,
        "duration": 1000,
        "intensity": 80
    })
    
    effect = mqtt_server._parse_effect(payload)
    
    assert effect is not None
    assert effect.effect_type == "light"
    assert effect.duration == 1000
    assert effect.intensity == 80


def test_mqtt_server_parse_effect_yaml(mqtt_server):
    """Test parsing effect from YAML payload."""
    payload = """
effect_type: wind
timestamp: 500
duration: 2000
intensity: 60
"""
    
    effect = mqtt_server._parse_effect(payload)
    
    assert effect is not None
    assert effect.effect_type == "wind"
    assert effect.timestamp == 500
    assert effect.duration == 2000
    assert effect.intensity == 60


def test_mqtt_server_parse_effect_invalid(mqtt_server):
    """Test parsing invalid effect returns None."""
    payload = "invalid data that is not json or yaml"
    
    effect = mqtt_server._parse_effect(payload)
    
    assert effect is None


def test_mqtt_server_on_message(mqtt_server, mock_mqtt_client):
    """Test MQTT on_message callback."""
    # Create mock message
    mock_msg = Mock()
    mock_msg.topic = "effects/light"
    mock_msg.payload = json.dumps({
        "effect_type": "light",
        "timestamp": 0,
        "duration": 1000,
        "intensity": 100
    }).encode('utf-8')
    
    # Mock the dispatcher's dispatch method
    mqtt_server.dispatcher.dispatch_effect_metadata = Mock()
    
    # Process message
    mqtt_server._on_message(mock_mqtt_client, None, mock_msg)
    
    # Verify effect was dispatched
    mqtt_server.dispatcher.dispatch_effect_metadata.assert_called_once()
    
    # Verify response was published
    response_calls = [
        call for call in mock_mqtt_client.publish.call_args_list
        if 'response' in str(call)
    ]
    assert len(response_calls) > 0


def test_mqtt_server_callback(mqtt_server, mock_mqtt_client):
    """Test on_effect_received callback is called."""
    callback = Mock()
    mqtt_server.on_effect_received = callback
    
    # Create mock message
    mock_msg = Mock()
    mock_msg.topic = "effects/vibration"
    mock_msg.payload = json.dumps({
        "effect_type": "vibration",
        "timestamp": 0,
        "duration": 500,
        "intensity": 75
    }).encode('utf-8')
    
    # Mock dispatcher
    mqtt_server.dispatcher.dispatch_effect_metadata = Mock()
    
    # Process message
    mqtt_server._on_message(mock_mqtt_client, None, mock_msg)
    
    # Verify callback was called
    callback.assert_called_once()
    effect = callback.call_args[0][0]
    assert effect.effect_type == "vibration"


def test_mqtt_server_double_start(mqtt_server):
    """Test starting server twice doesn't cause issues."""
    mqtt_server.start()
    
    # Try starting again
    mqtt_server.start()  # Should log warning but not crash
    
    assert mqtt_server.is_running()


def test_mqtt_server_stop_when_not_running(mqtt_server):
    """Test stopping server when not running."""
    # Stop without starting
    mqtt_server.stop()  # Should log warning but not crash
    
    assert not mqtt_server.is_running()
