from fastapi.testclient import TestClient
import pytest

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover
    BeautifulSoup = None

# Import the server app
from examples.server.main import ControlPanelServer


@pytest.fixture(scope="module")
def test_app():
    server = ControlPanelServer()
    return server.app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_super_controller_route_serves_html(client):
    resp = client.get("/super_controller")
    assert resp.status_code == 200
    if BeautifulSoup is None:
        pytest.skip("beautifulsoup4 not installed")
    soup = BeautifulSoup(resp.text, "html.parser")
    assert soup.find(id="modality") is not None
    assert soup.find(id="deviceList") is not None
    assert soup.find(id="sendEffect") is not None
    assert soup.find(id="sendCapEffect") is not None
    assert soup.find(id="effectHistory") is not None
    h2_texts = [h.get_text(strip=True) for h in soup.find_all("h2")]
    assert any("Device & Effect Control" in t for t in h2_texts)
    assert "Quick Send" not in h2_texts
    assert "Device Capabilities" not in h2_texts


@pytest.mark.timeout(5)
def test_websocket_get_devices(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "get_devices"})
        data = ws.receive_json()
        assert data["type"] == "device_list"
        assert "devices" in data
        assert isinstance(data["devices"], list)


@pytest.mark.timeout(10)
def test_websocket_protocol_mqtt_publish(client):
    # This exercises the MQTT readiness logic and effect_protocol_result path
    with client.websocket_connect("/ws") as ws:
        ws.send_json(
            {
                "type": "send_effect_protocol",
                "protocol": "mqtt",
                "effect": {
                    "effect_type": "vibration",
                    "intensity": 10,
                    "duration": 100,
                },
            }
        )
        # We expect one or more messages; read until effect_protocol_result or timeout
        for _ in range(5):
            msg = ws.receive_json()
            if msg.get("type") == "effect_protocol_result":
                assert msg.get("protocol") == "mqtt"
                assert msg.get("success") is True
                break
        else:
            pytest.fail("Did not receive effect_protocol_result for MQTT")


@pytest.mark.timeout(10)
def test_websocket_send_effect_direct_no_devices(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json(
            {
                "type": "send_effect",
                "device_id": "nonexistent-device",
                "effect": {
                    "effect_type": "vibration",
                    "intensity": 50,
                    "duration": 200,
                },
            }
        )
        msg = ws.receive_json()
        assert msg.get("type") == "effect_result"
        assert msg.get("success") is False
        assert "Device not found" in msg.get("error", "")


@pytest.mark.timeout(10)
def test_websocket_simple_broadcast_effect(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json(
            {
                "type": "effect",
                "effect_type": "light",
                "intensity": 25,
                "duration": 300,
            }
        )
        # Expect broadcast effect message
        for _ in range(5):
            msg = ws.receive_json()
            if msg.get("type") == "effect_broadcast":
                assert msg.get("effect_type") == "light"
                assert msg.get("intensity") == 25
                assert msg.get("duration") == 300
                break
        else:
            pytest.fail("No effect_broadcast received for simple effect")
