"""Unit tests for modular test server service layer."""

from tools.test_server.services import (
    DeviceService,
    EffectService,
    ProtocolService,
)


def test_device_service_register_and_list():
    service = DeviceService()

    service.register_device(
        device_id="device_1",
        device_name="Device 1",
        device_type="mock",
        capabilities=["light"],
        protocols=["http"],
        metadata={"protocol_endpoints": {"http": {"url": "http://localhost"}}},
    )

    devices = service.list_devices()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "device_1"
    assert devices[0]["protocols"] == ["http"]


def test_effect_service_send_and_inbox():
    service = EffectService()

    result = service.send_effect(
        device_exists=True,
        device_id="device_1",
        effect={"effect_type": "vibration"},
    )
    assert result["success"] is True
    assert result["effect_type"] == "vibration"
    assert service.effects_sent == 1

    inbox_result = service.store_inbox_effect({"effect_type": "wind"})
    assert inbox_result["stored"] is True
    listing = service.list_inbox()
    assert listing["count"] == 1


def test_protocol_service_build_default_endpoints():
    service = ProtocolService(
        server_port=8090,
        mqtt_port=1883,
        coap_port=5683,
        upnp_http_port=8008,
    )

    endpoints = service.build_protocol_endpoints(
        device_id="device_1",
        protocols=["mqtt", "http", "coap", "upnp"],
        provided_endpoints=None,
    )

    assert "mqtt" in endpoints
    assert "http" in endpoints
    assert "coap" in endpoints
    assert "upnp" in endpoints
