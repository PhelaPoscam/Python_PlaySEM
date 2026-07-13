"""
End-to-end validation of the full PlaySEM data path.

These tests boot the complete system (DeviceManager + EffectDispatcher +
MQTTServer + MockConnectivityDriver) and verify that effects flow through
every layer correctly.
"""

import asyncio
import json
import time
import pytest
import paho.mqtt.client as mqtt
from playsem import DeviceManager, EffectDispatcher
from playsem.timeline import Timeline
from playsem.effect_metadata import (
    EffectMetadata,
    create_effect,
    create_timeline,
)
from playsem.drivers.mock_driver import MockConnectivityDriver
from playsem.protocol_servers import MQTTServer
from playsem.config.loader import ConfigLoader


@pytest.fixture
async def full_system(tmp_path, request):
    """Boot the complete PlaySEM stack with a real mock driver."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    devices_file = config_dir / "devices.yaml"
    devices_file.write_text(
        """
devices:
  - deviceId: light_device
    connectivityInterface: mock
  - deviceId: wind_device
    connectivityInterface: mock
  - deviceId: vibration_device
    connectivityInterface: mock
connectivityInterfaces:
  - name: mock
    protocol: mock
"""
    )

    effects_file = config_dir / "effects.yaml"
    effects_file.write_text(
        """
effects:
  light:
    device: light_device
    command: set_brightness
    parameters:
      - name: intensity
        mapping: {low: 64, high: 255}
        default: 128
  wind:
    device: wind_device
    command: set_speed
  vibration:
    device: vibration_device
    command: set_intensity
