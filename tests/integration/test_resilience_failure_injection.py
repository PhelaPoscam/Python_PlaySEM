import asyncio
from unittest.mock import MagicMock

import pytest

import paho.mqtt.client as mqtt

from playsem.drivers.mqtt_driver import MQTTDriver
from playsem.drivers.retry_policy import RetryPolicy


class _PublishResult:
    def __init__(self, rc: int):
        self.rc = rc


@pytest.mark.integration
def test_mqtt_broker_disconnect_recovery_slo():
    """Failure-injection: broker disconnect storms keep >=99% recovery."""
    driver = MQTTDriver(
        interface_name="mqtt_resilience",
        broker="localhost",
        retry_policy=RetryPolicy(max_attempts=2, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )

    total_events = 100
    recovered = 0

    for event in range(total_events):
        if event == 0:
            # Inject one unrecoverable event to validate threshold behavior.
            driver.client.reconnect = MagicMock(
                side_effect=[RuntimeError("broker down"), RuntimeError("down")]
            )
        else:
            driver.client.reconnect = MagicMock(side_effect=[None])

        driver._reconnect_loop()
        if driver._last_reconnect_error is None:
            recovered += 1

    reconnect_success_rate = recovered / total_events
    assert reconnect_success_rate >= 0.99


@pytest.mark.integration
def test_mqtt_command_loss_budget_during_transient_disconnect():
    """Failure-injection: command loss remains <=1 during transient disconnect."""
    driver = MQTTDriver(
        interface_name="mqtt_resilience",
        broker="localhost",
        retry_policy=RetryPolicy(max_attempts=2, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )

    driver._is_connected = True

    def publish_side_effect(*args, **kwargs):
        if not driver._is_connected:
            return _PublishResult(rc=mqtt.MQTT_ERR_NO_CONN)
        return _PublishResult(rc=mqtt.MQTT_ERR_SUCCESS)

    def reconnect_side_effect():
        driver._is_connected = True

    driver.client.publish = MagicMock(side_effect=publish_side_effect)
    driver.client.reconnect = MagicMock(side_effect=reconnect_side_effect)

    command_loss = 0

    # Simulate a transient disconnect window.
    driver._is_connected = False
    if not driver.send_command("devices/test", "pulse", {"intensity": 100}):
        command_loss += 1

    # Recover and continue command flow.
    driver._reconnect_loop()

    for _ in range(49):
        if not driver.send_command(
            "devices/test", "pulse", {"intensity": 100}
        ):
            command_loss += 1

    assert command_loss <= 1


@pytest.mark.integration
def test_serial_port_unavailable_then_reconnect(monkeypatch):
    """Failure-injection: serial port unavailable first, then reconnects."""
    import playsem.drivers.serial_driver as serial_module

    if not serial_module.SERIAL_AVAILABLE:
        pytest.skip("pyserial not available")

    driver = serial_module.SerialDriver(
        port="COM_TEST",
        retry_policy=RetryPolicy(max_attempts=1, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )

    # First auto-reconnect fails (port unavailable), second succeeds.
    open_attempts = [False, True]

    def open_connection_side_effect():
        result = open_attempts.pop(0)
        if result:
            driver._is_connected = True
            driver._serial = object()
        else:
            driver._is_connected = False
            driver._serial = None
        return result

    monkeypatch.setattr(driver, "open_connection", open_connection_side_effect)
    monkeypatch.setattr(driver, "send_bytes", MagicMock(return_value=True))

    loss = 0
    if not driver.send_command("serial_device", "set_speed", {"speed": 10}):
        loss += 1

    if not driver.send_command("serial_device", "set_speed", {"speed": 10}):
        loss += 1

    assert loss <= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bluetooth_drop_and_reconnect(monkeypatch):
    """Failure-injection: BLE drop schedules reconnect and recovers."""
    import playsem.drivers.bluetooth_driver as bluetooth_module

    if not bluetooth_module.BLEAK_AVAILABLE:
        pytest.skip("bleak not available")

    class FakeBleakClient:
        def __init__(self, address, disconnected_callback=None, timeout=10.0):
            self.address = address
            self.disconnected_callback = disconnected_callback
            self.timeout = timeout
            self.is_connected = False
            self.services = []

        async def connect(self):
            self.is_connected = True

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(bluetooth_module, "BleakClient", FakeBleakClient)

    driver = bluetooth_module.BluetoothDriver(
        address="AA:BB:CC:DD:EE:FF",
        retry_policy=RetryPolicy(max_attempts=2, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )

    assert await driver.connect(timeout=0.01) is True

    # Inject drop and confirm reconnect task executes.
    reconnect_called = {"value": False}

    async def fake_attempt_reconnect():
        reconnect_called["value"] = True
        driver._is_connected = True

    monkeypatch.setattr(driver, "_attempt_reconnect", fake_attempt_reconnect)

    driver._is_connected = False
    driver._handle_disconnect(client=None)
    await asyncio.sleep(0)

    assert reconnect_called["value"] is True
    assert await driver.is_connected() is True
