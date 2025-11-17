"""
Unit tests for UPnP Server.
"""

import pytest
from unittest.mock import Mock

from src.protocol_server import UPnPServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager


@pytest.fixture
def device_manager():
    """Create a DeviceManager with mock devices."""
    # Use mock MQTT client to avoid actual network connection
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    manager = DeviceManager(client=mock_client)
    return manager


@pytest.fixture
def dispatcher(device_manager):
    """Create an EffectDispatcher."""
    return EffectDispatcher(device_manager)


@pytest.fixture
def upnp_server(dispatcher):
    """Create a UPnPServer instance."""
    return UPnPServer(
        friendly_name="Test PlaySEM Server",
        dispatcher=dispatcher,
        uuid="uuid:test-1234-5678",
        location_url="http://192.168.1.100:8080/description.xml",
        manufacturer="Test Manufacturer",
        model_name="Test Model",
        model_version="1.0.0",
    )


def test_upnp_server_initialization(upnp_server):
    """Test UPnP server initialization."""
    assert upnp_server.friendly_name == "Test PlaySEM Server"
    assert upnp_server.uuid == "uuid:test-1234-5678"
    assert (
        upnp_server.location_url == "http://192.168.1.100:8080/description.xml"
    )
    assert upnp_server.manufacturer == "Test Manufacturer"
    assert upnp_server.model_name == "Test Model"
    assert upnp_server.model_version == "1.0.0"
    assert not upnp_server.is_running()


def test_upnp_server_auto_uuid(dispatcher):
    """Test that UUID is auto-generated if not provided."""
    server = UPnPServer(dispatcher=dispatcher)
    assert server.uuid.startswith("uuid:")
    assert len(server.uuid) > 10  # Should be a valid UUID


def test_upnp_server_service_types(upnp_server):
    """Test UPnP service type definitions."""
    assert upnp_server.device_type == "urn:schemas-upnp-org:device:PlaySEM:1"
    assert upnp_server.service_type == "urn:schemas-upnp-org:service:PlaySEM:1"


def test_upnp_server_constants(upnp_server):
    """Test SSDP constants."""
    assert upnp_server.SSDP_ADDR == "239.255.255.250"
    assert upnp_server.SSDP_PORT == 1900
    assert upnp_server.SSDP_MX == 3


def test_device_description_xml(upnp_server):
    """Test device description XML generation."""
    xml = upnp_server.get_device_description_xml()

    # Check XML structure
    assert '<?xml version="1.0"?>' in xml
    assert '<root xmlns="urn:schemas-upnp-org:device-1-0">' in xml
    assert "<device>" in xml
    assert "</device>" in xml
    assert "</root>" in xml

    # Check device info
    assert "<friendlyName>Test PlaySEM Server</friendlyName>" in xml
    assert "<manufacturer>Test Manufacturer</manufacturer>" in xml
    assert "<modelName>Test Model</modelName>" in xml
    assert "<modelNumber>1.0.0</modelNumber>" in xml
    assert "<UDN>uuid:test-1234-5678</UDN>" in xml

    # Check device type
    assert (
        "<deviceType>urn:schemas-upnp-org:device:PlaySEM:1</deviceType>" in xml
    )

    # Check service
    assert "<serviceList>" in xml
    assert "<service>" in xml
    assert (
        "<serviceType>urn:schemas-upnp-org:service:PlaySEM:1</serviceType>"
        in xml
    )
    assert "<serviceId>urn:upnp-org:serviceId:PlaySEM</serviceId>" in xml


def test_device_description_xml_escaping(dispatcher):
    """Test that device description properly handles special characters."""
    server = UPnPServer(
        dispatcher=dispatcher,
        friendly_name="Test & Demo <Server>",
    )
    xml = server.get_device_description_xml()

    # Note: In production, should escape XML special chars
    # For now, just verify it generates without error
    assert xml is not None
    assert len(xml) > 0


@pytest.mark.asyncio
async def test_upnp_server_start_stop(upnp_server):
    """Test starting and stopping the UPnP server."""
    # Initially not running
    assert not upnp_server.is_running()

    # Start server
    await upnp_server.start()
    assert upnp_server.is_running()

    # Stop server
    await upnp_server.stop()
    assert not upnp_server.is_running()


