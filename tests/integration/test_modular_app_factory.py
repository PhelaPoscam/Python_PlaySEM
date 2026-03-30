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
