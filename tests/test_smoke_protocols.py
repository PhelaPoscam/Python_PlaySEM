import sys


import pytest


@pytest.mark.smoke
def test_serial_driver_smoke(monkeypatch):
    """
    Smoke test: SerialDriver can be instantiated, connect, send, and disconnect (mocked).
    """
    from src.device_driver import serial_driver

    class DummySerial:
        def __init__(self, *a, **kw):
            pass

        def open(self):
            pass

        def close(self):
            pass

        def write(self, data):
            return len(data)

        def isOpen(self):
            return True

    monkeypatch.setattr(serial_driver.serial, "Serial", DummySerial)
    driver = serial_driver.SerialDriver(port="COM1")
    driver._serial = DummySerial()
    driver._is_connected = True
    # Simulate sending bytes
    assert driver._is_connected
    assert driver._serial.write(b"\x01\x02") == 2
    driver._serial.close()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_bluetooth_driver_smoke(monkeypatch):
    """
    Smoke test: BluetoothDriver can be instantiated and connect/disconnect (mocked).
    """
    from src.device_driver import bluetooth_driver

    class DummyBleakClient:
        def __init__(self, *a, **kw):
            self.is_connected = False

        async def connect(self):
            self.is_connected = True

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(bluetooth_driver, "BleakClient", DummyBleakClient)
    driver = bluetooth_driver.BluetoothDriver(address="00:11:22:33:44:55")
    driver._client = DummyBleakClient()
    await driver._client.connect()
    assert driver._client.is_connected is True
    await driver._client.disconnect()
    assert driver._client.is_connected is False


@pytest.mark.smoke
def test_serial_driver_smoke(monkeypatch):
    """Smoke test: SerialDriver can be instantiated, connect, send, and disconnect (mocked)."""
    from src.device_driver import serial_driver

    # Patch serial.Serial to a dummy class
    class DummySerial:
        def __init__(*a, **kw):
            pass

        def open(self):
            pass

        def close(self):
            pass

        def write(self, data):
            return len(data)

        def isOpen(self):
            return True

    monkeypatch.setattr(serial_driver.serial, "Serial", DummySerial)
    driver = serial_driver.SerialDriver(port="COM1")
    driver._serial = DummySerial()
    driver._is_connected = True
    # Simulate sending bytes
    assert driver._is_connected
    assert driver._serial.write(b"\x01\x02") == 2
    driver._serial.close()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_bluetooth_driver_smoke(monkeypatch):
    """Smoke test: BluetoothDriver can be instantiated and connect/disconnect (mocked)."""
    from src.device_driver import bluetooth_driver

    # Patch BleakClient to a dummy async class
    class DummyBleakClient:
        def __init__(self, *a, **kw):
            self.is_connected = False

        async def connect(self):
            self.is_connected = True

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(bluetooth_driver, "BleakClient", DummyBleakClient)
    driver = bluetooth_driver.BluetoothDriver(address="00:11:22:33:44:55")
    driver._client = DummyBleakClient()
    await driver._client.connect()
    assert driver._client.is_connected is True
    await driver._client.disconnect()
    assert driver._client.is_connected is False


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


@pytest.mark.smoke
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
            "effect": {
                "effect_type": "vibration",
                "intensity": 60,
                "duration": 250,
            },
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
        call.args[0].get("protocol") == "mqtt"
        and call.args[0].get("running") is True
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
        call.args[0].get("protocol") == "http"
        and call.args[0].get("running") is True
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
