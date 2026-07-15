import pytest
from fastapi.testclient import TestClient
from playsem import DeviceManager, DeviceRegistry
from playsem.protocol_servers.http_server import HTTPServer
from playsem.effect_dispatcher import EffectDispatcher
from playsem.drivers.base_driver import BaseDriver


class MockMetricsDriver(BaseDriver):
    def get_driver_type(self) -> str:
        return "mock"

    def get_interface_name(self) -> str:
        return "mock_interface"

    def is_connected(self) -> bool:
        return True

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def send_command(self, device_id: str, command: str, params: dict) -> bool:
        return True


@pytest.mark.asyncio
async def test_metrics_endpoint():
    registry = DeviceRegistry()
    driver = MockMetricsDriver()
    manager = DeviceManager(
        connectivity_driver=driver,
        circuit_breaker_failure_threshold=2,
        device_registry=registry,
    )
    dispatcher = EffectDispatcher(manager)

    # Configure a mock effect
    dispatcher.effects_config = {
        "effects": {
            "light": {
                "device": "device_1",
                "command": "set_color",
            }
        }
    }

    server = HTTPServer(
        host="127.0.0.1",
        port=9999,
        dispatcher=dispatcher,
        device_registry=registry,
    )

    client = TestClient(server._app)

    # Initially fetch metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text

    assert "playsem_dispatcher_queue_depth" in text
    assert "playsem_dispatch_latency_ms_sum" in text
    assert "playsem_dispatch_latency_ms_count" in text

    # Dispatch an effect
    success = dispatcher.dispatch_effect("light", {"color": "red"})
    assert success

    # Fetch metrics again and check that dispatch_count is updated
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text

    # Count should be 1
    assert "playsem_dispatch_latency_ms_count 1" in text
