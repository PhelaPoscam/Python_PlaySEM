"""Device-related API routes for the modular server."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from tools.test_server.dependencies import (
    get_device_service,
    get_protocol_service,
)
from tools.test_server.services import DeviceService, ProtocolService

router = APIRouter()


@router.get("/api/devices")
async def list_devices(
    device_service: DeviceService = Depends(get_device_service),
) -> Dict[str, Any]:
    """List all currently registered devices."""

    return {"devices": device_service.list_devices()}


@router.post("/api/devices/register")
async def register_device(
    body: Dict[str, Any],
    device_service: DeviceService = Depends(get_device_service),
    protocol_service: ProtocolService = Depends(get_protocol_service),
) -> Dict[str, Any]:
    """Register a device and materialize default protocol endpoints."""

    device_id = body.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")

    protocols = body.get("protocols", [])
    await protocol_service.ensure_protocol_servers(protocols)

    provided_endpoints = (
        body.get("metadata")
        or body.get("protocol_endpoints")
        or body.get("endpoints")
        or {}
    )
    endpoints = (
        provided_endpoints if isinstance(provided_endpoints, dict) else {}
    )
    endpoints = protocol_service.build_protocol_endpoints(
        device_id=device_id,
        protocols=protocols,
        provided_endpoints=endpoints,
    )

    device_service.register_device(
        device_id=device_id,
        device_name=body.get("device_name", device_id),
        device_type=body.get("device_type", "unknown"),
        capabilities=body.get("capabilities", []),
        protocols=protocols,
        connection_mode=body.get("connection_mode", "direct"),
        metadata={"protocol_endpoints": endpoints},
    )

    return {"success": True, "device_id": device_id, "status": "registered"}


@router.post("/api/devices/connect")
@router.post("/api/connect")
async def connect_device(
    body: Dict[str, Any],
    device_service: DeviceService = Depends(get_device_service),
) -> Dict[str, Any]:
    """Connect a device using an address/driver identifier payload."""

    address = body.get("address")
    driver_type = body.get("driver_type", "unknown")
    if not address:
        raise HTTPException(status_code=400, detail="address required")

    device = device_service.connect_device(
        address=address,
        driver_type=driver_type,
    )
    return {
        "type": "success",
        "device_id": device.device_id,
        "message": f"Connected to {address}",
    }
