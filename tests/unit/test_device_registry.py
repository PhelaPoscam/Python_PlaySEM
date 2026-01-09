"""
Unit tests for Device Registry

Tests the core functionality of the central device registry:
- Device registration from multiple protocols
- Cross-protocol device visibility
- Query operations (by protocol, type, capability)
- Event notifications
- Multi-protocol device merging
"""

import pytest
from playsem import DeviceRegistry, DeviceInfo


class TestDeviceRegistry:
    """Test Device Registry core functionality."""

    def setup_method(self):
        """Create a fresh registry for each test."""
        self.registry = DeviceRegistry()

    def test_register_device_mqtt(self):
        """Test registering a device from MQTT protocol."""
        device_data = {
            "id": "mqtt_light_001",
            "name": "MQTT Light",
            "type": "light",
            "address": "192.168.1.100",
            "protocols": ["mqtt"],
            "capabilities": ["light", "color"],
        }

        device = self.registry.register_device(
            device_data, source_protocol="mqtt"
        )

        assert device.id == "mqtt_light_001"
        assert device.name == "MQTT Light"
        assert device.type == "light"
        assert "mqtt" in device.protocols
        assert device.source_protocol == "mqtt"

    def test_register_device_websocket(self):
        """Test registering a device from WebSocket protocol."""
        device_data = {
            "id": "ws_vibration_001",
            "name": "WS Vibration",
            "type": "vibration",
            "address": "COM3",
            "protocols": ["websocket"],
            "capabilities": ["vibration"],
        }

        device = self.registry.register_device(
            device_data, source_protocol="websocket"
        )

        assert device.id == "ws_vibration_001"
        assert "websocket" in device.protocols
        assert device.source_protocol == "websocket"

    def test_get_all_devices_cross_protocol(self):
        """Test that devices from different protocols are all visible."""
        # Register MQTT device
        mqtt_device = {
            "id": "mqtt_001",
            "name": "MQTT Device",
            "type": "light",
            "address": "192.168.1.100",
            "protocols": ["mqtt"],
        }
        self.registry.register_device(mqtt_device, source_protocol="mqtt")

        # Register WebSocket device
        ws_device = {
            "id": "ws_001",
            "name": "WebSocket Device",
            "type": "vibration",
            "address": "COM3",
            "protocols": ["websocket"],
        }
        self.registry.register_device(ws_device, source_protocol="websocket")

        # Query all devices - should see both!
        all_devices = self.registry.get_all_devices()

        assert len(all_devices) == 2
        device_ids = [d.id for d in all_devices]
        assert "mqtt_001" in device_ids
        assert "ws_001" in device_ids

    def test_get_devices_by_protocol(self):
        """Test querying devices by specific protocol."""
        # Register devices with different protocols
        self.registry.register_device(
            {
                "id": "mqtt_001",
                "name": "MQTT Device",
                "type": "light",
                "address": "addr1",
            },
            source_protocol="mqtt",
        )
        self.registry.register_device(
            {
                "id": "ws_001",
                "name": "WebSocket Device",
                "type": "vibration",
                "address": "addr2",
            },
            source_protocol="websocket",
        )

        # Query MQTT devices
        mqtt_devices = self.registry.get_devices_by_protocol("mqtt")
        assert len(mqtt_devices) == 1
        assert mqtt_devices[0].id == "mqtt_001"

        # Query WebSocket devices
        ws_devices = self.registry.get_devices_by_protocol("websocket")
        assert len(ws_devices) == 1
        assert ws_devices[0].id == "ws_001"

    def test_get_devices_by_type(self):
        """Test querying devices by device type."""
        self.registry.register_device(
            {
                "id": "light_001",
                "name": "Light",
                "type": "light",
                "address": "addr1",
            },
            source_protocol="mqtt",
        )
        self.registry.register_device(
            {
                "id": "light_002",
                "name": "Another Light",
                "type": "light",
                "address": "addr2",
            },
            source_protocol="websocket",
        )
        self.registry.register_device(
            {
                "id": "vib_001",
                "name": "Vibration",
                "type": "vibration",
                "address": "addr3",
            },
            source_protocol="mqtt",
        )

        # Query light devices
        lights = self.registry.get_devices_by_type("light")
        assert len(lights) == 2
        assert all(d.type == "light" for d in lights)

        # Query vibration devices
        vibrations = self.registry.get_devices_by_type("vibration")
        assert len(vibrations) == 1
        assert vibrations[0].type == "vibration"

    def test_get_devices_by_capability(self):
        """Test querying devices by capability."""
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device 1",
                "type": "light",
                "address": "addr1",
                "capabilities": ["light", "color"],
            },
            source_protocol="mqtt",
        )
        self.registry.register_device(
            {
                "id": "dev_002",
                "name": "Device 2",
                "type": "vibration",
                "address": "addr2",
                "capabilities": ["vibration", "intensity"],
            },
            source_protocol="websocket",
        )

        # Query devices with color capability
        color_devices = self.registry.get_devices_by_capability("color")
        assert len(color_devices) == 1
        assert color_devices[0].id == "dev_001"

        # Query devices with vibration capability
        vib_devices = self.registry.get_devices_by_capability("vibration")
        assert len(vib_devices) == 1
        assert vib_devices[0].id == "dev_002"

    def test_device_update_merges_protocols(self):
        """Test that re-registering a device merges protocols."""
        device_data = {
            "id": "dev_001",
            "name": "Multi-Protocol Device",
            "type": "light",
            "address": "192.168.1.100",
        }

        # Register via MQTT
        device = self.registry.register_device(
            device_data, source_protocol="mqtt"
        )
        assert device.protocols == ["mqtt"]

        # Register same device via WebSocket
        device = self.registry.register_device(
            device_data, source_protocol="websocket"
        )
        assert "mqtt" in device.protocols
        assert "websocket" in device.protocols
        assert (
            len(self.registry.get_all_devices()) == 1
        )  # Still only one device

    def test_event_notifications(self):
        """Test that event listeners are notified of device changes."""
        events_received = []

        def listener(event_type, device):
            events_received.append((event_type, device.id))

        self.registry.add_listener(listener)

        # Register device - should trigger event
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device",
                "type": "light",
                "address": "addr",
            },
            source_protocol="mqtt",
        )

        assert len(events_received) == 1
        assert events_received[0] == ("device_registered", "dev_001")

        # Update device - should trigger event
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device",
                "type": "light",
                "address": "addr",
            },
            source_protocol="websocket",
        )

        assert len(events_received) == 2
        assert events_received[1] == ("device_updated", "dev_001")

    def test_unregister_device(self):
        """Test removing a device from registry."""
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device",
                "type": "light",
                "address": "addr",
            },
            source_protocol="mqtt",
        )

        assert self.registry.device_exists("dev_001")

        # Unregister
        result = self.registry.unregister_device("dev_001")
        assert result is True
        assert not self.registry.device_exists("dev_001")

        # Try to unregister again
        result = self.registry.unregister_device("dev_001")
        assert result is False

    def test_get_stats(self):
        """Test registry statistics."""
        self.registry.register_device(
            {
                "id": "mqtt_001",
                "name": "MQTT Light",
                "type": "light",
                "address": "addr1",
            },
            source_protocol="mqtt",
        )
        self.registry.register_device(
            {
                "id": "ws_001",
                "name": "WS Vibration",
                "type": "vibration",
                "address": "addr2",
            },
            source_protocol="websocket",
        )
        self.registry.register_device(
            {
                "id": "ws_002",
                "name": "WS Light",
                "type": "light",
                "address": "addr3",
            },
            source_protocol="websocket",
        )

        stats = self.registry.get_stats()

        assert stats["total_devices"] == 3
        assert stats["devices_by_protocol"]["mqtt"] == 1
        assert stats["devices_by_protocol"]["websocket"] == 2
        assert stats["devices_by_type"]["light"] == 2
        assert stats["devices_by_type"]["vibration"] == 1

    def test_to_dict_list(self):
        """Test converting registry to dictionary list."""
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device",
                "type": "light",
                "address": "addr",
            },
            source_protocol="mqtt",
        )

        dict_list = self.registry.to_dict_list()

        assert len(dict_list) == 1
        assert dict_list[0]["id"] == "dev_001"
        assert dict_list[0]["name"] == "Device"
        assert dict_list[0]["type"] == "light"
        assert "registered_at" in dict_list[0]
        assert "last_seen" in dict_list[0]

    def test_clear(self):
        """Test clearing all devices from registry."""
        self.registry.register_device(
            {
                "id": "dev_001",
                "name": "Device 1",
                "type": "light",
                "address": "addr1",
            },
            source_protocol="mqtt",
        )
        self.registry.register_device(
            {
                "id": "dev_002",
                "name": "Device 2",
                "type": "vibration",
                "address": "addr2",
            },
            source_protocol="websocket",
        )

        assert len(self.registry.get_all_devices()) == 2

        self.registry.clear()

        assert len(self.registry.get_all_devices()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
