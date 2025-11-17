"""Tests for WebSocket server functionality"""

import json
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from src.protocol_server import WebSocketServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.effect_metadata import EffectMetadata


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
def websocket_server(effect_dispatcher):
    """Create a WebSocket server."""
    return WebSocketServer(
        host="localhost",
        port=8080,
        dispatcher=effect_dispatcher
    )


def test_websocket_server_initialization(effect_dispatcher):
    """Test WebSocket server initializes correctly."""
    server = WebSocketServer(
        host="0.0.0.0",
        port=9090,
        dispatcher=effect_dispatcher
    )
    
    assert server.host == "0.0.0.0"
    assert server.port == 9090
    assert server.dispatcher == effect_dispatcher
    assert not server.is_running()
    assert len(server.clients) == 0


@pytest.mark.asyncio
async def test_websocket_server_parse_effect(websocket_server):
    """Test parsing effect from message data."""
    data = {
        "effect_type": "light",
        "timestamp": 500,
        "duration": 2000,
        "intensity": 90,
        "location": "left"
    }
    
    effect = websocket_server._parse_effect(data)
    
    assert effect is not None
    assert effect.effect_type == "light"
    assert effect.timestamp == 500
    assert effect.duration == 2000
    assert effect.intensity == 90
    assert effect.location == "left"


@pytest.mark.asyncio
async def test_websocket_server_parse_effect_minimal(websocket_server):
    """Test parsing effect with minimal data."""
    data = {
        "effect_type": "wind"
    }
    
    effect = websocket_server._parse_effect(data)
    
    assert effect is not None
    assert effect.effect_type == "wind"
    assert effect.timestamp == 0
    assert effect.duration == 1000
    assert effect.intensity == 50


@pytest.mark.asyncio
async def test_websocket_server_parse_effect_invalid(websocket_server):
    """Test parsing invalid effect returns None."""
    data = {}  # Missing effect_type
    
    effect = websocket_server._parse_effect(data)
    
    assert effect is None


@pytest.mark.asyncio
async def test_websocket_server_broadcast(websocket_server):
    """Test broadcasting message to clients."""
    # Create mock clients
    mock_client1 = AsyncMock()
    mock_client2 = AsyncMock()
    
    websocket_server.clients.add(mock_client1)
    websocket_server.clients.add(mock_client2)
    
    message = {"type": "test", "data": "hello"}
    
    await websocket_server._broadcast(message)
    
    # Both clients should receive message
    mock_client1.send.assert_called_once()
    mock_client2.send.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_server_broadcast_with_exclude(websocket_server):
    """Test broadcasting excludes specified client."""
    # Create mock clients
    mock_client1 = AsyncMock()
    mock_client2 = AsyncMock()
    
    websocket_server.clients.add(mock_client1)
    websocket_server.clients.add(mock_client2)
    
    message = {"type": "test", "data": "hello"}
    
    await websocket_server._broadcast(message, exclude=mock_client1)
    
    # Only client2 should receive message
    mock_client1.send.assert_not_called()
    mock_client2.send.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_server_broadcast_effect(websocket_server):
    """Test broadcasting an effect to all clients."""
    # Create mock client
    mock_client = AsyncMock()
    websocket_server.clients.add(mock_client)
    
    effect = EffectMetadata(
        effect_type="vibration",
        timestamp=1000,
        duration=500,
        intensity=75
    )
    
    await websocket_server.broadcast_effect(effect)
    
    # Client should receive broadcast
    mock_client.send.assert_called_once()
    
    # Verify message content
    call_args = mock_client.send.call_args[0][0]
    message = json.loads(call_args)
    
    assert message["type"] == "effect_triggered"
    assert message["effect_type"] == "vibration"
    assert message["intensity"] == 75


@pytest.mark.asyncio
async def test_websocket_server_process_effect_message(websocket_server):
    """Test processing an effect message from client."""
    mock_websocket = AsyncMock()
    
    message = json.dumps({
        "type": "effect",
        "effect_type": "light",
        "timestamp": 0,
        "duration": 1000,
        "intensity": 100
    })
    
    # Mock dispatcher
    websocket_server.dispatcher.dispatch_effect_metadata = Mock()
    
    await websocket_server._process_message(
        mock_websocket,
        message,
        "test_client"
    )
    
    # Verify effect was dispatched
    websocket_server.dispatcher.dispatch_effect_metadata.assert_called_once()
    
    # Verify response was sent
    mock_websocket.send.assert_called()


@pytest.mark.asyncio
async def test_websocket_server_process_ping_message(websocket_server):
    """Test processing a ping message."""
    mock_websocket = AsyncMock()
    
    message = json.dumps({"type": "ping"})
    
    await websocket_server._process_message(
        mock_websocket,
        message,
        "test_client"
    )
    
    # Verify pong response was sent
    mock_websocket.send.assert_called_once()
    
    call_args = mock_websocket.send.call_args[0][0]
    response = json.loads(call_args)
    
    assert response["type"] == "pong"


@pytest.mark.asyncio
async def test_websocket_server_process_invalid_json(websocket_server):
    """Test processing invalid JSON."""
    mock_websocket = AsyncMock()
    
    message = "invalid json {{"
    
    await websocket_server._process_message(
        mock_websocket,
        message,
        "test_client"
    )
    
    # Verify error response was sent
    mock_websocket.send.assert_called_once()
    
    call_args = mock_websocket.send.call_args[0][0]
    response = json.loads(call_args)
    
    assert response["type"] == "error"
    assert "Invalid JSON" in response["message"]


@pytest.mark.asyncio
async def test_websocket_server_callback(websocket_server):
    """Test on_effect_received callback is called."""
    callback = Mock()
    websocket_server.on_effect_received = callback
    
    mock_websocket = AsyncMock()
    
    message = json.dumps({
        "type": "effect",
        "effect_type": "wind",
        "timestamp": 0,
        "duration": 2000,
        "intensity": 60
    })
    
    # Mock dispatcher
    websocket_server.dispatcher.dispatch_effect_metadata = Mock()
    
    await websocket_server._process_message(
        mock_websocket,
        message,
        "test_client"
    )
    
    # Verify callback was called
    callback.assert_called_once()
    effect = callback.call_args[0][0]
    assert effect.effect_type == "wind"
    assert effect.intensity == 60


def test_websocket_server_is_running(websocket_server):
    """Test is_running returns correct state."""
    assert not websocket_server.is_running()
    
    # Manually set running state (for testing)
    websocket_server._is_running = True
    assert websocket_server.is_running()
    
    websocket_server._is_running = False
    assert not websocket_server.is_running()
