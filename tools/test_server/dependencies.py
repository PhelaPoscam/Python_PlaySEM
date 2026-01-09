"""
Dependency Injection for FastAPI routes.

Provides functions for injecting services into route handlers.
"""

from fastapi import Depends, Request

from .services import (
    DeviceService,
    EffectService,
    ProtocolService,
    TimelineService,
)


async def get_device_service(request: Request) -> DeviceService:
    """Get device service from app state."""
    return request.app.state.device_service


async def get_effect_service(request: Request) -> EffectService:
    """Get effect service from app state."""
    return request.app.state.effect_service


async def get_protocol_service(request: Request) -> ProtocolService:
    """Get protocol service from app state."""
    return request.app.state.protocol_service


async def get_timeline_service(request: Request) -> TimelineService:
    """Get timeline service from app state."""
    return request.app.state.timeline_service


async def get_devices(request: Request) -> dict:
    """Get devices dictionary from app state."""
    return request.app.state.device_service.devices


async def get_web_clients(request: Request) -> dict:
    """Get web clients dictionary from app state."""
    return request.app.state.web_clients


async def get_global_dispatcher(request: Request):
    """Get global effect dispatcher from app state."""
    return request.app.state.global_dispatcher


async def get_global_device_manager(request: Request):
    """Get global device manager from app state."""
    return request.app.state.global_device_manager


async def get_stats(request: Request) -> dict:
    """Get stats dictionary from app state."""
    return request.app.state.stats


# Dependency shortcuts for routes
DeviceServiceDep = Depends(get_device_service)
EffectServiceDep = Depends(get_effect_service)
ProtocolServiceDep = Depends(get_protocol_service)
TimelineServiceDep = Depends(get_timeline_service)
DevicesDep = Depends(get_devices)
WebClientsDep = Depends(get_web_clients)
GlobalDispatcherDep = Depends(get_global_dispatcher)
GlobalDeviceManagerDep = Depends(get_global_device_manager)
StatsDep = Depends(get_stats)
