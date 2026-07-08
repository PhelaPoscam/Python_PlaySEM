"""
Unit tests for mock sensory devices.

Verifies each MockDeviceBase subclass correctly tracks state transitions,
handles commands, and maintains command history — essential for testing
without physical hardware.
"""

import pytest
from playsem.drivers.mock_driver import (
    MockDeviceBase,
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
    MockConnectivityDriver,
)


# -- MockDeviceBase -------------------------------------------------------


class TestMockDeviceBase:
    def test_initial_state_empty(self):
        dev = MockDeviceBase("test_device")
        assert dev.device_id == "test_device"
        assert dev.state == {}
        assert dev.command_history == []

    def test_send_command_updates_state_and_history(self):
        dev = MockDeviceBase("test_device")
        dev.send_command("set_power", {"on": True})
        assert dev.state["on"] is True
        assert len(dev.command_history) == 1
        assert dev.command_history[0]["command"] == "set_power"

    def test_reset_clears_state_and_history(self):
        dev = MockDeviceBase("test_device")
        dev.send_command("set_power", {"on": True})
        dev.reset()
        assert dev.state == {}
        assert dev.command_history == []

    def test_get_state_returns_copy(self):
        dev = MockDeviceBase("test_device")
        dev.send_command("foo", {"x": 1})
        state = dev.get_state()
        state["x"] = 999  # mutate copy
        assert dev.state["x"] == 1  # original untouched

    def test_clear_history_leaves_state(self):
        dev = MockDeviceBase("test_device")
        dev.send_command("foo", {"x": 1})
        dev.clear_history()
        assert dev.command_history == []
        assert dev.state == {"x": 1}

    def test_properties_stored(self):
        dev = MockDeviceBase("dev", properties={"delay": 42, "color": "red"})
        assert dev.delay == 42
        assert dev.properties["color"] == "red"

    def test_delay_defaults_to_zero(self):
        dev = MockDeviceBase("dev")
        assert dev.delay == 0


# -- MockLightDevice ------------------------------------------------------


class TestMockLightDevice:
    def test_initial_state_zeros(self):
        dev = MockLightDevice("led1")
        assert dev.state == {"r": 0, "g": 0, "b": 0, "brightness": 0}

    def test_set_brightness(self):
        dev = MockLightDevice("led1")
        dev.set_brightness(200)
        assert dev.state["brightness"] == 200

    def test_set_brightness_clamped(self):
        dev = MockLightDevice("led1")
        dev.set_brightness(300)
        assert dev.state["brightness"] == 255
        dev.set_brightness(-10)
        assert dev.state["brightness"] == 0

    def test_set_color(self):
        dev = MockLightDevice("led1")
        dev.set_color(100, 150, 200)
        assert dev.state["r"] == 100
        assert dev.state["g"] == 150
        assert dev.state["b"] == 200

    def test_set_color_clamped(self):
        dev = MockLightDevice("led1")
        dev.set_color(300, -5, 128)
        assert dev.state["r"] == 255
        assert dev.state["g"] == 0
        assert dev.state["b"] == 128

    def test_send_command_set_brightness_updates_state(self):
        """Known commands use typed setters (not base class), so state
        changes but command_history is not appended."""
        dev = MockLightDevice("led1")
        dev.send_command("set_brightness", {"brightness": 128})
        assert dev.state["brightness"] == 128

    def test_send_command_set_color_updates_state(self):
        dev = MockLightDevice("led1")
        dev.send_command("set_color", {"r": 10, "g": 20, "b": 30})
        assert dev.state["r"] == 10
        assert dev.state["g"] == 20
        assert dev.state["b"] == 30

    def test_send_command_unknown_falls_back_to_base(self):
        dev = MockLightDevice("led1")
        dev.send_command("some_other_cmd", {"foo": "bar"})
        assert dev.state["foo"] == "bar"
        assert len(dev.command_history) == 1  # base class records it


# -- MockWindDevice -------------------------------------------------------


