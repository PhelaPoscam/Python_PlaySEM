"""
Device Routes - API endpoints for device management.

Endpoints:
- GET /api/devices - List connected devices
- POST /api/devices/scan - Scan for devices
- POST /api/devices/connect - Connect to device
- POST /api/devices/disconnect - Disconnect device
"""

from typing import Dict

from fastapi import APIRouter, WebSocket
from fastapi.responses import JSONResponse


class DeviceRoutes:
    """Routes for device management."""

    def __init__(self, router: APIRouter):
        """Initialize device routes.

        Args:
            router: FastAPI router
        """
        self.router = router
        self._register_routes()

    def _register_routes(self):
        """Register device routes."""

        @self.router.get("/api/devices")
        async def list_devices(device_service):
            """List connected devices."""
            devices = device_service.get_device_list()
            return JSONResponse(
                {
                    "type": "device_list",
                    "devices": devices,
                }
            )

        @self.router.post("/api/devices/scan")
        async def scan_devices(
            driver_type: str,
            websocket: WebSocket,
            device_service,
        ):
            """Scan for devices.

            Args:
                driver_type: Type of driver (bluetooth, serial, mqtt, mock)
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            print(f"[SCAN] Scanning for {driver_type} devices...")

            try:
                devices = await device_service.scan_devices(
                    websocket=websocket,
                    driver_type=driver_type,
                )

                return JSONResponse(
                    {
                        "type": "scan_result",
                        "success": True,
                        "devices_found": len(devices),
                        "devices": devices,
                    }
                )

            except Exception as e:
                print(f"[x] Scan error: {e}")
                return JSONResponse(
                    {
                        "type": "scan_result",
                        "success": False,
                        "error": str(e),
                    },
                    status_code=500,
                )

        @self.router.post("/api/devices/connect")
        async def connect_device(
            address: str,
            driver_type: str,
            websocket: WebSocket,
            device_service,
        ):
            """Connect to a device.

            Args:
                address: Device address
                driver_type: Driver type
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            try:
                device = await device_service.connect_device(
                    websocket=websocket,
                    address=address,
                    driver_type=driver_type,
                )

                return JSONResponse(
                    {
                        "type": "connect_result",
                        "success": True,
                        "device": {
                            "id": device.id,
                            "name": device.name,
                            "type": device.type,
                            "address": device.address,
                        },
                    }
                )

            except Exception as e:
                print(f"[x] Connect error: {e}")
                return JSONResponse(
                    {
                        "type": "connect_result",
                        "success": False,
                        "error": str(e),
                    },
                    status_code=500,
                )

        @self.router.post("/api/devices/disconnect")
        async def disconnect_device(
            device_id: str,
            websocket: WebSocket,
            device_service,
        ):
            """Disconnect from a device.

            Args:
                device_id: Device ID
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            try:
                await device_service.disconnect_device(
                    websocket=websocket,
                    device_id=device_id,
                )

                return JSONResponse(
                    {
                        "type": "disconnect_result",
                        "success": True,
                        "device_id": device_id,
                    }
                )

            except Exception as e:
                print(f"[x] Disconnect error: {e}")
                return JSONResponse(
                    {
                        "type": "disconnect_result",
                        "success": False,
                        "error": str(e),
                    },
                    status_code=500,
                )
