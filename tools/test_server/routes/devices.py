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

from ..dependencies import DeviceServiceDep
from ..services import DeviceService


class DeviceRoutes:
    """Routes for device management."""

    def __init__(self, router: APIRouter, device_service: DeviceService = None):
        """Initialize device routes.

        Args:
            router: FastAPI router
            device_service: Device service instance (optional for backward compat)
        """
        self.router = router
        self.device_service = device_service
        self._register_routes()

    def _register_routes(self):
        """Register device routes."""

        @self.router.get("/api/devices")
        async def list_devices(device_service: DeviceService = DeviceServiceDep):
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
            device_service: DeviceService = DeviceServiceDep,
        ):
            """Scan for devices.

            Args:
                driver_type: Type of driver (bluetooth, serial, mqtt, mock)
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            print(f"[SCAN] Scanning for {driver_type} devices...")

            try:
                await device_service.scan_devices(
                    websocket=websocket,
                    driver_type=driver_type,
                )

                return JSONResponse(
                    {
                        "type": "scan_result",
                        "success": True,
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
            device_service: DeviceService = DeviceServiceDep,
        ):
            """Connect to a device.

            Args:
                address: Device address
                driver_type: Driver type
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            try:
                success = await device_service.connect_device(
                    websocket=websocket,
                    address=address,
                    driver_type=driver_type,
                )

                if success:
                    device_id = f"{driver_type}_{address.replace(':', '_').replace('/', '_')}"
                    device = device_service.get_device(device_id)
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
                else:
                    return JSONResponse(
                        {
                            "type": "connect_result",
                            "success": False,
                            "error": "Connection failed",
                        },
                        status_code=500,
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
            device_service: DeviceService = DeviceServiceDep,
        ):
            """Disconnect from a device.

            Args:
                device_id: Device ID
                websocket: WebSocket for updates
                device_service: Device service instance
            """
            try:
                success = await device_service.disconnect_device(
                    websocket=websocket,
                    device_id=device_id,
                )

                return JSONResponse(
                    {
                        "type": "disconnect_result",
                        "success": success,
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
