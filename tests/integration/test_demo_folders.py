import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path if not present
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.mark.asyncio
async def test_mock_serial_demo_runs_successfully():
    """Verify that tools/serial/mock_serial_demo.py runs to completion without errors."""
    from tools.serial.mock_serial_demo import main as mock_serial_main

    # mock_serial_main runs entirely in memory and doesn't sleep or prompt, so we can call it directly.
    await mock_serial_main()


def test_import_all_demo_modules():
    """Verify that all demo/client/server scripts in the tools directories can be successfully imported.

    This ensures there are no syntax errors, missing package imports, or broken paths.
    """
    # Verify serial driver demo import
    from tools.serial import driver_demo as serial_demo

    assert serial_demo is not None

    # Verify bluetooth driver demo import
    from tools.bluetooth import driver_demo as bluetooth_demo

    assert bluetooth_demo is not None

    # Verify HTTP client/server import
    from tools.http import client as http_client, server as http_server

    assert http_client is not None
    assert http_server is not None

    # Verify WebSocket client/server import
    from tools.websocket import client as ws_client, server as ws_server

    assert ws_client is not None
    assert ws_server is not None

    # Verify CoAP client/server import
    from tools.coap import client as coap_client, server as coap_server

    assert coap_client is not None
    assert coap_server is not None
    assert hasattr(coap_server, "main")

    # Verify MQTT client/server import
    from tools.mqtt import client_public as mqtt_client, server as mqtt_server

    assert hasattr(mqtt_client, "main")
    assert hasattr(mqtt_server, "main")

    # Verify UPnP client/server import
    from tools.upnp import client as upnp_client, server as upnp_server

    assert hasattr(upnp_client, "main")
    assert hasattr(upnp_server, "main")
