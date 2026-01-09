"""Protocol server start/stop and effect send tests."""

import pytest
from fastapi.testclient import TestClient

from tools.test_server.main import ControlPanelServer


@pytest.fixture(scope="module")
def app():
    server = ControlPanelServer()
    return server.app


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as client:
        yield client


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


@pytest.mark.timeout(20)
def test_mqtt_restart_cycle(client):
    """Start/stop/start MQTT to ensure restart path stays healthy."""
    with client.websocket_connect("/ws") as ws:
        # Start MQTT
        ws.send_json({"type": "start_protocol_server", "protocol": "mqtt"})
        running1 = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "protocol_status"
                and msg.get("protocol") == "mqtt"
            ):
                running1 = msg.get("running")
                break
        assert running1 is True

        # Stop MQTT
        ws.send_json({"type": "stop_protocol_server", "protocol": "mqtt"})
        stopped = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "protocol_status"
                and msg.get("protocol") == "mqtt"
            ):
                stopped = msg.get("running") is False
                break
        assert stopped is True

        # Restart MQTT
        ws.send_json({"type": "start_protocol_server", "protocol": "mqtt"})
        running2 = None
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "protocol_status"
                and msg.get("protocol") == "mqtt"
            ):
                running2 = msg.get("running")
                break
        assert running2 is True


@pytest.mark.timeout(10)
def test_websocket_register_and_effect_delivery(client):
    """End-to-end WS flow: register a web device then deliver an effect to it."""
    with client.websocket_connect("/ws") as ws:
        device_id = "ws_device_smoke"

        # Register a web device
        ws.send_json(
            {
                "type": "register_device",
                "device_id": device_id,
                "device_name": "WS Demo",
                "device_type": "web_client",
                "protocols": ["websocket"],
                "capabilities": ["light"],
                "connection_mode": "direct",
            }
        )

        # Expect device_registered acknowledgment
        registered = False
        for _ in range(10):
            msg = ws.receive_json()
            if (
                msg.get("type") == "device_registered"
                and msg.get("device_id") == device_id
            ):
                registered = True
                break
        assert registered, "Web device did not register"

        # Send an effect to the registered device
        ws.send_json(
            {
                "type": "send_effect",
                "device_id": device_id,
                "effect": {
                    "effect_type": "light",
                    "intensity": 10,
                    "duration": 50,
                },
            }
        )

        effect_result = None
        effect_payload = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg.get("type") == "effect_result":
                effect_result = msg
            if (
                msg.get("type") == "effect"
                and msg.get("effect_type") == "light"
            ):
                effect_payload = msg
            if effect_result and effect_payload:
                break

        assert effect_result and effect_result.get("success") is True
        assert effect_payload and effect_payload.get("effect_type") == "light"
