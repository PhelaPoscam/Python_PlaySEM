#!/usr/bin/env python3
import pytest

from src.device_driver.mock_driver import MockConnectivityDriver
from src.protocol_server import HTTPServer


class _FakeDeviceManager:
    def __init__(self, driver):
        self.driver = driver


class _FakeDispatcher:
    def __init__(self, driver):
        self.device_manager = _FakeDeviceManager(driver)


def test_mock_driver_light_capabilities():
    driver = MockConnectivityDriver()
    driver.connect()
    caps = driver.get_capabilities("mock_light_1")
    assert caps is not None
    assert any(e["effect_type"] == "light" for e in caps.get("effects", []))


def test_http_capabilities_endpoint_returns_caps():
    # Setup HTTP server with a fake dispatcher/driver
    driver = MockConnectivityDriver()
    dispatcher = _FakeDispatcher(driver)

    server = HTTPServer(
        host="127.0.0.1",
        port=0,
        dispatcher=dispatcher,
        api_key=None,
    )

    # Use FastAPI TestClient to hit the endpoint (skip if incompatible)
    try:
        from fastapi.testclient import TestClient
        client = TestClient(server._app)
    except Exception:
        pytest.skip("TestClient not available or incompatible with environment")
    resp = client.get("/api/capabilities/mock_light_1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert any(
        e.get("effect_type") == "light" for e in data.get("effects", [])
    )