class TestMockWindDevice:
    def test_initial_state(self):
        dev = MockWindDevice("fan1")
        assert dev.state == {"speed": 0, "direction": "forward"}

    def test_set_speed(self):
        dev = MockWindDevice("fan1")
        dev.set_speed(75)
        assert dev.state["speed"] == 75

    def test_set_speed_clamped(self):
        dev = MockWindDevice("fan1")
        dev.set_speed(150)
        assert dev.state["speed"] == 100
        dev.set_speed(-5)
        assert dev.state["speed"] == 0

    def test_set_direction(self):
        dev = MockWindDevice("fan1")
        dev.set_direction("reverse")
        assert dev.state["direction"] == "reverse"

    def test_send_command_set_speed_updates_state(self):
        dev = MockWindDevice("fan1")
        dev.send_command("set_speed", {"speed": 42})
        assert dev.state["speed"] == 42

    def test_send_command_set_direction_updates_state(self):
        dev = MockWindDevice("fan1")
        dev.send_command("set_direction", {"direction": "reverse"})
        assert dev.state["direction"] == "reverse"

    def test_reset_clears_state(self):
        """Base class reset() sets state to {}, not the __init__ defaults."""
        dev = MockWindDevice("fan1")
        dev.set_speed(80)
        dev.set_direction("reverse")
        dev.reset()
        assert dev.state == {}
        assert dev.command_history == []


# -- MockVibrationDevice --------------------------------------------------


class TestMockVibrationDevice:
    def test_initial_state(self):
        dev = MockVibrationDevice("haptic1")
        assert dev.state == {"intensity": 0, "duration": 0}

    def test_set_intensity(self):
        dev = MockVibrationDevice("haptic1")
        dev.set_intensity(85)
        assert dev.state["intensity"] == 85

    def test_set_intensity_clamped(self):
        dev = MockVibrationDevice("haptic1")
        dev.set_intensity(200)
        assert dev.state["intensity"] == 100
        dev.set_intensity(-10)
        assert dev.state["intensity"] == 0

    def test_set_duration(self):
        dev = MockVibrationDevice("haptic1")
        dev.set_duration(500)
        assert dev.state["duration"] == 500

    def test_set_duration_non_negative(self):
        dev = MockVibrationDevice("haptic1")
        dev.set_duration(-100)
        assert dev.state["duration"] == 0

    def test_send_command_set_intensity_updates_state(self):
        dev = MockVibrationDevice("haptic1")
        dev.send_command("set_intensity", {"intensity": 60})
        assert dev.state["intensity"] == 60

    def test_send_command_set_duration_updates_state(self):
        dev = MockVibrationDevice("haptic1")
        dev.send_command("set_duration", {"duration": 300})
        assert dev.state["duration"] == 300

    def test_multiple_commands_update_state_correctly(self):
        """State reflects the last value set for each parameter."""
        dev = MockVibrationDevice("haptic1")
        dev.send_command("set_intensity", {"intensity": 50})
        dev.send_command("set_duration", {"duration": 200})
        dev.send_command("set_intensity", {"intensity": 80})
        assert dev.state["intensity"] == 80
        assert dev.state["duration"] == 200


# -- MockScentDevice ------------------------------------------------------


class TestMockScentDevice:
    def test_initial_state(self):
        dev = MockScentDevice("scent1")
        assert dev.state == {"scent": None, "intensity": 0}

    def test_set_scent(self):
        dev = MockScentDevice("scent1")
        dev.set_scent("ocean", 60)
        assert dev.state["scent"] == "ocean"
        assert dev.state["intensity"] == 60

    def test_set_scent_intensity_clamped(self):
        dev = MockScentDevice("scent1")
        dev.set_scent("rose", 150)
        assert dev.state["intensity"] == 100
        dev.set_scent("rose", -10)
        assert dev.state["intensity"] == 0

    def test_stop_scent(self):
        dev = MockScentDevice("scent1")
        dev.set_scent("coffee", 80)
        dev.stop_scent()
        assert dev.state["scent"] is None
        assert dev.state["intensity"] == 0

    def test_send_command_set_scent_updates_state(self):
        dev = MockScentDevice("scent1")
        dev.send_command("set_scent", {"scent": "vanilla", "intensity": 40})
        assert dev.state["scent"] == "vanilla"
        assert dev.state["intensity"] == 40

    def test_send_command_stop_scent_updates_state(self):
        dev = MockScentDevice("scent1")
        dev.set_scent("pine", 70)
        dev.send_command("stop_scent", {})
        assert dev.state["scent"] is None
        assert dev.state["intensity"] == 0

    def test_send_command_unknown_falls_back(self):
        dev = MockScentDevice("scent1")
        dev.send_command("diffuse", {"scent": "citrus"})
        assert dev.state["scent"] == "citrus"
        assert len(dev.command_history) == 1


