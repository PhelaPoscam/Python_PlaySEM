import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path before imports/collection
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def pytest_configure(config):
    """Guarantee sys.path contains the project root during collection."""
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))


def pytest_collection_modifyitems(items):
    """Automatically mark network integration tests."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        if "integration" in parts or "protocols" in parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture
async def playsem_system(tmp_path):
    """
    High-fidelity system orchestrator fixture.
    Boots DeviceManager, EffectDispatcher, and MQTTServer.
    """
    import socket
    import asyncio
    from playsem import DeviceManager, EffectDispatcher
    from playsem.drivers.mock_driver import MockConnectivityDriver
    from playsem.protocol_servers import MQTTServer
    from playsem.config.loader import ConfigLoader

    # 1. Setup temporary config
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    devices_file = config_dir / "devices.yaml"
    devices_file.write_text(
        """
devices:
  - deviceId: vibration_device
    driver_type: mock
    connectivityInterface: mock_interface
  - deviceId: light_device
    driver_type: mock
    connectivityInterface: mock_interface
connectivityInterfaces:
  - name: mock_interface
    protocol: mock
    """
    )

    effects_file = config_dir / "effects.yaml"
    effects_file.write_text(
        "effects: {}"
    )  # Use empty dict to allow defaults or define them explicitly

    protocols_file = config_dir / "protocols.yaml"
    protocols_file.write_text("protocols: []")

    # 2. Initialize Core Components
    loader = ConfigLoader(
        devices_path=str(devices_file),
        effects_path=str(effects_file),
        protocols_path=str(protocols_file),
    )

    # Mock driver for observability
    mock_driver = MockConnectivityDriver(interface_name="mock_interface")

    # DeviceManager with the mock driver and loader
    manager = DeviceManager(config_loader=loader, drivers=[mock_driver])
    await manager.start_async_workers()

    # Dispatcher
    dispatcher = EffectDispatcher(device_manager=manager)

    # 3. Start MQTT Server on free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    mqtt_port = sock.getsockname()[1]
    sock.close()

    mqtt_server = MQTTServer(dispatcher=dispatcher, host="127.0.0.1", port=mqtt_port)
    mqtt_server.start()
    await asyncio.wait_for(mqtt_server.wait_until_ready(), timeout=5.0)

    class SystemBundle:
        def __init__(self):
            self.manager = manager
            self.dispatcher = dispatcher
            self.mock_driver = mock_driver
            self.mqtt_server = mqtt_server
            self.mqtt_port = mqtt_port

    bundle = SystemBundle()
    try:
        yield bundle
    finally:
        # Teardown — always runs so async workers don't leak across tests.
        mqtt_server.stop()
        try:
            await manager.stop_async_workers()
        except Exception:
            pass  # ponytail: swallow teardown errors, log when tests are stable
