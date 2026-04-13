import asyncio
from unittest.mock import MagicMock

import pytest

from playsem.drivers.mqtt_driver import MQTTDriver
from playsem.drivers.retry_policy import RetryPolicy


class _AsyncNoop:
    async def __call__(self, *args, **kwargs):
        return None


def test_retry_policy_delays_are_bounded():
    policy = RetryPolicy(
        max_attempts=4,
        initial_delay=0.5,
        max_delay=1.0,
        backoff_factor=2.0,
    )

    assert policy.delays() == [0.5, 1.0, 1.0]


def test_mqtt_connect_retries_and_succeeds():
    driver = MQTTDriver(
        interface_name="mqtt_test",
        broker="localhost",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0, max_delay=0),
        auto_reconnect=False,
    )
    driver.client.connect = MagicMock(side_effect=[RuntimeError("fail"), None])
    driver.client.loop_start = MagicMock()

    assert driver.connect() is True
    assert driver.client.connect.call_count == 2
    driver.client.loop_start.assert_called_once()


def test_mqtt_connect_exhausts_retry_budget():
    driver = MQTTDriver(
        interface_name="mqtt_test",
        broker="localhost",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0, max_delay=0),
        auto_reconnect=False,
    )
    driver.client.connect = MagicMock(side_effect=RuntimeError("fail"))

    assert driver.connect() is False
    assert driver.client.connect.call_count == 3


def test_mqtt_reconnect_loop_updates_attempts():
    driver = MQTTDriver(
        interface_name="mqtt_test",
        broker="localhost",
        retry_policy=RetryPolicy(max_attempts=2, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )
    driver.client.reconnect = MagicMock(
        side_effect=[RuntimeError("fail"), None]
    )

    driver._reconnect_loop()

    assert driver._reconnect_attempts == 2
    assert driver._last_reconnect_error is None


def test_serial_connect_retries(monkeypatch):
    import playsem.drivers.serial_driver as serial_module

    if not serial_module.SERIAL_AVAILABLE:
        pytest.skip("pyserial not available")

    driver = serial_module.SerialDriver(
        port="COM_TEST",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0, max_delay=0),
    )
    monkeypatch.setattr(
        driver,
        "open_connection",
        MagicMock(side_effect=[False, True]),
    )

    assert driver.connect() is True
    assert driver.open_connection.call_count == 2
    assert driver._last_reconnect_error is None


@pytest.mark.asyncio
async def test_bluetooth_connect_retries(monkeypatch):
    import playsem.drivers.bluetooth_driver as bluetooth_module

    if not bluetooth_module.BLEAK_AVAILABLE:
        pytest.skip("bleak not available")

    attempts = {"count": 0}

    class FakeBleakClient:
        def __init__(self, address, disconnected_callback=None, timeout=10.0):
            self.address = address
            self.disconnected_callback = disconnected_callback
            self.timeout = timeout
            self.is_connected = False
            self.services = []

        async def connect(self):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("first attempt fails")
            self.is_connected = True

        async def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(bluetooth_module, "BleakClient", FakeBleakClient)

    driver = bluetooth_module.BluetoothDriver(
        address="AA:BB:CC:DD:EE:FF",
        retry_policy=RetryPolicy(max_attempts=3, initial_delay=0, max_delay=0),
        auto_reconnect=False,
    )

    assert await driver.connect(timeout=0.01) is True
    assert attempts["count"] == 2
    assert driver._last_reconnect_error is None


@pytest.mark.asyncio
async def test_bluetooth_disconnect_schedules_reconnect(monkeypatch):
    import playsem.drivers.bluetooth_driver as bluetooth_module

    if not bluetooth_module.BLEAK_AVAILABLE:
        pytest.skip("bleak not available")

    driver = bluetooth_module.BluetoothDriver(
        address="AA:BB:CC:DD:EE:FF",
        retry_policy=RetryPolicy(max_attempts=1, initial_delay=0, max_delay=0),
        auto_reconnect=True,
    )

    reconnect_called = {"flag": False}

    async def fake_attempt_reconnect():
        reconnect_called["flag"] = True

    monkeypatch.setattr(driver, "_attempt_reconnect", fake_attempt_reconnect)

    driver._handle_disconnect(client=None)
    await asyncio.sleep(0)

    assert reconnect_called["flag"] is True
