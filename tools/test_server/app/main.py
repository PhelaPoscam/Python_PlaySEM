"""
FastAPI Application Factory

Creates and configures the FastAPI application with all services and routes.
This is the thin orchestrator that wires together services, routes, and handlers.
"""

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from playsem import DeviceManager, EffectDispatcher, Timeline

from ..config import ServerConfig
from ..models import ConnectedDevice
from ..routes import DeviceRoutes, EffectRoutes, UIRoutes
from ..services import (
    DeviceService,
    EffectService,
    ProtocolService,
    TimelineService,
)
from .handlers import WebSocketHandler, MQTTHandler


def create_app(config: Optional[ServerConfig] = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        config: Server configuration (uses defaults if None)

    Returns:
        Configured FastAPI instance
    """
    config = config or ServerConfig()

    # ============================================================
    # LIFESPAN MANAGEMENT
    # ============================================================
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Handle app startup and shutdown."""
        # Startup
        print("[*] PlaySEM Control Panel starting...")
        app.state.start_time = time.time()

        yield

        # Shutdown
        print("[*] PlaySEM Control Panel shutting down...")
        await _shutdown_app(app)

    # ============================================================
    # APP INITIALIZATION
    # ============================================================
    app = FastAPI(
        title="PlaySEM Control Panel API",
        description="Backend for real-time device management and effect testing",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ============================================================
    # MIDDLEWARE
    # ============================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # CORE STATE
    # ============================================================
    app.state.config = config
    app.state.devices = {}
    app.state.web_clients = {}
    app.state.stats = {
        "effects_sent": 0,
        "errors": 0,
        "start_time": time.time(),
    }

    # ============================================================
    # GLOBAL DEVICE MANAGER & DISPATCHER
    # ============================================================
    # Mock client for protocol servers that need to publish/subscribe
    # without an actual MQTT connection
    mock_client = type("MockClient", (), {"publish": lambda *args: None})()
    app.state.global_device_manager = DeviceManager(client=mock_client)
    app.state.global_dispatcher = EffectDispatcher(
        app.state.global_device_manager
    )

    # ============================================================
    # TIMELINE PLAYER
    # ============================================================
    app.state.timeline_player = Timeline(app.state.global_dispatcher)

    # ============================================================
    # SERVICE INSTANTIATION (DEPENDENCY INJECTION)
    # ============================================================
    app.state.device_service = DeviceService(
        global_dispatcher=app.state.global_dispatcher
    )
    app.state.effect_service = EffectService()
    app.state.timeline_service = TimelineService()
    app.state.protocol_service = ProtocolService()
    app.state.websocket_handler = WebSocketHandler()

    # ============================================================
    # PROTOCOL HANDLERS (ISOLATED)
    # ============================================================
    app.state.mqtt_handler = MQTTHandler(
        global_dispatcher=app.state.global_dispatcher
    )

    # ============================================================
    # ROUTES SETUP
    # ============================================================
    ui_files_dir = config.get_ui_path()
    DeviceRoutes(app.router)
    EffectRoutes(app.router)
    UIRoutes(app.router, ui_files_dir)

    # ============================================================
    # STATIC FILES
    # ============================================================
    _setup_static_files(app, config)

    # ============================================================
    # HEALTH CHECK ENDPOINT
    # ============================================================
    @app.get("/health")
    async def health_check():
        """Health check endpoint for deployment readiness probes."""
        return {
            "status": "healthy",
            "uptime": time.time() - app.state.stats["start_time"],
        }

    return app


async def _shutdown_app(app: FastAPI) -> None:
    """
    Gracefully shutdown all services.

    Args:
        app: FastAPI application instance
    """
    print("[SHUTDOWN] Initiating graceful shutdown...")

    # Stop protocol servers
    if hasattr(app.state, "protocol_service"):
        try:
            print("[SHUTDOWN] Stopping protocol servers...")
            await app.state.protocol_service.stop_all()
            print("[OK] Protocol servers stopped")
        except Exception as e:
            print(f"[WARNING] Error stopping protocol servers: {e}")

    # Stop timeline player
    if hasattr(app.state, "timeline_player"):
        try:
            print("[SHUTDOWN] Stopping timeline player...")
            if hasattr(app.state.timeline_player, "stop"):
                await app.state.timeline_player.stop()
            print("[OK] Timeline player stopped")
        except Exception as e:
            print(f"[WARNING] Error stopping timeline: {e}")

    # Disconnect all devices
    if hasattr(app.state, "device_service"):
        try:
            print("[SHUTDOWN] Disconnecting devices...")
            device_ids = list(app.state.device_service.devices.keys())
            for device_id in device_ids:
                device = app.state.device_service.devices.get(device_id)
                if device and device.driver:
                    try:
                        if hasattr(device.driver, "disconnect"):
                            if hasattr(device.driver.disconnect, "__await__"):
                                await device.driver.disconnect()
                            else:
                                device.driver.disconnect()
                    except Exception as e:
                        print(f"[WARNING] Error disconnecting {device_id}: {e}")
            print("[OK] Devices disconnected")
        except Exception as e:
            print(f"[WARNING] Error in device shutdown: {e}")

    print("[OK] Shutdown complete")


def _setup_static_files(app: FastAPI, config: ServerConfig) -> None:
    """
    Setup static file serving for web UI.

    Args:
        app: FastAPI application instance
        config: Server configuration
    """
    try:
        ui_root = config.get_ui_path()
        if ui_root.exists() and ui_root.is_dir():
            app.mount("/static", StaticFiles(directory=ui_root), name="static")
            print(f"[OK] Static files mounted from {ui_root}")
        else:
            print(f"[WARNING] UI root not found: {ui_root}")
    except Exception as e:
        print(f"[WARNING] Failed to setup static files: {e}")
