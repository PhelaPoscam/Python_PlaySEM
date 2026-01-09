"""
Main Server - ControlPanelServer orchestrator integrating all services.

This is the main application server that:
- Initializes and manages all services
- Sets up FastAPI routes
- Handles WebSocket connections
- Manages protocol servers
- Coordinates device and effect operations
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from playsem import DeviceManager, EffectDispatcher, Timeline

from .config import ServerConfig
from .handlers import WebSocketHandler
from .models import ConnectedDevice
from .routes import DeviceRoutes, EffectRoutes, UIRoutes
from .services import (
    DeviceService,
    EffectService,
    TimelineService,
    ProtocolService,
)


class ControlPanelServer:
    """Backend server for PlaySEM control panel."""

    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the control panel server.

        Args:
            config: Server configuration (uses defaults if None)
        """
        self.config = config or ServerConfig()

        # Setup FastAPI with lifespan
        @asynccontextmanager
        async def lifespan(app):
            # Startup
            print("[*] Server starting up...")
            yield
            # Shutdown
            await self._shutdown()

        self.app = FastAPI(
            title="PlaySEM Control Panel API",
            lifespan=lifespan,
        )

        # Core state
        self.devices: Dict[str, ConnectedDevice] = {}
        self.stats = {
            "effects_sent": 0,
            "errors": 0,
            "start_time": time.time(),
        }

        # Global device manager and dispatcher for protocol servers
        # Allows external clients (MQTT, CoAP, HTTP, UPnP) to access devices
        mock_client = type("MockClient", (), {"publish": lambda *args: None})()
        self.global_device_manager = DeviceManager(client=mock_client)
        self.global_dispatcher = EffectDispatcher(self.global_device_manager)

        # Protocol servers
        self.mqtt_server = None
        self.coap_server = None
        self.http_api_server = None
        self.upnp_server = None

        # Timeline player
        self.timeline_player = Timeline(self.global_dispatcher)

        # Initialize services
        self.device_service = DeviceService(global_dispatcher=self.global_dispatcher)
        self.effect_service = EffectService()
        self.timeline_service = TimelineService()
        self.protocol_service = ProtocolService()
        self.websocket_handler = WebSocketHandler()

        # Setup routes and handlers
        self._setup_routes()
        self._setup_static_files()

    def _setup_routes(self):
        """Setup FastAPI routes."""
        router = self.app.router

        # Device routes
        DeviceRoutes(router)

        # Effect routes
        EffectRoutes(router)

        # UI routes
        ui_path = self.config.get_ui_path()
        UIRoutes(router, ui_path)

        # WebSocket endpoint
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint for client communication."""
            await self.websocket_handler.handle_client(
                websocket=websocket,
                devices=self.devices,
                message_handler=self._handle_websocket_message,
            )

        @self.app.get("/health")
        async def health_check():
            """Health check for automated tests."""
            return {"status": "ok"}

        # API endpoints
        @self.app.get("/api/stats")
        async def get_stats():
            """Get server statistics."""
            return {
                "uptime": time.time() - self.stats["start_time"],
                "effects_sent": self.stats["effects_sent"],
                "errors": self.stats["errors"],
                "connected_devices": len(self.devices),
                "connected_clients": len(self.websocket_handler.clients),
                "protocols": self.protocol_service.get_all_statuses(),
            }

    def _setup_static_files(self):
        """Setup static file serving."""
        ui_path = self.config.get_ui_path()
        if ui_path.exists():
            try:
                self.app.mount(
                    "/static",
                    StaticFiles(directory=str(ui_path)),
                    name="static",
                )
            except Exception as e:
                print(f"[WARNING] Could not mount static files: {e}")

    async def _handle_websocket_message(
        self,
        websocket: WebSocket,
        **kwargs,
    ):
        """Route WebSocket messages to appropriate handlers.

        Args:
            websocket: WebSocket connection
            **kwargs: Message-specific parameters
        """
        message_type = kwargs.get("message_type")

        try:
            if message_type == "scan_devices":
                await self.device_service.scan_devices(
                    websocket=websocket,
                    driver_type=kwargs.get("driver_type"),
                )

            elif message_type == "connect_device":
                await self.device_service.connect_device(
                    websocket=websocket,
                    address=kwargs.get("address"),
                    driver_type=kwargs.get("driver_type"),
                )

            elif message_type == "disconnect_device":
                await self.device_service.disconnect_device(
                    websocket=websocket,
                    device_id=kwargs.get("device_id"),
                )

            elif message_type == "send_effect":
                device_id = kwargs.get("device_id")
                effect_data = kwargs.get("effect_data", {})
                await self.effect_service.send_effect(
                    websocket=websocket,
                    device_id=device_id,
                    effect_data=effect_data,
                    devices=self.devices,
                    web_clients=self.websocket_handler.web_clients,
                )
                self.stats["effects_sent"] += 1

            elif message_type == "send_effect_protocol":
                protocol = kwargs.get("protocol")
                effect_data = kwargs.get("effect_data", {})
                await self.effect_service.send_effect_protocol(
                    websocket=websocket,
                    protocol=protocol,
                    effect_data=effect_data,
                    mqtt_server=self.mqtt_server,
                    http_api_server=self.http_api_server,
                    coap_server=self.coap_server,
                    upnp_server=self.upnp_server,
                    web_clients=self.websocket_handler.web_clients,
                )
                self.stats["effects_sent"] += 1

            elif message_type == "broadcast_effect":
                effect = kwargs.get("effect")
                await self.websocket_handler.broadcast_effect(
                    effect=effect,
                    device_id="broadcast",
                    protocol="websocket",
                )
                self.stats["effects_sent"] += 1

            elif message_type == "start_protocol_server":
                protocol = kwargs.get("protocol")
                port = self.config.get_protocol_port(protocol)
                await self.protocol_service.start_protocol_server(
                    websocket=websocket,
                    protocol=protocol,
                    port=port,
                    host=self.config.host,
                )

                # Store server reference
                server = self.protocol_service.get_server(protocol)
                if protocol == "mqtt":
                    self.mqtt_server = server
                elif protocol == "coap":
                    self.coap_server = server
                elif protocol == "http":
                    self.http_api_server = server
                elif protocol == "upnp":
                    self.upnp_server = server

            elif message_type == "stop_protocol_server":
                protocol = kwargs.get("protocol")
                await self.protocol_service.stop_protocol_server(
                    websocket=websocket,
                    protocol=protocol,
                )

                # Clear server reference
                if protocol == "mqtt":
                    self.mqtt_server = None
                elif protocol == "coap":
                    self.coap_server = None
                elif protocol == "http":
                    self.http_api_server = None
                elif protocol == "upnp":
                    self.upnp_server = None

            elif message_type == "upload_timeline":
                file_content = kwargs.get("file_content")
                file_type = kwargs.get("file_type")
                timeline_id = f"timeline_{int(time.time() * 1000)}"

                try:
                    timeline_data = json.loads(file_content)
                except json.JSONDecodeError:
                    timeline_data = {}

                await self.timeline_service.handle_timeline_upload(
                    websocket=websocket,
                    timeline_id=timeline_id,
                    timeline_data=timeline_data,
                    effect_dispatcher=self.global_dispatcher,
                )

            elif message_type in [
                "play_timeline",
                "pause_timeline",
                "resume_timeline",
                "stop_timeline",
                "get_timeline_status",
            ]:
                # Timeline operations
                await self._handle_timeline_operation(
                    websocket=websocket,
                    operation=message_type,
                )

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

        except Exception as e:
            print(f"[ERROR] Message handling error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                }
            )

    async def _handle_timeline_operation(
        self,
        websocket: WebSocket,
        operation: str,
    ):
        """Handle timeline operations.

        Args:
            websocket: WebSocket connection
            operation: Timeline operation (play, pause, resume, stop, get_status)
        """
        timeline_id = "current"  # Default timeline ID

        if operation == "play_timeline":
            await self.timeline_service.play_timeline(
                websocket=websocket,
                timeline_id=timeline_id,
                broadcast_callback=self._on_timeline_event,
            )

        elif operation == "pause_timeline":
            await self.timeline_service.pause_timeline(
                websocket=websocket,
                timeline_id=timeline_id,
                broadcast_callback=self._on_timeline_event,
            )

        elif operation == "resume_timeline":
            await self.timeline_service.resume_timeline(
                websocket=websocket,
                timeline_id=timeline_id,
                broadcast_callback=self._on_timeline_event,
            )

        elif operation == "stop_timeline":
            await self.timeline_service.stop_timeline(
                websocket=websocket,
                timeline_id=timeline_id,
                broadcast_callback=self._on_timeline_event,
            )

        elif operation == "get_timeline_status":
            await self.timeline_service.get_timeline_status(
                websocket=websocket,
                timeline_id=timeline_id,
            )

    async def _on_timeline_event(self, **kwargs):
        """Handle timeline events.

        Args:
            **kwargs: Timeline event parameters
        """
        timeline_id = kwargs.get("timeline_id")
        effect = kwargs.get("effect")
        event_type = kwargs.get("event_type")

        if effect:
            # Dispatch effect from timeline
            await self.websocket_handler.broadcast_effect(
                effect=effect,
                device_id=timeline_id,
                protocol="timeline",
            )

        elif event_type:
            # Broadcast timeline event
            await self.websocket_handler.broadcast_effect(
                effect=type(
                    "Effect",
                    (),
                    {
                        "effect_type": event_type,
                        "duration": 0,
                        "intensity": 0,
                    },
                )(),
                device_id=timeline_id,
                protocol="timeline",
            )

    async def _shutdown(self):
        """Gracefully shutdown all services."""
        print("[SHUTDOWN] Initiating graceful shutdown...")

        try:
            # Stop protocol servers
            await self.protocol_service.stop_all()

            # Cleanup timeline service
            await self.timeline_service.cleanup()

            print("[OK] All services stopped gracefully")

        except Exception as e:
            print(f"[ERROR] Shutdown error: {e}")

    async def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8090,
    ):
        """Run the server.

        Args:
            host: Host address
            port: Port number
        """
        import uvicorn

        print(f"[*] Starting server on {host}:{port}")
        print(f"[*] WebSocket endpoint: ws://{host}:{port}/ws")
        print(f"[*] Web UI: http://{host}:{port}/")

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance.

        Returns:
            FastAPI app
        """
        return self.app