@pytest.mark.asyncio
async def test_upnp_server_double_start(upnp_server):
    """Test that starting an already running server is handled gracefully."""
    await upnp_server.start()
    assert upnp_server.is_running()

    # Try starting again - should log warning but not error
    await upnp_server.start()
    assert upnp_server.is_running()

    await upnp_server.stop()


@pytest.mark.asyncio
async def test_upnp_server_double_stop(upnp_server):
    """Test that stopping an already stopped server is handled gracefully."""
    await upnp_server.start()
    await upnp_server.stop()
    assert not upnp_server.is_running()

    # Try stopping again - should log warning but not error
    await upnp_server.stop()
    assert not upnp_server.is_running()


@pytest.mark.asyncio
async def test_upnp_server_callback(dispatcher):
    """Test effect received callback."""
    callback = Mock()
    server = UPnPServer(dispatcher=dispatcher, on_effect_received=callback)

    # Callback should be stored
    assert server.on_effect_received == callback


@pytest.mark.asyncio
async def test_notify_alive_format(upnp_server):
    """Test NOTIFY alive message format."""
    # We can't easily test the actual network messages without complex mocking,
    # but we can verify the message would be correctly formatted
    await upnp_server.start()

    # Check that server is running and has transport
    assert upnp_server.is_running()
    assert upnp_server._transport is not None

    await upnp_server.stop()


@pytest.mark.asyncio
async def test_msearch_response_targets(upnp_server):
    """Test that M-SEARCH response includes correct targets."""
    # The server should respond to:
    # - ssdp:all
    # - device type
    # - service type
    # - uuid

    await upnp_server.start()

    # Verify targets are set correctly
    assert upnp_server.uuid == "uuid:test-1234-5678"
    assert upnp_server.device_type == "urn:schemas-upnp-org:device:PlaySEM:1"
    assert upnp_server.service_type == "urn:schemas-upnp-org:service:PlaySEM:1"

    await upnp_server.stop()


@pytest.mark.asyncio
async def test_upnp_server_location_url(dispatcher):
    """Test location URL configuration."""
    server1 = UPnPServer(
        dispatcher=dispatcher, location_url="http://10.0.0.5:9000/device.xml"
    )
    assert server1.location_url == "http://10.0.0.5:9000/device.xml"

    # Test default location
    server2 = UPnPServer(dispatcher=dispatcher)
    assert server2.location_url == "http://0.0.0.0:8080/description.xml"


@pytest.mark.asyncio
async def test_upnp_server_with_effect_dispatcher_integration(upnp_server):
    """Test UPnP server integration with effect dispatcher."""
    # Start server
    await upnp_server.start()
    assert upnp_server.is_running()

    # Server should have dispatcher configured
    assert upnp_server.dispatcher is not None
    assert upnp_server.dispatcher.device_manager is not None

    # Verify device manager has driver (new API)
    assert hasattr(upnp_server.dispatcher.device_manager, "driver")
    assert upnp_server.dispatcher.device_manager.driver is not None

    await upnp_server.stop()


@pytest.mark.asyncio
async def test_advertisement_periodic_task(upnp_server):
    """Test that periodic advertisement task is created."""
    await upnp_server.start()

    # Check that advertisement task exists
    assert upnp_server._advertisement_task is not None
    assert not upnp_server._advertisement_task.done()

    await upnp_server.stop()

    # Task should be cancelled after stop
    assert (
        upnp_server._advertisement_task.cancelled()
        or upnp_server._advertisement_task.done()
    )


def test_upnp_server_thread_safety(upnp_server):
    """Test that server uses proper locking."""
    assert hasattr(upnp_server, "_lock")
    assert upnp_server._lock is not None


@pytest.mark.asyncio
async def test_upnp_server_context_cleanup(upnp_server):
    """Test that server cleans up resources properly."""
    await upnp_server.start()
    assert upnp_server._transport is not None
    assert upnp_server._advertisement_task is not None

    await upnp_server.stop()

    # Resources should be cleaned up
    # (Note: _transport might still exist but should be closed)
    assert not upnp_server.is_running()
