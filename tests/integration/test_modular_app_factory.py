"""Integration tests for the Phase 3 modular server factory."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_modular_api():
    """Load modular API symbols or xfail when modules are unavailable."""
    try:
        from tools.test_server.app import create_app
        from tools.test_server.config import ServerConfig
    except ModuleNotFoundError as exc:
        pytest.xfail(
            "Phase 3 modular architecture not restored yet "
            f"(missing module: {exc.name})"
        )

    return create_app, ServerConfig


@pytest.fixture(scope="module")
def client():
    create_app, ServerConfig = _load_modular_api()
    app = create_app(ServerConfig(host="127.0.0.1", port=8090, debug=False))

    assert isinstance(app, FastAPI)

    with TestClient(app) as test_client:
        yield test_client


def test_create_app_returns_fastapi():
    create_app, ServerConfig = _load_modular_api()
    app = create_app(ServerConfig())
    assert isinstance(app, FastAPI)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_devices_endpoint_empty_list(client):
    response = client.get("/api/devices")
    assert response.status_code == 200
    payload = response.json()
    assert "devices" in payload
    assert isinstance(payload["devices"], list)


def test_websocket_connects(client):
    with client.websocket_connect("/ws") as websocket:
        # Connection success is the main assertion for this baseline test.
        websocket.send_json({"type": "ping"})


def test_devices_and_effects_routes_are_wired(client):
    connect_payload = {"address": "demo-device", "driver_type": "mock"}
    connect_response = client.post(
        "/api/devices/connect",
        json=connect_payload,
    )
    assert connect_response.status_code == 200
    connected_device_id = connect_response.json().get("device_id")

    effect_payload = {
        "device_id": connected_device_id,
        "effect": {"effect_type": "vibration", "intensity": 50},
    }
    effect_response = client.post("/api/effects/send", json=effect_payload)
    assert effect_response.status_code == 200
    assert effect_response.json().get("success") is True


@pytest.mark.asyncio
async def test_protocol_bridge_tags_broadcast_payload():
    create_app, ServerConfig = _load_modular_api()
    app = create_app(ServerConfig())

    captured = {}

    async def capture(message):
        captured.update(message)

    app.state.protocol_service.set_effect_callback(capture)
    await app.state.protocol_service._dispatch_bridge(
        type("Effect", (), {"effect_type": "light", "intensity": 80})(),
        "mqtt",
    )

    assert captured["device_id"] == "broadcast"
    assert captured["broadcast"] is True
    assert captured["source"] == "mqtt"


def test_broadcast_eligibility_blocks_anonymous_and_isolated():
    create_app, ServerConfig = _load_modular_api()
    app = create_app(ServerConfig())
    device_service = app.state.device_service

    device_service.register_device(
        device_id="direct_node",
        device_name="Direct Node",
        device_type="web",
        capabilities=[],
        protocols=["websocket"],
        connection_mode="Direct",
    )
    device_service.register_device(
        device_id="isolated_node",
        device_name="Isolated Node",
        device_type="web",
        capabilities=[],
        protocols=["websocket"],
        connection_mode="IsOlAtEd",
    )

    from tools.test_server.app.main import _can_receive_broadcast

    assert _can_receive_broadcast(device_service, "") is False
    assert _can_receive_broadcast(device_service, "direct_node") is True
    assert _can_receive_broadcast(device_service, "isolated_node") is False
    assert (
        device_service.get_device("isolated_node").connection_mode
        == "isolated"
    )
