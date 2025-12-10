"""
HTTP server for receiving sensory effect requests.
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable, Dict, Any

from fastapi import (
    FastAPI,
    HTTPException,
    Security,
    Depends,
    status,
    Body,
)
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata


logger = logging.getLogger(__name__)


class HTTPServer:
    """
    HTTP REST API server for sensory effect requests.

    Provides RESTful endpoints for submitting effects, checking status,
    and querying device information. Uses FastAPI for async operation
    and automatic OpenAPI documentation.

    Endpoints:
        POST /api/effects       - Submit effect metadata
        GET  /api/status        - Server health check
        GET  /api/devices       - List connected devices
        GET  /docs              - Interactive API documentation

    Example:
        >>> dispatcher = EffectDispatcher(device_manager)
        >>> server = HTTPServer(
        ...     host="0.0.0.0",
        ...     port=8080,
        ...     dispatcher=dispatcher,
        ...     api_key="secret123"
        ... )
        >>> await server.start()
        >>> # Server running at http://localhost:8080
        >>> await server.stop()
    """

    def __init__(
        self,
        host: str,
        port: int,
        dispatcher: EffectDispatcher,
        api_key: Optional[str] = None,
        cors_origins: Optional[list] = None,
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
        on_effect_broadcast: Optional[Callable] = None,
    ):
        """
        Initialize HTTP REST server.

        Args:
            host: Server bind address (use "0.0.0.0" for all interfaces)
            port: Server port (default: 8080)
            dispatcher: EffectDispatcher instance for effect execution
            api_key: Optional API key for authentication (X-API-Key header)
            cors_origins: List of allowed CORS origins (None = allow all)
            on_effect_received: Optional callback when effect is received
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.api_key = api_key
        self.cors_origins = cors_origins or ["*"]
        self.on_effect_received = on_effect_received
        self.on_effect_broadcast = on_effect_broadcast

        self._server = None
        self._app = None
        self._setup_app()

        logger.info(
            f"HTTP Server initialized - {host}:{port}, "
            f"auth: {'enabled' if api_key else 'disabled'}"
        )

    def _setup_app(self):
        """Setup FastAPI application with routes and middleware."""
        # Store for use in routes
        self._fastapi = FastAPI
        self._HTTPException = HTTPException
        self._Security = Security
        self._Depends = Depends
        self._status = status
        self._APIKeyHeader = APIKeyHeader
        self._uvicorn = uvicorn

        # Create app
        self._app = FastAPI(
            title="PlaySEM REST API",
            description="Sensory Effect Media playback system",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # Add CORS middleware
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Define request/response models
        class EffectRequest(BaseModel):
            effect_type: str = Field(..., description="Type of effect")
            timestamp: float = Field(0.0, description="Effect timestamp in ms")
            duration: float = Field(
                1000.0, description="Effect duration in ms"
            )
            intensity: int = Field(
                100, ge=0, le=255, description="Effect intensity"
            )
            location: Optional[str] = Field(
                None, description="Effect location"
            )
            parameters: Optional[Dict[str, Any]] = Field(
                None, description="Additional parameters"
            )

        class EffectResponse(BaseModel):
            success: bool
            message: str
            effect_id: Optional[str] = None

        class StatusResponse(BaseModel):
            status: str
            version: str
            uptime_seconds: float
            effects_processed: int

        class DeviceInfo(BaseModel):
            device_id: str
            device_type: str
            status: str

        class DevicesResponse(BaseModel):
            devices: list
            count: int

        # Store models for use in routes
        self._EffectRequest = EffectRequest
        self._EffectResponse = EffectResponse
        self._StatusResponse = StatusResponse
        self._DeviceInfo = DeviceInfo
        self._DevicesResponse = DevicesResponse

        # Setup API key security if enabled
        if self.api_key:
            api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

            async def verify_api_key(key: str = Security(api_key_header)):
                if key != self.api_key:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid API key",
                    )
                return key

            self._security_dependency = Depends(verify_api_key)
        else:
            self._security_dependency = None

        # Track server stats
        self._start_time = None
        self._effects_processed = 0

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register API routes."""

        @self._app.post(
            "/api/effects",
            response_model=self._EffectResponse,
            summary="Submit effect",
            description="Submit a sensory effect for execution",
        )
        async def submit_effect(
            effect: self._EffectRequest = Body(...),
            _auth=self._security_dependency,
        ):
            try:
                # Create EffectMetadata from request
                metadata = EffectMetadata(
                    effect_type=effect.effect_type,
                    timestamp=effect.timestamp,
                    duration=effect.duration,
                    intensity=effect.intensity,
                    location=effect.location,
                    parameters=effect.parameters or {},
                )

                # Dispatch effect
                self.dispatcher.dispatch_effect_metadata(metadata)
                self._effects_processed += 1

                # Call broadcast callback if provided
                if self.on_effect_broadcast:
                    await self.on_effect_broadcast(metadata, "http_broadcast")

                # Call local callback if provided
                if self.on_effect_received:
                    self.on_effect_received(metadata)

                logger.info(f"HTTP effect received: {effect.effect_type}")

                return self._EffectResponse(
                    success=True,
                    message="Effect dispatched successfully",
                    effect_id=(
                        f"{effect.effect_type}_{self._effects_processed}"
                    ),
                )
            except Exception as e:
                logger.error(f"Effect dispatch error: {e}")
                raise self._HTTPException(
                    status_code=self._status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

        @self._app.get(
            "/api/status",
            response_model=self._StatusResponse,
            summary="Server status",
            description="Get server health and statistics",
        )
        async def get_status():
            import time

            uptime = (
                time.time() - self._start_time if self._start_time else 0.0
            )
            return self._StatusResponse(
                status="running",
                version="0.1.0",
                uptime_seconds=uptime,
                effects_processed=self._effects_processed,
            )

        @self._app.get(
            "/api/devices",
            response_model=self._DevicesResponse,
            summary="List devices",
            description="Get list of connected devices",
            dependencies=[self._security_dependency] if self.api_key else [],
        )
        async def get_devices():
            # Mock device list (extend with real device manager integration)
            devices = [
                {
                    "device_id": "mock_light_1",
                    "device_type": "light",
                    "status": "connected",
                },
                {
                    "device_id": "mock_wind_1",
                    "device_type": "wind",
                    "status": "connected",
                },
            ]
            return self._DevicesResponse(devices=devices, count=len(devices))

        @self._app.get(
            "/ui/capabilities",
            response_class=HTMLResponse,
            summary="Capabilities UI",
            description="Simple UI to query device capabilities",
        )
        async def get_capabilities_ui():
            html = (
                "<!doctype html>\n"
                '<html><head><meta charset="utf-8">'
                "<title>Device Capabilities</title>"
                "<style>"
                "body{font-family:sans-serif;padding:16px;max-width:960px;margin:auto}"
                "label,select,input,button{font-size:14px;margin:4px 6px 12px 0}"
                ".row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}"
                "pre{background:#f5f5f5;padding:12px;overflow:auto;"
                "border:1px solid #ddd;border-radius:6px}"
                "small{color:#666}"
                "</style></head><body>"
                "<h2>Device Capabilities</h2>"
                "<div class='row'>"
                '<label for="deviceSelect">Device:</label>'
                '<select id="deviceSelect"><option value="">Loading…</option></select>'
                '<input id="did" placeholder="or enter device id" '
                'style="min-width:200px">'
                '<button id="btn">Fetch</button>'
                "</div>"
                "<small>Tip: pick from devices or type an id "
                "(e.g., mock_light_1)</small>"
                '<pre id="out">(result appears here)</pre>'
                "<script>"
                "const select=document.getElementById('deviceSelect');"
                "const input=document.getElementById('did');"
                "const btn=document.getElementById('btn');"
                "const out=document.getElementById('out');"
                "async function loadDevices(){ "
                "  try{"
                "    const r=await fetch('/api/devices');"
                "    const j=await r.json();"
                "    select.innerHTML='';"
                "    const empty=document.createElement('option');"
                "    empty.value=''; empty.text='— select —';"
                "    select.appendChild(empty);"
                "    (j.devices||[]).forEach(d=>{"
                "      const opt=document.createElement('option');"
                "      opt.value=d.device_id;"
                "      opt.text=`${d.device_id} (${d.device_type})`;"
                "      select.appendChild(opt);"
                "    });"
                "  }catch(e){ select.innerHTML='<option>Error</option>'; }"
                "}"
                "select.onchange=()=>{ if(select.value) input.value=select.value; }"
                "btn.onclick=async()=>{"
                "  const id=(select.value||input.value||'').trim();"
                "  if(!id){"
                "    out.textContent='Please select or enter a device id.';"
                "    return;"
                "  }"
                "  out.textContent='Loading…';"
                "  try{"
                "    const res=await fetch('/api/capabilities/' + "
                "      encodeURIComponent(id));"
                "    const txt=await res.text();"
                "    try{ out.textContent=JSON.stringify(JSON.parse(txt),null,2); }"
                "    catch{ out.textContent=txt; }"
                "  }catch(e){ out.textContent=String(e); }"
                "}"
                "loadDevices();"
                "</script>"
                "</body></html>"
            )
            return HTMLResponse(content=html, status_code=200)

        @self._app.get(
            "/api/capabilities/{device_id}",
            summary="Get device capabilities",
            description="Get detailed capabilities for a specific device",
            dependencies=[self._security_dependency] if self.api_key else [],
        )
        async def get_device_capabilities(device_id: str):
            """Get capabilities for a specific device."""
            try:
                # Get capabilities from device driver
                device_manager = self.dispatcher.device_manager
                if device_manager and device_manager.driver:
                    caps = device_manager.driver.get_capabilities(device_id)
                    if caps:
                        return caps
                    else:
                        raise self._HTTPException(
                            status_code=self._status.HTTP_404_NOT_FOUND,
                            detail=(
                                f"Capabilities not available for "
                                f"device: {device_id}"
                            ),
                        )
                else:
                    raise self._HTTPException(
                        status_code=self._status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="No device manager or driver available",
                    )
            except self._HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting capabilities: {e}")
                raise self._HTTPException(
                    status_code=self._status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e),
                )

    async def start(self):
        """
        Start the HTTP server.

        Runs the FastAPI application with uvicorn.
        """
        import time

        self._start_time = time.time()

        logger.info(f"Starting HTTP server at http://{self.host}:{self.port}")
        logger.info(
            f"API documentation available at "
            f"http://{self.host}:{self.port}/docs"
        )

        config = self._uvicorn.Config(
            self._app, host=self.host, port=self.port, log_level="info"
        )
        self._server = self._uvicorn.Server(config)
        await self._server.serve()

    async def stop(self):
        """Stop the HTTP server."""
        if self._server:
            logger.info("Stopping HTTP server")
            self._server.should_exit = True
            await asyncio.sleep(0.1)
        logger.info("HTTP server stopped")
