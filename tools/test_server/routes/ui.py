"""UI routes for serving demo pages."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter()


def _ui_file(name: str) -> Path:
    # Route module is tools/test_server/routes/ui.py; climb to tools/.
    return Path(__file__).resolve().parents[2] / "ui_demos" / name


@router.get("/super_controller")
async def super_controller():
    ui_file = _ui_file("super_controller.html")
    if ui_file.exists():
        return FileResponse(str(ui_file), media_type="text/html")
    return HTMLResponse(
        "<h1>super_controller.html not found</h1>", status_code=404
    )


@router.get("/mobile_device")
async def mobile_device():
    ui_file = _ui_file("mobile_device.html")
    if ui_file.exists():
        return FileResponse(str(ui_file), media_type="text/html")
    return HTMLResponse(
        "<h1>mobile_device.html not found</h1>", status_code=404
    )


@router.get("/super_receiver")
async def super_receiver():
    ui_file = _ui_file("super_receiver.html")
    if ui_file.exists():
        return FileResponse(str(ui_file), media_type="text/html")
    return HTMLResponse(
        "<h1>super_receiver.html not found</h1>", status_code=404
    )
