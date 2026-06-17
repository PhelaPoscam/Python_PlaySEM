import pytest
import asyncio
import time
from playsem import DeviceManager, DeviceRegistry
from playsem.drivers.base_driver import BaseDriver


class CircuitTestDriver(BaseDriver):
    def __init__(self):
        self.should_fail = False

    def get_driver_type(self) -> str:
        return "circuit_test"

    def get_interface_name(self) -> str:
        return "circuit_test_interface"

    def is_connected(self) -> bool:
        return True

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def send_command(
        self, device_id: str, command: str, params: dict
    ) -> bool:
        if self.should_fail:
            raise ValueError("Simulated failure")
        return True


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_closed():
    """Verify that a successful command in half-open state closes the circuit."""
    registry = DeviceRegistry()
    driver = CircuitTestDriver()
    manager = DeviceManager(
        connectivity_driver=driver,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_reset_timeout=0.05,
        device_registry=registry,
    )

    # Trigger 2 failures to open the circuit
    driver.should_fail = True
    assert not await manager.async_send_command("dev_1", "cmd", {})
    assert not await manager.async_send_command("dev_1", "cmd", {})

    state = manager._get_circuit_state("dev_1")
    assert state.state == "open"
    assert state.failures == 2

    # Wait for the reset timeout to expire
    await asyncio.sleep(0.06)

    # Next request should move it to half-open and since the probe succeeds, it should close
    driver.should_fail = False
    success = await manager.async_send_command("dev_1", "cmd", {})
    assert success

    # Verify state transitions back to closed
    assert state.state == "closed"
    assert state.failures == 0
    assert state.last_error is None


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_to_open_on_first_failure():
    """Verify that a single failure in half-open state immediately re-opens the circuit, ignoring the threshold."""
    registry = DeviceRegistry()
    driver = CircuitTestDriver()
    manager = DeviceManager(
        connectivity_driver=driver,
        circuit_breaker_failure_threshold=3,  # Set threshold to 3
        circuit_breaker_reset_timeout=0.05,
        device_registry=registry,
    )

    # Trigger 3 failures to open the circuit
    driver.should_fail = True
    assert not await manager.async_send_command("dev_1", "cmd", {})
    assert not await manager.async_send_command("dev_1", "cmd", {})
    assert not await manager.async_send_command("dev_1", "cmd", {})

    state = manager._get_circuit_state("dev_1")
    assert state.state == "open"
    assert state.failures == 3

    # Wait for reset timeout
    await asyncio.sleep(0.06)

    # Next request will be allowed as a probe, but it will fail.
    # It should immediately move back to open status on the first failure.
    driver.should_fail = True
    success = await manager.async_send_command("dev_1", "cmd", {})
    assert not success

    # Verify it went back to open state instantly
    assert state.state == "open"
    # The failures counter in half_open failure does increment to 4
    assert state.failures == 4
