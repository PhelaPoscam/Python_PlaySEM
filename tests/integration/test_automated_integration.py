# tests/test_automated_integration.py

import pytest
import httpx
import websockets
import json
import asyncio

# All tests in this file will use the asyncio event loop
pytestmark = pytest.mark.asyncio


async def test_http_health_check(live_server):
    """
    Test if the server's HTTP /health endpoint is responding.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{live_server}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


async def test_http_get_stats(live_server):
    """
    Test the /api/stats HTTP endpoint.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{live_server}/api/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "effects_sent" in stats
        assert "connected_devices" in stats


async def test_websocket_connection(live_server):
    """
    Test a basic WebSocket connection, send a ping, and disconnect.
    """
    ws_url = live_server.replace("http", "ws") + "/ws"
    async with websockets.connect(ws_url) as websocket:
        # Connection is implicitly tested by the context manager
        # In newer websockets library, check connection state instead of .open attribute
        assert websocket.state.name == "OPEN"
        # Send a ping and expect a pong (or at least no error)
        await websocket.send(json.dumps({"type": "ping"}))
        # The server may or may not send an explicit pong,
        # but the connection should remain open.
        # We'll just ensure we can close gracefully.
    # After exiting context manager, connection should be closed
    assert websocket.state.name == "CLOSED"


async def test_device_discovery_via_websocket(live_server):
    """
    Test the device discovery mechanism over WebSocket.
    """
    ws_url = live_server.replace("http", "ws") + "/ws"
    async with websockets.connect(ws_url) as websocket:
        # Request the device list
        await websocket.send(json.dumps({"type": "get_devices"}))

        # Wait for the response
        response_str = await asyncio.wait_for(websocket.recv(), timeout=5)
        response = json.loads(response_str)

        # Assert the response is a device list
        assert response["type"] == "device_list"
        assert "devices" in response
        assert isinstance(response["devices"], list)
