"""
Unit tests for the refactored, more complete UPnP Server.
"""

import asyncio
import socket
import pytest
from unittest.mock import Mock
import aiohttp

from src.protocol_server import UPnPServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager


# --- Smoke test for UPNP ---
import pytest


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_upnp_smoke_description(upnp_server):
    """Smoke test: Start UPnP server and check /description.xml endpoint responds."""
    desc_url = upnp_server.location_url
    async with aiohttp.ClientSession() as session:
        async with session.get(desc_url) as response:
            assert response.status == 200
            text = await response.text()
            assert "<friendlyName>" in text


@pytest.fixture
def device_manager():
    """Create a DeviceManager with a mock client."""
    return DeviceManager(client=Mock())


@pytest.fixture
def dispatcher(device_manager):
    """Create an EffectDispatcher."""
    return EffectDispatcher(device_manager)


@pytest.fixture
async def upnp_server(dispatcher):
    """
    Provides a running UPnPServer instance for testing.
    This fixture handles the startup and shutdown of the server.
    """
    # Find a free port for the HTTP server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        http_port = s.getsockname()[1]

    server = UPnPServer(
        friendly_name="Test PlaySEM Server",
        dispatcher=dispatcher,
        uuid="uuid:test-1234-5678",
        http_host="127.0.0.1",
        http_port=http_port,
        manufacturer="Test Manufacturer",
        model_name="Test Model",
        model_version="1.0.0",
    )

    await server.start()
    yield server
    await server.stop()


def test_upnp_server_initialization(dispatcher):
    """Test UPnP server initialization and dynamic URL generation."""
    server = UPnPServer(
        dispatcher=dispatcher, http_host="127.0.0.1", http_port=9999
    )
    assert server.http_port == 9999
    assert server.http_host == "127.0.0.1"
    assert server.location_url == "http://127.0.0.1:9999/description.xml"
    assert not server.is_running()


def test_upnp_server_auto_uuid(dispatcher):
    """Test that UUID is auto-generated if not provided."""
    server = UPnPServer(dispatcher=dispatcher)
    assert server.uuid.startswith("uuid:")
    assert len(server.uuid) > 10


def test_device_description_xml_generation(dispatcher):
    """Test device description XML generation with special characters."""
    server = UPnPServer(
        dispatcher=dispatcher,
        friendly_name="Test & Demo <Server>",
        uuid="uuid:test-xml",
    )
    xml = server.get_device_description_xml()
    assert '<?xml version="1.0"?>' in xml
    assert '<root xmlns="urn:schemas-upnp-org:device-1-0">' in xml
    assert "<friendlyName>Test &amp; Demo &lt;Server&gt;</friendlyName>" in xml
    assert "<UDN>uuid:test-xml</UDN>" in xml
    assert "<SCPDURL>/scpd.xml</SCPDURL>" in xml
    assert "<controlURL>/control</controlURL>" in xml


@pytest.mark.asyncio
async def test_upnp_http_endpoints(upnp_server):
    """
    Test that the integrated HTTP server correctly serves the UPnP XML files.
    """
    assert upnp_server.is_running()

    desc_url = upnp_server.location_url
    scpd_url = (
        f"http://{upnp_server.http_host}:{upnp_server.http_port}/scpd.xml"
    )
    control_url = (
        f"http://{upnp_server.http_host}:{upnp_server.http_port}/control"
    )

    async with aiohttp.ClientSession() as session:
        # 1. Test the description.xml endpoint
        async with session.get(desc_url) as response:
            assert response.status == 200
            assert response.content_type == "application/xml"
            text = await response.text()
            assert "<friendlyName>Test PlaySEM Server</friendlyName>" in text
            assert f"<UDN>{upnp_server.uuid}</UDN>" in text

        # 2. Test the scpd.xml endpoint
        async with session.get(scpd_url) as response:
            assert response.status == 200
            assert response.content_type == "application/xml"
            text = await response.text()
            assert '<scpd xmlns="urn:schemas-upnp-org:service-1-0">' in text
            assert "<name>SendEffect</name>" in text

        # 3. Test the control endpoint (stub)
        soap_request_body = (
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><u:SendEffect '
            "xmlns:u='urn:schemas-upnp-org:service:PlaySEM:1'>"
            "</u:SendEffect></s:Body></s:Envelope>"
        )
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": '"urn:schemas-upnp-org:service:PlaySEM:1#SendEffect"',
        }
        async with session.post(
            control_url, data=soap_request_body, headers=headers
        ) as response:
            assert response.status == 500
            text = await response.text()
            assert "<faultstring>UPnPError</faultstring>" in text
            assert "<errorCode>501</errorCode>" in text


@pytest.mark.asyncio
async def test_ssdp_discovery(upnp_server):
    """
    Test that the server responds to SSDP M-SEARCH requests.
    This is a simplified test that checks if the server is listening.
    A full test would require a separate client sending multicast packets.
    """
    assert upnp_server.is_running()
    assert upnp_server._transport is not None

    # Check that the server is listening on the SSDP port
    sockname = upnp_server._transport.get_extra_info("socket").getsockname()
    assert sockname[1] == 1900

    # The fixture handles start and stop, so we just need to ensure
    # it ran without error
    await asyncio.sleep(0.1)
