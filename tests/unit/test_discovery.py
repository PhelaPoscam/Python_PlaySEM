import pytest
import asyncio
from playsem import DeviceRegistry, DeviceManager, BaseDiscovery, UPnPDiscovery


class MockDiscoveryScanner(BaseDiscovery):
    def __init__(self, interface_name: str, devices_to_return: list):
        self.interface_name = interface_name
        self.devices_to_return = devices_to_return

    def get_interface_name(self) -> str:
        return self.interface_name

    async def discover_devices(self) -> list:
        # Simulate slight delay to test parallel execution
        await asyncio.sleep(0.01)
        return self.devices_to_return


@pytest.mark.asyncio
async def test_device_manager_discovery():
    registry = DeviceRegistry()

    mock_devices_1 = [
        {
            "id": "dev_ble_1",
            "name": "BLE Device 1",
            "type": "vibrator",
            "address": "AA:BB:CC:11:22:33",
            "protocols": ["bluetooth"],
            "metadata": {"rssi": -65},
        }
    ]
    mock_devices_2 = [
        {
            "id": "dev_serial_1",
            "name": "Serial Device 1",
            "type": "light",
            "address": "COM3",
            "protocols": ["serial"],
            "metadata": {"baud": 9600},
        }
    ]

    scanner_ble = MockDiscoveryScanner("bluetooth", mock_devices_1)
    scanner_serial = MockDiscoveryScanner("serial", mock_devices_2)

    # Initialize DeviceManager
    manager = DeviceManager(
        connectivity_driver=MockDiscoveryScanner(
            "dummy", []
        ),  # Just to place it in single driver mode
        device_registry=registry,
    )

    # Register our mock scanners
    manager.register_scanner(scanner_ble)
    manager.register_scanner(scanner_serial)

    # Execute discovery
    discovered = await manager.discover_all_devices()

    # We should get a flat list of 2 discovered devices
    assert len(discovered) == 2
    ids = [d["id"] for d in discovered]
    assert "dev_ble_1" in ids
    assert "dev_serial_1" in ids

    # The devices must be auto-registered in our DeviceRegistry
    ble_device = registry.get_device("dev_ble_1")
    assert ble_device is not None
    assert ble_device.name == "BLE Device 1"
    assert ble_device.type == "vibrator"
    assert ble_device.address == "AA:BB:CC:11:22:33"
    assert ble_device.metadata["rssi"] == -65

    serial_device = registry.get_device("dev_serial_1")
    assert serial_device is not None
    assert serial_device.name == "Serial Device 1"
    assert serial_device.type == "light"
    assert serial_device.address == "COM3"
    assert serial_device.metadata["baud"] == 9600


@pytest.mark.asyncio
async def test_upnp_discovery_timeout():
    # Since there are probably no actual UPnP devices in the test environment,
    # calling UPnPDiscovery.discover_devices() should time out after 2.0s and return empty list.
    scanner = UPnPDiscovery()
    assert scanner.get_interface_name() == "upnp"

    # We can mock socket.socket to return dummy SSDP responses to verify parser logic
    import socket
    from unittest.mock import MagicMock, patch

    mock_socket = MagicMock()
    # Configure mock socket to return one packet and then raise timeout
    mock_socket.recvfrom.side_effect = [
        (
            b"HTTP/1.1 200 OK\r\n"
            b"LOCATION: http://192.168.1.100:8080/description.xml\r\n"
            b"SERVER: PlaySEM-UPnP-Test/1.0\r\n"
            b"\r\n",
            ("192.168.1.100", 1900),
        ),
        socket.timeout("timeout"),
    ]

    with patch("socket.socket", return_value=mock_socket):
        devices = await scanner.discover_devices()
        assert len(devices) == 1
        dev = devices[0]
        assert dev["id"] == "upnp_192_168_1_100"
        assert dev["name"] == "PlaySEM-UPnP-Test/1.0"
        assert dev["address"] == "http://192.168.1.100:8080/description.xml"
        assert dev["protocols"] == ["upnp"]
        assert dev["metadata"]["ip"] == "192.168.1.100"