"""
    )

    protocols_file = config_dir / "protocols.yaml"
    protocols_file.write_text("protocols: []")

    loader = ConfigLoader(
        devices_path=str(devices_file),
        effects_path=str(effects_file),
        protocols_path=str(protocols_file),
    )

    driver = MockConnectivityDriver(interface_name="mock")
    manager = DeviceManager(drivers=[driver], config_loader=loader)
    await manager.start_async_workers()

    dispatcher = EffectDispatcher(
        device_manager=manager, effects_config_path=str(effects_file)
    )

    use_mqtt = "TestMqttPath" in request.node.nodeid
    if use_mqtt:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        mqtt_port = sock.getsockname()[1]
        sock.close()

        mqtt_server = MQTTServer(
            dispatcher=dispatcher, host="127.0.0.1", port=mqtt_port
        )
        mqtt_server.start()
        await asyncio.wait_for(mqtt_server.wait_until_ready(), timeout=5.0)
    else:
        mqtt_server = None
        mqtt_port = None

    class System:
        pass

    system = System()
    system.manager = manager
    system.dispatcher = dispatcher
    system.driver = driver
    system.mqtt_server = mqtt_server
    system.mqtt_port = mqtt_port

    yield system

    if mqtt_server:
        mqtt_server.stop()
    await manager.stop_async_workers()


class TestDirectDispatchPath:
    """Effects dispatched directly via EffectDispatcher."""

    def test_single_effect_reaches_driver(self, full_system):
        """A simple effect is dispatched and reaches the mock driver."""
        full_system.dispatcher.dispatch_effect("wind", {"speed": 75})

        assert len(full_system.driver.command_history) == 1
        cmd = full_system.driver.command_history[0]
        assert cmd["device_id"] == "wind_device"
        assert cmd["command"] == "set_speed"
        assert cmd["params"]["speed"] == 75

    def test_parameter_mapping_applied(self, full_system):
        """Parameter mappings (e.g., 'high' -> 255) are applied."""
        full_system.dispatcher.dispatch_effect("light", {"intensity": "high"})

        cmd = full_system.driver.command_history[0]
        assert cmd["params"]["intensity"] == 255

    def test_default_parameter_used(self, full_system):
        """Default parameter values are used when not provided."""
        full_system.dispatcher.dispatch_effect("light", {})

        cmd = full_system.driver.command_history[0]
        assert cmd["params"]["intensity"] == 128

    def test_multiple_effects_in_order(self, full_system):
        """Multiple effects are dispatched and recorded in order."""
        full_system.dispatcher.dispatch_effect("light", {"intensity": 50})
        full_system.dispatcher.dispatch_effect("wind", {"speed": 100})
        full_system.dispatcher.dispatch_effect(
            "vibration", {"pattern": "pulse"}
        )

        assert len(full_system.driver.command_history) == 3
        cmds = full_system.driver.command_history
        assert cmds[0]["device_id"] == "light_device"
        assert cmds[1]["device_id"] == "wind_device"
        assert cmds[2]["device_id"] == "vibration_device"

    def test_dispatch_result_has_latency(self, full_system):
        """DispatchResult includes a non-negative latency measurement."""
        result = full_system.dispatcher.dispatch_effect_result(
            "wind", {"speed": 50}
        )
        assert result.status == "dispatched"
        assert result.latency_ms >= 0


class TestTimelinePath:
    """Effects scheduled via Timeline reach the driver at correct times."""

    @pytest.mark.asyncio
    async def test_timeline_executes_all_effects(self, full_system):
        """A timeline with 3 effects executes all of them."""
        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=50, intensity=100),
            create_effect("wind", timestamp=20, duration=50, intensity=75),
            create_effect(
                "vibration", timestamp=40, duration=50, intensity=50
            ),
        )

        scheduler = Timeline(full_system.dispatcher, tick_interval=0.001)
        scheduler.load_timeline(timeline)
        await scheduler.start()

        while scheduler.is_running:
            await asyncio.sleep(0.01)
        await scheduler.stop()

        history = full_system.driver.command_history
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_timeline_effects_in_timestamp_order(self, full_system):
        """Effects from a timeline are dispatched in timestamp order."""
        dispatched_types = []

        def capture(effect):
            dispatched_types.append(effect.effect_type)

        timeline = create_timeline(
            create_effect("wind", timestamp=50, duration=50),
            create_effect("light", timestamp=0, duration=50),
            create_effect("vibration", timestamp=100, duration=50),
        )

        scheduler = Timeline(full_system.dispatcher, tick_interval=0.001)
        scheduler.load_timeline(timeline)
        scheduler.set_callbacks(on_effect=capture)
        await scheduler.start()

        while scheduler.is_running:
            await asyncio.sleep(0.01)
        await scheduler.stop()

        assert dispatched_types == ["light", "wind", "vibration"]

    @pytest.mark.asyncio
    async def test_timeline_on_complete_fires(self, full_system):
        """Timeline calls on_complete exactly once when finished."""
        complete_count = [0]

        def on_complete():
            complete_count[0] += 1

        timeline = create_timeline(
            create_effect("light", timestamp=0, duration=50)
        )

        scheduler = Timeline(full_system.dispatcher, tick_interval=0.001)
        scheduler.load_timeline(timeline)
        scheduler.set_callbacks(on_complete=on_complete)
        await scheduler.start()

        while scheduler.is_running:
            await asyncio.sleep(0.01)
        await scheduler.stop()

        assert complete_count[0] == 1


class TestMqttPath:
    """Effects sent via MQTT broker reach the driver."""

    @pytest.mark.asyncio
    async def test_mqtt_effect_reaches_driver(self, full_system):
        """Publishing an effect via MQTT results in a driver command."""
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        client.connect("127.0.0.1", full_system.mqtt_port, 60)
        client.loop_start()
        await asyncio.sleep(0.3)

        try:
            payload = json.dumps(
                {"effect_type": "vibration", "intensity": 85, "duration": 400}
            )
            client.publish("effects/vibration_device", payload)
            await asyncio.sleep(1.0)

            history = full_system.driver.command_history
            assert len(history) >= 1
            assert any(
                h["device_id"] == "vibration_device"
                and h["params"].get("intensity") == 85
                for h in history
            )
        finally:
            client.loop_stop()
            client.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_and_direct_both_arrive(self, full_system):
        """Effects from MQTT and direct dispatch both reach the driver."""
        # 1. Direct dispatch
        full_system.dispatcher.dispatch_effect("light", {"intensity": 50})

        # 2. MQTT dispatch
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        client.connect("127.0.0.1", full_system.mqtt_port, 60)
        client.loop_start()
        await asyncio.sleep(0.3)

        try:
            payload = json.dumps(
                {"effect_type": "wind", "intensity": 80, "duration": 500}
            )
            client.publish("effects/wind_device", payload)
            await asyncio.sleep(1.0)

            history = full_system.driver.command_history
            devices = [h["device_id"] for h in history]
            assert "light_device" in devices
            assert "wind_device" in devices
        finally:
            client.loop_stop()
            client.disconnect()


class TestManagedMode:
    """Managed mode queues effects and processes them on demand."""

    def test_managed_mode_queues_instead_of_sending(self, full_system):
        """In managed mode, effects are queued, not immediately dispatched."""
        full_system.dispatcher.managed_mode = True
        full_system.dispatcher.dispatch_effect("light", {"intensity": 50})

        assert full_system.dispatcher.get_queue_size() == 1
        assert len(full_system.driver.command_history) == 0

    def test_process_all_pending_drains_queue(self, full_system):
        """process_all_pending dispatches all queued effects."""
        full_system.dispatcher.managed_mode = True
        full_system.dispatcher.dispatch_effect("light", {"intensity": 10})
        full_system.dispatcher.dispatch_effect("wind", {"speed": 20})

        outcomes = full_system.dispatcher.process_all_pending()
        assert len(outcomes) == 2
        assert full_system.dispatcher.get_queue_size() == 0
        assert len(full_system.driver.command_history) == 2


class TestCircuitBreaker:
    """Circuit breaker protects devices from cascading failures."""

    def test_circuit_opens_after_failures(self, full_system):
        """After threshold failures, circuit opens and blocks commands."""
        from unittest.mock import patch

        # Enable circuit breaker
        full_system.manager.circuit_breaker_failure_threshold = 2

        with patch.object(
            full_system.driver, "send_command", return_value=False
        ):
            full_system.dispatcher.dispatch_effect("light", {"intensity": 50})
            full_system.dispatcher.dispatch_effect("light", {"intensity": 50})

        info = full_system.manager.get_circuit_info("light_device")
        assert info["state"] == "open"

        # Third command should be blocked
        result = full_system.dispatcher.dispatch_effect("light", {})
        assert result is False
