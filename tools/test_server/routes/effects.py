"""Effect-related API routes for the modular server."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from tools.test_server.dependencies import (
    get_device_service,
    get_effect_service,
)
from tools.test_server.services import DeviceService, EffectService

router = APIRouter()


@router.post("/api/effects/send")
@router.post("/api/effect")
async def send_effect(
    body: Dict[str, Any],
    device_service: DeviceService = Depends(get_device_service),
    effect_service: EffectService = Depends(get_effect_service),
) -> Dict[str, Any]:
    """Send an effect to a registered device."""

    device_id = body.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")

    effect_payload = body.get("effect", body)
    try:
        return await effect_service.send_effect(
            device_exists=device_service.has_device(device_id),
            device_id=device_id,
            effect=effect_payload,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found",
        )


@router.post("/api/effects/inbox")
async def inbox_add(
    effect: Dict[str, Any],
    effect_service: EffectService = Depends(get_effect_service),
) -> Dict[str, Any]:
    """Store incoming effects for observability/testing."""

    return effect_service.store_inbox_effect(effect)


@router.get("/api/effects/inbox")
async def inbox_list(
    effect_service: EffectService = Depends(get_effect_service),
) -> Dict[str, Any]:
    """List observed effects from the inbox."""

    return effect_service.list_inbox()
