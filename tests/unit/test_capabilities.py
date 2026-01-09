#!/usr/bin/env python3
import asyncio

from playsem.drivers.mock_driver import MockConnectivityDriver
from playsem.protocol_servers import HTTPServer


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


async def _asgi_get(app, path: str):
    """Minimal ASGI client to perform a GET request without external deps."""
    status = None
    headers = []
    body_chunks = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status, headers
        if message["type"] == "http.response.start":
            status = message.get("status")
            headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }

    await app(scope, receive, send)

    return status, b"".join(body_chunks)


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

    # Use a minimal ASGI client to hit the endpoint (no httpx dependency)
    status, body = asyncio.run(
        _asgi_get(server._app, "/api/capabilities/mock_light_1")
    )
    assert status == 200
    import json

    data = json.loads(body.decode("utf-8"))
    assert isinstance(data, dict)
    assert any(
        e.get("effect_type") == "light" for e in data.get("effects", [])
    )
