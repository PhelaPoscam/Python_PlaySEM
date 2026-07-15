import pytest
import asyncio
from playsem import DeviceRegistry, DeviceManager
from playsem.drivers.base_driver import BaseDriver
from playsem.protocol_servers.http_server import HTTPServer
from playsem.effect_dispatcher import EffectDispatcher


class FailingDriver(BaseDriver):
    def get_driver_type(self) -> str:
        return "failing"

    def get_interface_name(self) -> str:
        return "failing_interface"

    def is_connected(self) -> bool:
        return True

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def send_command(self, device_id: str, command: str, params: dict) -> bool:
        raise ValueError("Simulated connection failure")


class SuccessfulDriver(BaseDriver):
    def get_driver_type(self) -> str:
        return "successful"

    def get_interface_name(self) -> str:
        return "successful_interface"

    def is_connected(self) -> bool:
        return True

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def send_command(self, device_id: str, command: str, params: dict) -> bool:
        return True


@pytest.mark.asyncio
async def test_circuit_breaker_registry_sync():
    registry = DeviceRegistry()
    driver = FailingDriver()

    manager = DeviceManager(
        connectivity_driver=driver,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_reset_timeout=0.1,
        device_registry=registry,
    )

    # Check initial state in registry (it will be registered automatically upon first circuit state access)
    device = registry.get_device("device_1")
    assert device is None

    # First failure
    success = await manager.async_send_command("device_1", "turn_on", {})
    assert not success

    device = registry.get_device("device_1")
    assert device is not None
    assert device.circuit_state == "closed"
    assert device.consecutive_failures == 1
    assert "Simulated connection failure" in device.last_error_message

    # Second failure - should open the circuit
    success = await manager.async_send_command("device_1", "turn_on", {})
    assert not success

    assert device.circuit_state == "open"
    assert device.consecutive_failures == 2

    # Verify HTTP endpoint returns this metadata
    dispatcher = EffectDispatcher(manager)
    server = HTTPServer(
        host="127.0.0.1",
        port=9999,
        dispatcher=dispatcher,
        device_registry=registry,
    )

    # Call the router endpoint handler directly
    from fastapi.testclient import TestClient

    client = TestClient(server._app)

    response = client.get("/api/devices")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1

    target_device = None
    for d in data["devices"]:
        if d["device_id"] == "device_1":
            target_device = d
            break

    assert target_device is not None
    assert target_device["circuit_state"] == "open"
    assert target_device["consecutive_failures"] == 2
    assert "Simulated connection failure" in target_device["last_error_message"]

    # Now transition to success with a successful driver
    success_driver = SuccessfulDriver()
    manager.connectivity_driver = success_driver

    # Wait for reset timeout
    await asyncio.sleep(0.15)

    # Sending command should succeed and close the circuit
    success = await manager.async_send_command("device_1", "turn_on", {})
    assert success

    assert device.circuit_state == "closed"
    assert device.consecutive_failures == 0
    assert device.last_error_message is None

    # Check http response again
    response = client.get("/api/devices")
    assert response.status_code == 200
    data = response.json()
    for d in data["devices"]:
        if d["device_id"] == "device_1":
            target_device = d

    assert target_device["circuit_state"] == "closed"
    assert target_device["consecutive_failures"] == 0
    assert target_device["last_error_message"] is None
