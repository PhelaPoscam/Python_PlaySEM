import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import AsyncMock
from pathlib import Path
import sys

# Add project root to path so examples.server.main can be found
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.server.main import ControlPanelServer


@pytest.fixture
def server():
    return ControlPanelServer()


@pytest.fixture
def client(server):
    return TestClient(server.app)


def test_connect_and_effect_mock_via_http(client):
    # 1) connect a mock device via HTTP
    connect_resp = client.post(
        "/api/connect",
        json={"address": "mock_light_1", "driver_type": "mock"},
    )
    assert connect_resp.status_code == 200
    data = connect_resp.json()
    assert data["type"] == "success"

    # 2) send an effect via HTTP to connected mock device
    effect_resp = client.post(
        "/api/effect",
        json={
            "device_id": "mock_mock_light_1",
            "effect": {"effect_type": "vibration", "intensity": 60, "duration": 250},
        },
    )
    assert effect_resp.status_code == 200
    res = effect_resp.json()
    assert res.get("success") is True


@pytest.mark.asyncio
async def test_protocol_servers_mqtt_http_websocket(server):
    # Prepare an async mock websocket to receive control messages
    mock_ws = AsyncMock(spec=WebSocket)

    # Start MQTT server and verify start status
    await server.start_protocol_server(mock_ws, "mqtt")
    # Expect a status message from start_protocol_server
    assert any(
        call.args[0].get("protocol") == "mqtt" and call.args[0].get("running") is True
        for call in mock_ws.send_json.call_args_list
    )

    # Clear past calls
    mock_ws.send_json.reset_mock()

    # Send an effect using MQTT protocol and expect an effect_protocol_result
    await server.send_effect_protocol(
        mock_ws,
        "mqtt",
        {"effect_type": "vibration", "intensity": 70, "duration": 300},
    )

    assert any(
        (call.args[0].get("type") == "effect_protocol_result")
        and (call.args[0].get("success") is True)
        for call in mock_ws.send_json.call_args_list
    )

    # Stop the MQTT server after use
    await server.stop_protocol_server(mock_ws, "mqtt")

    # HTTP protocol: start and send effect
    mock_ws.send_json.reset_mock()
    await server.start_protocol_server(mock_ws, "http")
    assert any(
        call.args[0].get("protocol") == "http" and call.args[0].get("running") is True
        for call in mock_ws.send_json.call_args_list
    )

    mock_ws.send_json.reset_mock()
    await server.send_effect_protocol(
        mock_ws,
        "http",
        {"effect_type": "vibration", "intensity": 50, "duration": 200},
    )
    assert any(
        (call.args[0].get("type") == "effect_protocol_result")
        and (call.args[0].get("success") is True)
        for call in mock_ws.send_json.call_args_list
    )

    # WebSocket protocol server start
    mock_ws.send_json.reset_mock()
    await server.start_protocol_server(mock_ws, "websocket")
    assert any(
        (call.args[0].get("protocol") == "websocket")
        and (call.args[0].get("running") is True)
        for call in mock_ws.send_json.call_args_list
    )
    # Stop websocket and http servers
    await server.stop_protocol_server(mock_ws, "websocket")
    await server.stop_protocol_server(mock_ws, "http")
