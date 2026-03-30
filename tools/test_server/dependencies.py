"""Dependency providers for the modular PlaySEM test server."""

from fastapi import Request

from tools.test_server.config import ServerConfig
from tools.test_server.services import (
    DeviceService,
    EffectService,
    ProtocolService,
)


def get_server_config(request: Request) -> ServerConfig:
    """Return app runtime configuration from application state."""

    return request.app.state.server_config


def get_device_service(request: Request) -> DeviceService:
    """Return device service from application state."""

    return request.app.state.device_service


def get_effect_service(request: Request) -> EffectService:
    """Return effect service from application state."""

    return request.app.state.effect_service


def get_protocol_service(request: Request) -> ProtocolService:
    """Return protocol service from application state."""

    return request.app.state.protocol_service