# -- MockConnectivityDriver ------------------------------------------------


class TestMockConnectivityDriver:
    def test_initial_state_disconnected(self):
        driver = MockConnectivityDriver()
        assert driver._connected is False
        assert driver.command_history == []

    @pytest.mark.asyncio
    async def test_connect(self):
        driver = MockConnectivityDriver()
        result = await driver.connect()
        assert result is True
        assert await driver.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self):
        driver = MockConnectivityDriver()
        await driver.connect()
        result = await driver.disconnect()
        assert result is True
        assert await driver.is_connected() is False

    @pytest.mark.asyncio
    async def test_send_command_journals_and_formats_json(self):
        driver = MockConnectivityDriver(data_format="json")
        await driver.send_command("dev1", "set_power", {"level": 5})
        assert len(driver.command_history) == 1
        entry = driver.command_history[0]
        assert entry["device_id"] == "dev1"
        assert entry["command"] == "set_power"
        assert entry["params"]["level"] == 5
        assert '"command": "set_power"' in entry["payload"]

    @pytest.mark.asyncio
    async def test_send_command_formats_xml(self):
        driver = MockConnectivityDriver(data_format="xml")
        await driver.send_command("dev1", "set_power", {"level": 5})
        entry = driver.command_history[0]
        assert "<command>" in entry["payload"]
        assert "<name>set_power</name>" in entry["payload"]

    @pytest.mark.asyncio
    async def test_clear_history(self):
        driver = MockConnectivityDriver()
        await driver.send_command("dev1", "cmd", {})
        driver.clear_history()
        assert driver.command_history == []

    @pytest.mark.asyncio
    async def test_register_device_forwards_commands(self):
        driver = MockConnectivityDriver()
        light = MockLightDevice("led1")
        driver.register_device("led1", light)
        await driver.send_command(
            "led1", "set_brightness", {"brightness": 200}
        )
        assert light.state["brightness"] == 200

    def test_get_capabilities_light_device(self):
        driver = MockConnectivityDriver()
        caps = driver.get_capabilities("light_device_01")
        assert caps is not None
        assert caps["device_type"] == "MockLightDevice"

    def test_get_capabilities_wind_device(self):
        driver = MockConnectivityDriver()
        caps = driver.get_capabilities("wind_machine")
        assert caps["device_type"] == "MockWindDevice"

    def test_get_capabilities_vibration_device(self):
        driver = MockConnectivityDriver()
        caps = driver.get_capabilities("haptic_vibrator")
        assert caps["device_type"] == "MockVibrationDevice"

    def test_get_capabilities_scent_device(self):
        driver = MockConnectivityDriver()
        caps = driver.get_capabilities("smell_generator")
        assert caps["device_type"] == "MockScentDevice"

    def test_get_capabilities_unknown_device(self):
        driver = MockConnectivityDriver()
        caps = driver.get_capabilities("random_unknown_device")
        assert caps["device_type"] == "MockDevice"

    def test_get_driver_type(self):
        driver = MockConnectivityDriver()
        assert driver.get_driver_type() == "mock"

    def test_get_interface_name(self):
        driver = MockConnectivityDriver(interface_name="my_mock")
        assert driver.get_interface_name() == "my_mock"
