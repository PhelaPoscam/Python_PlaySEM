"""Protocol server start/stop and effect send tests."""

import pytest
from fastapi.testclient import TestClient

from examples.server.main import ControlPanelServer


@pytest.fixture(scope="module")
def app():
    server = ControlPanelServer()
    return server.app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "protocol", ["mqtt", "http", "coap", "upnp", "websocket"]
)
def test_start_protocol_server_and_send_effect(client, protocol):
    # WebSocket lifecycle
    with client.websocket_connect("/ws") as ws:
        # Start protocol server
        ws.send_json({"type": "start_protocol_server", "protocol": protocol})
        # Collect a few messages until we get protocol_status
        status_msg = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "protocol_status"
                and msg.get("protocol") == protocol
            ):
                status_msg = msg
                break
        assert status_msg is not None, f"No protocol_status for {protocol}"
        assert status_msg.get("running") is True
        # Send an effect via this protocol (except websocket which broadcasts)
        ws.send_json(
            {
                "type": "send_effect_protocol",
                "protocol": protocol,
                "effect": {
                    "effect_type": "vibration",
                    "intensity": 5,
                    "duration": 100,
                },
            }
        )
        effect_result = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "effect_protocol_result"
                and msg.get("protocol") == protocol
            ):
                effect_result = msg
                break
        assert (
            effect_result is not None
        ), f"No effect_protocol_result for {protocol}"
        assert effect_result.get("success") is True
        # Stop
        ws.send_json({"type": "stop_protocol_server", "protocol": protocol})
        stopped_msg = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "protocol_status"
                and msg.get("protocol") == protocol
                and msg.get("running") is False
            ):
                stopped_msg = msg
                break
        assert stopped_msg is not None, f"No stop confirmation for {protocol}"
