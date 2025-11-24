import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path is set
from examples.server.main import ControlPanelServer


@pytest.fixture
def server():
    """Create a control panel server instance."""
    return ControlPanelServer()


@pytest.fixture
def client(server):
    """Create a test client."""
    return TestClient(server.app)


class TestDeviceRegistration:
    """Test device registration and listing."""

    def test_device_registration_via_http(self, client):
        """Test device registration via HTTP API."""
        device_data = {
            "device_id": "test_light_001",
            "device_name": "Test Light",
            "device_type": "Smart Device",
            "capabilities": ["light", "vibration"],
            "protocols": ["http", "mqtt"],
            "connection_mode": "isolated",
        }

        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post("/api/devices/register", json=device_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["device_id"] == "test_light_001"

    def test_device_list_includes_metadata(self, server):
        """Test that device list includes protocols, capabilities, and connection_mode."""
        # Mock a device with metadata
        from examples.server.main import ConnectedDevice

        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "test_device_123"
        mock_device.name = "Test Device"
        mock_device.type = "Smart Device"
        mock_device.address = "192.168.1.100"
        mock_device.protocols = ["mqtt", "coap"]
        mock_device.capabilities = ["light", "vibration"]
        mock_device.connection_mode = "isolated"

        server.devices["test_device_123"] = mock_device

        # Create a mock websocket
        mock_ws = AsyncMock(spec=WebSocket)

        # Run the async function
        asyncio.run(server.send_device_list(mock_ws))

        # Verify the message sent
        mock_ws.send_json.assert_called_once()
        message = mock_ws.send_json.call_args[0][0]

        assert message["type"] == "device_list"
        assert len(message["devices"]) == 1

        device = message["devices"][0]
        assert device["id"] == "test_device_123"
        assert device["name"] == "Test Device"
        assert device["protocols"] == ["mqtt", "coap"]
        assert device["capabilities"] == ["light", "vibration"]
        assert device["connection_mode"] == "isolated"

    def test_broadcast_device_list_includes_metadata(self, server):
        """Test that broadcast_device_list includes all metadata."""
        from examples.server.main import ConnectedDevice

        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "broadcast_test_001"
        mock_device.name = "Broadcast Test"
        mock_device.type = "Sensor"
        mock_device.address = "10.0.0.5"
        mock_device.protocols = ["upnp"]
        mock_device.capabilities = ["temperature"]
        mock_device.connection_mode = "direct"

        server.devices["broadcast_test_001"] = mock_device

        # Add a mock client
        mock_client = AsyncMock(spec=WebSocket)
        server.clients.add(mock_client)

        # Run broadcast
        asyncio.run(server.broadcast_device_list())

        # Verify broadcast
        mock_client.send_json.assert_called_once()
        message = mock_client.send_json.call_args[0][0]

        assert message["type"] == "device_list"
        device = message["devices"][0]
        assert device["protocols"] == ["upnp"]
        assert device["capabilities"] == ["temperature"]
        assert device["connection_mode"] == "direct"


class TestWebSocketCommunication:
    """Test WebSocket protocol communication."""

    @pytest.mark.asyncio
    async def test_websocket_device_registration(self, server):
        """Test device registration via WebSocket."""
        mock_ws = AsyncMock(spec=WebSocket)

        # Simulate registration message
        registration_msg = {
            "type": "register_device",
            "device_id": "ws_device_001",
            "device_name": "WebSocket Device",
            "device_type": "Actuator",
            "capabilities": ["motor"],
            "protocols": ["websocket"],
            "connection_mode": "direct",
        }

        await server.register_web_device(mock_ws, registration_msg)

        # Verify device was registered
        assert "ws_device_001" in server.devices
        device = server.devices["ws_device_001"]
        assert device.name == "WebSocket Device"
        assert hasattr(device, "protocols")
        assert hasattr(device, "capabilities")
        assert hasattr(device, "connection_mode")

    @pytest.mark.asyncio
    async def test_get_devices_message(self, server):
        """Test that 'get_devices' message triggers device list send."""
        from examples.server.main import ConnectedDevice

        # Add a test device
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "test_123"
        mock_device.name = "Test"
        mock_device.type = "Device"
        mock_device.address = "localhost"
        mock_device.protocols = ["mqtt"]
        mock_device.capabilities = ["light"]
        mock_device.connection_mode = "direct"

        server.devices["test_123"] = mock_device

        mock_ws = AsyncMock(spec=WebSocket)

        # Simulate get_devices message
        message = {"type": "get_devices"}
        await server.handle_message(mock_ws, message)

        # Verify send_json was called with device list
        mock_ws.send_json.assert_called_once()
        sent_message = mock_ws.send_json.call_args[0][0]
        assert sent_message["type"] == "device_list"
        assert len(sent_message["devices"]) == 1


class TestShutdownBehavior:
    """Test graceful shutdown and cleanup."""

    @pytest.mark.asyncio
    async def test_shutdown_closes_websockets(self, server):
        """Test that shutdown closes all WebSocket connections."""
        # Add mock clients
        mock_client1 = AsyncMock(spec=WebSocket)
        mock_client2 = AsyncMock(spec=WebSocket)

        server.clients.add(mock_client1)
        server.clients.add(mock_client2)

        # Mock os._exit to prevent actual exit
        with patch("os._exit") as mock_exit:
            await server._shutdown()

        # Verify clients were closed
        mock_client1.close.assert_called_once()
        mock_client2.close.assert_called_once()
        assert len(server.clients) == 0

    @pytest.mark.asyncio
    async def test_shutdown_calls_os_exit(self, server):
        """Test that shutdown calls os._exit(0) to force process termination."""
        with patch("os._exit") as mock_exit:
            await server._shutdown()

        # Verify os._exit was called with 0
        mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_shutdown_stops_timeline_player(self, server):
        """Test that shutdown stops the timeline player."""
        server.timeline_player.stop = Mock()

        with patch("os._exit"):
            await server._shutdown()

        server.timeline_player.stop.assert_called_once()


class TestProtocolSupport:
    """Test multi-protocol support."""

    def test_http_device_registration_endpoint_exists(self, client):
        """Test that HTTP device registration endpoint exists."""
        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post(
                "/api/devices/register",
                json={
                    "device_id": "http_test",
                    "device_name": "HTTP Test Device",
                    "device_type": "Sensor",
                    "capabilities": ["temperature"],
                    "protocols": ["http"],
                    "connection_mode": "direct",
                },
            )
            assert response.status_code == 200

    def test_device_with_multiple_protocols(self, client):
        """Test device registration with multiple protocols."""
        device_data = {
            "device_id": "multi_proto_001",
            "device_name": "Multi Protocol Device",
            "device_type": "Hybrid",
            "capabilities": ["light", "vibration", "temperature"],
            "protocols": ["http", "mqtt", "coap", "upnp"],
            "connection_mode": "direct",
        }
        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post("/api/devices/register", json=device_data)
            assert response.status_code == 200

            # Verify device was registered
            data = response.json()
            assert data["device_id"] == "multi_proto_001"


class TestConnectionModes:
    """Test connection mode handling."""

    def test_direct_mode_device(self, client):
        """Test device registration in direct mode."""
        device_data = {
            "device_id": "direct_001",
            "device_name": "Direct Device",
            "device_type": "Light",
            "capabilities": ["light"],
            "protocols": ["websocket", "mqtt"],
            "connection_mode": "direct",
        }
        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post("/api/devices/register", json=device_data)
            assert response.status_code == 200

    def test_isolated_mode_device(self, client):
        """Test device registration in isolated mode."""
        device_data = {
            "device_id": "isolated_001",
            "device_name": "Isolated Device",
            "device_type": "Sensor",
            "capabilities": ["temperature"],
            "protocols": ["mqtt"],
            "connection_mode": "isolated",
        }
        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post("/api/devices/register", json=device_data)
            assert response.status_code == 200


class TestEffectBroadcasting:
    """Test effect broadcasting to devices."""

    @pytest.mark.asyncio
    async def test_effect_broadcast_to_websocket_devices(self, server):
        """Test that effects are broadcast to WebSocket-connected devices."""
        # Add mock device with WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        server.web_clients["test_device"] = mock_ws

        # Simulate effect broadcast
        effect_data = {
            "effect_type": "vibration",
            "intensity": 0.8,
            "duration": 2.0,
            "timestamp": 1234567890,
        }

        # Broadcast to clients
        message = {"type": "effect", "effect": effect_data}
        for client in list(server.web_clients.values()):
            await client.send_json(message)

        mock_ws.send_json.assert_called_once()
        sent = mock_ws.send_json.call_args[0][0]
        assert sent["type"] == "effect"
        assert sent["effect"]["effect_type"] == "vibration"


@pytest.mark.integration
class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_device_registration_and_listing(self, server):
        """Test complete flow: register device -> broadcast -> list."""
        from examples.server.main import ConnectedDevice

        # 1. Register device via WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        registration_msg = {
            "device_id": "e2e_test_001",
            "device_name": "E2E Test Device",
            "device_type": "Smart Light",
            "capabilities": ["light", "color"],
            "protocols": ["mqtt", "coap"],
            "connection_mode": "isolated",
        }
        await server.register_web_device(mock_ws, registration_msg)

        # 2. Verify device is in devices dict
        assert "e2e_test_001" in server.devices

        # 3. Send device list to controller
        controller_ws = AsyncMock(spec=WebSocket)
        await server.send_device_list(controller_ws)

        # 4. Verify controller received correct data
        controller_ws.send_json.assert_called_once()
        message = controller_ws.send_json.call_args[0][0]

        assert message["type"] == "device_list"
        device = message["devices"][0]
        assert device["id"] == "e2e_test_001"
        assert device["protocols"] == ["mqtt", "coap"]
        assert device["capabilities"] == ["light", "color"]
        assert device["connection_mode"] == "isolated"

    def test_http_to_websocket_flow(self, client, server):
        """Test HTTP registration followed by WebSocket listing."""
        # 1. Register via HTTP
        with patch('examples.server.main.ControlPanelServer.broadcast_device_list', new_callable=AsyncMock):
            response = client.post(
                "/api/devices/register",
                json={
                    "device_id": "http_ws_test",
                    "device_name": "HTTP WS Test",
                    "device_type": "Actuator",
                    "capabilities": ["motor"],
                    "protocols": ["http"],
                    "connection_mode": "direct",
                },
            )
            assert response.status_code == 200

        # 2. Verify device exists
        assert "http_ws_test" in server.devices

        # 3. Mock WebSocket client requesting device list
        mock_ws = AsyncMock(spec=WebSocket)
        asyncio.run(server.send_device_list(mock_ws))

        # 4. Verify response includes HTTP device
        mock_ws.send_json.assert_called_once()
        message = mock_ws.send_json.call_args[0][0]
        devices = {d["id"]: d for d in message["devices"]}

        assert "http_ws_test" in devices
        device = devices["http_ws_test"]
        assert device["protocols"] == ["http"]
        assert device["capabilities"] == ["motor"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])