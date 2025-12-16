import pytest
from fastapi.testclient import TestClient

from tools.test_server.main import ControlPanelServer


@pytest.fixture(scope="module")
def client():
    server = ControlPanelServer()
    with TestClient(server.app) as client:
        yield client


def test_health_and_stats_contract(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json().get("status") == "ok"

    stats = client.get("/api/stats")
    assert stats.status_code == 200
    body = stats.json()
    for key in [
        "effects_sent",
        "errors",
        "connected_devices",
        "uptime_seconds",
    ]:
        assert key in body


def test_device_register_and_list_contract(client):
    payload = {
        "device_id": "http_contract_1",
        "device_name": "Contract Device",
        "device_type": "http",
        "capabilities": ["light", "vibration"],
        "protocols": ["http"],
        "connection_mode": "direct",
    }

    resp = client.post("/api/devices/register", json=payload)
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    # Device list should include metadata
    list_resp = client.get("/api/devices")
    assert list_resp.status_code == 200
    devices = list_resp.json().get("devices", [])
    assert any(
        d.get("id") == "http_contract_1"
        and "protocols" in d
        and "capabilities" in d
        for d in devices
    )
