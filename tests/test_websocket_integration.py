"""Integration tests for WebSocket server - tests real connections"""

import json
import pytest
import asyncio
import websockets

from src.protocol_server import WebSocketServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.device_driver.mock_driver import MockDriver


@pytest.fixture
def device_manager():
    """Create a DeviceManager for testing."""
    return DeviceManager()


@pytest.fixture
def effect_dispatcher(device_manager):
    """Create an EffectDispatcher."""
    return EffectDispatcher(device_manager)


@pytest.mark.asyncio
async def test_websocket_real_connection(effect_dispatcher):
    """
    Integration test: Start real WebSocket server and connect real client.
    
    This test catches signature issues that unit tests miss!
    """
    # Register a device to receive effects
    driver = MockDriver("test_light")
    manager = effect_dispatcher.device_manager
    manager.register_device("test_light", "light", driver)
    
    # Track received effects
    received_effects = []
    
    def on_effect(effect):
        received_effects.append(effect)
    
    # Start server on fixed port for testing
    server = WebSocketServer(
        host="localhost",
        port=18765,  # Test port
        dispatcher=effect_dispatcher
    )
    server.on_effect_received = on_effect
    
    # Start server in background task
    server_task = asyncio.create_task(server.start())
    
    # Give server time to start
    await asyncio.sleep(0.3)
    
    try:
        # Connect real WebSocket client
        uri = "ws://localhost:18765"
        async with websockets.connect(uri) as websocket:
            
            # Should receive welcome message
            welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            welcome_data = json.loads(welcome)
            assert welcome_data["type"] == "welcome"
            assert "Connected to PythonPlaySEM" in welcome_data["message"]
            
            # Send an effect
            effect_msg = {
                "type": "effect",
                "effect_type": "light",
                "intensity": 90,
                "duration": 1500
            }
            await websocket.send(json.dumps(effect_msg))
            
            # Wait briefly for processing
            await asyncio.sleep(0.2)
            
            # Should have received the effect
            assert len(received_effects) == 1
            assert received_effects[0].effect_type == "light"
            assert received_effects[0].intensity == 90
            assert received_effects[0].duration == 1500
            
            # Driver should have received effect
            assert len(driver.effects_sent) == 1
            assert driver.effects_sent[0] == ("light", 90, 1500)
            
            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Should receive pong
            pong = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            pong_data = json.loads(pong)
            assert pong_data["type"] == "pong"
            
    finally:
        # Clean up
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_websocket_multiple_clients(effect_dispatcher):
    """
    Integration test: Multiple real clients connecting simultaneously.
    """
    server = WebSocketServer(
        host="localhost",
        port=18766,  # Different port
        dispatcher=effect_dispatcher
    )
    
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.3)
    
    try:
        # Connect two clients
        uri = "ws://localhost:18766"
        async with websockets.connect(uri) as client1:
            async with websockets.connect(uri) as client2:
                
                # Both should get welcome
                welcome1 = await asyncio.wait_for(client1.recv(), timeout=2.0)
                welcome2 = await asyncio.wait_for(client2.recv(), timeout=2.0)
                
                assert json.loads(welcome1)["type"] == "welcome"
                assert json.loads(welcome2)["type"] == "welcome"
                
                # Client 1 sends effect
                effect = {
                    "type": "effect",
                    "effect_type": "wind",
                    "intensity": 50,
                    "duration": 1000
                }
                await client1.send(json.dumps(effect))
                
                # Wait for broadcast
                await asyncio.sleep(0.2)
                
                # Both clients should receive messages
                # (client1 gets response, client2 gets broadcast)
                msg1 = await asyncio.wait_for(client1.recv(), timeout=1.0)
                msg2 = await asyncio.wait_for(client2.recv(), timeout=1.0)
                
                # At least one should be the effect broadcast
                data1 = json.loads(msg1)
                data2 = json.loads(msg2)
                
                # Check that effect was processed
                assert (data1["type"] in ["response", "effect"] or 
                        data2["type"] in ["response", "effect"])
                
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_websocket_invalid_json(effect_dispatcher):
    """
    Integration test: Server handles invalid JSON gracefully.
    """
    server = WebSocketServer(
        host="localhost",
        port=18767,  # Different port
        dispatcher=effect_dispatcher
    )
    
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.3)
    
    try:
        uri = "ws://localhost:18767"
        async with websockets.connect(uri) as client:
            # Receive welcome
            await asyncio.wait_for(client.recv(), timeout=2.0)
            
            # Send invalid JSON
            await client.send("this is not json")
            
            # Should receive error response
            response = await asyncio.wait_for(client.recv(), timeout=1.0)
            data = json.loads(response)
            
            assert data["type"] == "error"
            assert "JSON" in data["message"]
            
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(0.1)
