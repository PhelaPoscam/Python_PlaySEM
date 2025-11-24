"""
Integration tests for isolated vs direct routing logic.

Tests that devices with different connection modes and protocol lists
route effects correctly through the appropriate protocol channels.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.websockets import WebSocket
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.server.main import ControlPanelServer, ConnectedDevice


@pytest.fixture
def server():
    """Create a control panel server instance."""
    return ControlPanelServer()


class TestIsolatedRouting:
    """Test routing for devices in isolated connection mode."""

    @pytest.mark.asyncio
    async def test_isolated_mqtt_only_device_uses_mqtt(self, server):
        """Test that isolated device with MQTT protocol uses MQTT, not websocket."""
        # Create mock device with MQTT-only protocol
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "mqtt_isolated_001"
        mock_device.name = "MQTT Isolated Device"
        mock_device.type = "web"
        mock_device.protocols = ["mqtt"]
        mock_device.capabilities = ["vibration"]
        mock_device.connection_mode = "isolated"

        server.devices[mock_device.id] = mock_device

        # Mock websocket for device connection
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device

        # Mock websocket for control client
        mock_ws_client = AsyncMock(spec=WebSocket)

        # Mock send_effect_protocol to verify MQTT is used
        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            # Send effect
            effect_data = {
                "effect_type": "vibration",
                "intensity": 75,
                "duration": 500,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            # Verify send_effect_protocol was called with MQTT
            mock_send_protocol.assert_called_once()
            call_args = mock_send_protocol.call_args
            assert call_args[0][1] == "mqtt"  # Second arg is protocol
            assert (
                call_args[0][2]["effect_type"] == "vibration"
            )  # Third arg is effect_data

            # Verify websocket was NOT used for effect (only for confirmation)
            # The web_client should not receive the effect directly
            mock_ws_device.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_isolated_coap_device_uses_coap(self, server):
        """Test that isolated device with CoAP protocol uses CoAP."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "coap_isolated_002"
        mock_device.name = "CoAP Isolated Device"
        mock_device.type = "web"
        mock_device.protocols = ["coap"]
        mock_device.capabilities = ["light"]
        mock_device.connection_mode = "isolated"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            effect_data = {
                "effect_type": "light",
                "intensity": 100,
                "duration": 2000,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            mock_send_protocol.assert_called_once()
            call_args = mock_send_protocol.call_args
            assert call_args[0][1] == "coap"
            mock_ws_device.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_isolated_websocket_only_falls_back_to_websocket(
        self, server
    ):
        """Test that isolated device with only websocket protocol uses websocket."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "ws_isolated_003"
        mock_device.name = "WebSocket Only Isolated"
        mock_device.type = "web"
        mock_device.protocols = ["websocket"]
        mock_device.capabilities = ["wind"]
        mock_device.connection_mode = "isolated"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        # Should NOT call send_effect_protocol
        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            effect_data = {
                "effect_type": "wind",
                "intensity": 50,
                "duration": 1000,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            # Verify protocol routing was NOT used
            mock_send_protocol.assert_not_called()

            # Verify websocket WAS used
            mock_ws_device.send_json.assert_called_once()
            message = mock_ws_device.send_json.call_args[0][0]
            assert message["type"] == "effect"
            assert message["effect_type"] == "wind"
            assert message["intensity"] == 50

    @pytest.mark.asyncio
    async def test_isolated_prefers_first_non_websocket_protocol(self, server):
        """Test that isolated device with multiple protocols chooses first non-websocket."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "multi_isolated_004"
        mock_device.name = "Multi-Protocol Isolated"
        mock_device.type = "web"
        mock_device.protocols = ["websocket", "http", "mqtt", "coap"]
        mock_device.capabilities = ["vibration", "light"]
        mock_device.connection_mode = "isolated"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            effect_data = {
                "effect_type": "vibration",
                "intensity": 60,
                "duration": 800,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            # Should use HTTP (first non-websocket in list)
            mock_send_protocol.assert_called_once()
            call_args = mock_send_protocol.call_args
            assert call_args[0][1] == "http"


class TestDirectRouting:
    """Test routing for devices in direct connection mode."""

    @pytest.mark.asyncio
    async def test_direct_device_with_mqtt_uses_websocket(self, server):
        """Test that direct device uses websocket even if other protocols available."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "direct_mqtt_001"
        mock_device.name = "Direct MQTT Device"
        mock_device.type = "web"
        mock_device.protocols = ["mqtt", "websocket"]
        mock_device.capabilities = ["vibration"]
        mock_device.connection_mode = "direct"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            effect_data = {
                "effect_type": "vibration",
                "intensity": 80,
                "duration": 600,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            # Should NOT use protocol routing for direct mode
            mock_send_protocol.assert_not_called()

            # Should use websocket directly
            mock_ws_device.send_json.assert_called_once()
            message = mock_ws_device.send_json.call_args[0][0]
            assert message["type"] == "effect"
            assert message["effect_type"] == "vibration"

    @pytest.mark.asyncio
    async def test_direct_device_multiple_protocols_prefers_websocket(
        self, server
    ):
        """Test that direct device with many protocols still uses websocket."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "direct_multi_002"
        mock_device.name = "Direct Multi-Protocol"
        mock_device.type = "web"
        mock_device.protocols = ["http", "mqtt", "coap", "websocket"]
        mock_device.capabilities = ["light", "wind"]
        mock_device.connection_mode = "direct"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            effect_data = {
                "effect_type": "light",
                "intensity": 90,
                "duration": 1500,
            }

            await server.send_effect(
                mock_ws_client, mock_device.id, effect_data
            )

            # Direct mode skips protocol routing
            mock_send_protocol.assert_not_called()

            # Uses websocket
            mock_ws_device.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_device_no_websocket_still_sends(self, server):
        """Test that direct device without websocket in protocol list still uses websocket connection."""
        mock_device = Mock(spec=ConnectedDevice)
        mock_device.id = "direct_no_ws_003"
        mock_device.name = "Direct No WebSocket Listed"
        mock_device.type = "web"
        mock_device.protocols = ["http", "mqtt"]
        mock_device.capabilities = ["vibration"]
        mock_device.connection_mode = "direct"

        server.devices[mock_device.id] = mock_device
        mock_ws_device = AsyncMock(spec=WebSocket)
        server.web_clients[mock_device.id] = mock_ws_device
        mock_ws_client = AsyncMock(spec=WebSocket)

        effect_data = {
            "effect_type": "vibration",
            "intensity": 70,
            "duration": 900,
        }

        await server.send_effect(mock_ws_client, mock_device.id, effect_data)

        # Should use websocket connection (direct mode bypasses protocol check)
        mock_ws_device.send_json.assert_called_once()
        message = mock_ws_device.send_json.call_args[0][0]
        assert message["type"] == "effect"


class TestMixedScenarios:
    """Test mixed device scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_devices_route_independently(self, server):
        """Test that multiple devices with different modes route correctly."""
        # Device 1: Isolated MQTT
        device1 = Mock(spec=ConnectedDevice)
        device1.id = "iso_mqtt"
        device1.name = "Isolated MQTT"
        device1.type = "web"
        device1.protocols = ["mqtt"]
        device1.capabilities = ["vibration"]
        device1.connection_mode = "isolated"

        # Device 2: Direct WebSocket
        device2 = Mock(spec=ConnectedDevice)
        device2.id = "dir_ws"
        device2.name = "Direct WebSocket"
        device2.type = "web"
        device2.protocols = ["websocket"]
        device2.capabilities = ["light"]
        device2.connection_mode = "direct"

        server.devices[device1.id] = device1
        server.devices[device2.id] = device2

        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        server.web_clients[device1.id] = mock_ws1
        server.web_clients[device2.id] = mock_ws2

        mock_ws_client = AsyncMock(spec=WebSocket)

        with patch.object(
            server, "send_effect_protocol", new=AsyncMock()
        ) as mock_send_protocol:
            # Send to device1 (isolated MQTT)
            await server.send_effect(
                mock_ws_client,
                device1.id,
                {"effect_type": "vibration", "intensity": 50, "duration": 500},
            )

            # Send to device2 (direct websocket)
            await server.send_effect(
                mock_ws_client,
                device2.id,
                {"effect_type": "light", "intensity": 100, "duration": 1000},
            )

            # Device1 should use MQTT protocol
            assert mock_send_protocol.call_count == 1
            call_args = mock_send_protocol.call_args
            assert call_args[0][1] == "mqtt"

            # Device1 websocket should NOT be used
            mock_ws1.send_json.assert_not_called()

            # Device2 websocket SHOULD be used
            mock_ws2.send_json.assert_called_once()
            message = mock_ws2.send_json.call_args[0][0]
            assert message["effect_type"] == "light"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
