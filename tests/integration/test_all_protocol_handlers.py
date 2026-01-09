"""
Test protocol handlers integration
"""

import pytest
from tools.test_server.handlers import (
    HTTPHandler,
    CoAPHandler,
    UPnPHandler,
    MQTTHandler,
    WebSocketHandler,
)


class MockDispatcher:
    """Mock effect dispatcher."""

    async def dispatch_effect(self, device_id, effect):
        pass



def test_http_handler_import():
    """Test HTTP handler can be imported."""
    assert HTTPHandler is not None


def test_coap_handler_import():
    """Test CoAP handler can be imported."""
    assert CoAPHandler is not None


def test_upnp_handler_import():
    """Test UPnP handler can be imported."""
    assert UPnPHandler is not None


def test_mqtt_handler_import():
    """Test MQTT handler can be imported."""
    assert MQTTHandler is not None


def test_websocket_handler_import():
    """Test WebSocket handler can be imported."""
    assert WebSocketHandler is not None


def test_all_handlers_exported():
    """Test all 5 protocol handlers are properly exported."""
    from tools.test_server.handlers import __all__

    assert "HTTPHandler" in __all__
    assert "CoAPHandler" in __all__
    assert "UPnPHandler" in __all__
    assert "MQTTHandler" in __all__
    assert "WebSocketHandler" in __all__

    assert len(__all__) == 5


def test_http_handler_instantiation():
    """Test HTTP handler can be instantiated."""
    from tools.test_server.handlers.http_handler import HTTPConfig

    dispatcher = MockDispatcher()
    config = HTTPConfig(host="127.0.0.1", port=8080)
    handler = HTTPHandler(global_dispatcher=dispatcher, config=config)
    
    assert handler is not None
    assert handler.config.host == "127.0.0.1"
    assert handler.config.port == 8080


def test_coap_handler_instantiation():
    """Test CoAP handler can be instantiated."""
    from tools.test_server.handlers.coap_handler import CoAPConfig

    dispatcher = MockDispatcher()
    config = CoAPConfig(host="127.0.0.1", port=5683)
    handler = CoAPHandler(global_dispatcher=dispatcher, config=config)
    
    assert handler is not None
    assert handler.config.host == "127.0.0.1"
    assert handler.config.port == 5683


def test_upnp_handler_instantiation():
    """Test UPnP handler can be instantiated."""
    from tools.test_server.handlers.upnp_handler import UPnPConfig

    dispatcher = MockDispatcher()

    config = UPnPConfig(
        device_name="Test Device",
        device_type="urn:test:device:1"
    )
    handler = UPnPHandler(global_dispatcher=dispatcher, config=config)

    assert handler is not None
    assert handler.config.device_name == "Test Device"
    assert handler.config.device_type == "urn:test:device:1"


def test_mqtt_handler_instantiation():
    """Test MQTT handler can be instantiated."""
    from tools.test_server.handlers.mqtt_handler import MQTTConfig

    dispatcher = MockDispatcher()
    config = MQTTConfig(host="127.0.0.1", port=1883)
    handler = MQTTHandler(global_dispatcher=dispatcher, config=config)

    assert handler is not None
    assert handler.config.host == "127.0.0.1"
    assert handler.config.port == 1883


def test_websocket_handler_instantiation():
    """Test WebSocket handler can be instantiated."""
    dispatcher = MockDispatcher()
    # WebSocketHandler in test_server uses old pattern without config
    handler = WebSocketHandler()
    
    assert handler is not None


def test_modular_architecture_complete():
    """Test that modular extraction is complete with all 5 handlers."""
    # All handlers should be importable from single module
    from tools.test_server import handlers
    
    # Verify all handlers are available
    assert hasattr(handlers, "HTTPHandler")
    assert hasattr(handlers, "CoAPHandler")
    assert hasattr(handlers, "UPnPHandler")
    assert hasattr(handlers, "MQTTHandler")
    assert hasattr(handlers, "WebSocketHandler")
    
    # All should be Handler classes
    assert callable(handlers.HTTPHandler)
    assert callable(handlers.CoAPHandler)
    assert callable(handlers.UPnPHandler)
    assert callable(handlers.MQTTHandler)
    assert callable(handlers.WebSocketHandler)
