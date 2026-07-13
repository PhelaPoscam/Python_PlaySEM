"""
CoAP server for receiving sensory effect requests.
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable, Dict, Any

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata, EffectMetadataParser
from ..utils.rate_limiter import SlidingWindowLimiter


logger = logging.getLogger(__name__)


class CoAPServer:
    """
    CoAP server for IoT-friendly constrained protocol.

    Provides lightweight protocol for resource-constrained devices.

    Implemented using aiocoap (asyncio-based CoAP library).
    """

    def __init__(
        self,
        host: str,
        port: int,
        dispatcher: EffectDispatcher,
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
        started_event: Optional[asyncio.Event] = None,
        max_payload_size: int = 64 * 1024,  # 64 KB default
        rate_limit_requests: int = 100,  # requests per window
        rate_limit_window: float = 60.0,  # seconds
    ):
        """
        Initialize CoAP server.

        Args:
            host: Host address to bind to
                (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default CoAP port: 5683)
            dispatcher: EffectDispatcher for executing effects
            on_effect_received: Optional callback when effect received
            started_event: asyncio.Event to signal when server is started
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.on_effect_received = on_effect_received
        self.started_event = started_event
        self.max_payload_size = max_payload_size
        self.rate_limiter = SlidingWindowLimiter(
            max_requests=rate_limit_requests, window_seconds=rate_limit_window
        )

        self._context = None
        self._site = None
        self._is_running = False
        self._lock = threading.Lock()

        logger.info(f"CoAP Server initialized - {host}:{port}")

    async def start(self):
        """
        Start the CoAP server.

        This is an async method - must be called with await or asyncio.run().
        """
        import aiocoap.resource as resource
        from aiocoap import Context

        with self._lock:
            if self._is_running:
                logger.warning("CoAP Server already running")
                return

        try:
            logger.info(f"Starting CoAP server on {self.host}:{self.port}")

            class EffectsResource(resource.Resource):
                def __init__(self, outer: "CoAPServer"):
                    super().__init__()
                    self._outer = outer
                    self.content_type = 50  # application/json

                async def render_post(self, request):
                    try:
                        # Rate limit check
                        client_ip = getattr(
                            request.remote, "host", None
                        ) or str(request.remote)
                        if not self._outer.rate_limiter.allow(client_ip):
                            logger.warning(
                                f"CoAP rate limit exceeded for client {client_ip}"
                            )
                            return self._outer._json_response(
                                {
                                    "success": False,
                                    "error": "Rate limit exceeded",
                                },
                                code="BAD_REQUEST",
                            )

                        # Payload size check
                        if len(request.payload) > self._outer.max_payload_size:
                            logger.warning(
                                f"CoAP payload size {len(request.payload)} "
                                f"exceeds limit {self._outer.max_payload_size} "
                                f"from {client_ip}"
                            )
                            return self._outer._json_response(
                                {
                                    "success": False,
                                    "error": "Payload too large",
                                },
                                code="BAD_REQUEST",
                            )

                        payload = request.payload.decode("utf-8")
                        effect = self._outer._parse_effect(payload)
                        if not effect:
                            response = {
                                "success": False,
                                "error": "Invalid effect format",
                            }
                            return self._outer._json_response(
                                response, code="BAD_REQUEST"
                            )

                        # Callback
                        if self._outer.on_effect_received:
                            self._outer.on_effect_received(effect)

                        # Dispatch effect
                        # Submit the effect to the async dispatch queue
                        await self._outer.dispatcher.async_dispatch_effect_metadata(
                            effect
                        )

                        resp = {
                            "success": True,
                            "effect_type": effect.effect_type,
                            "timestamp": effect.timestamp,
                        }
                        return self._outer._json_response(resp)
                    except Exception as e:
                        logger.error(f"CoAP POST error: {e}")
                        return self._outer._json_response(
                            {"success": False, "error": str(e)},
                            code="INTERNAL_SERVER_ERROR",
                        )

            # Build resource site
            site = resource.Site()
            site.add_resource(["effects"], EffectsResource(self))

            # Create server context bound to host/port
            bind = (self.host, int(self.port))
            self._context = await Context.create_server_context(
                site, bind=bind
            )
            self._site = site
            with self._lock:
                self._is_running = True

            # Small delay to ensure UDP socket readiness, especially on Windows
            await asyncio.sleep(0.2)
            if self.started_event:
                self.started_event.set()

            logger.info(
                f"CoAP Server started on " f"coap://{self.host}:{self.port}"
            )

        except Exception as e:
            logger.error(f"Failed to start CoAP Server: {e}")
            raise

    async def stop(self):
        """
        Stop the CoAP server.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("CoAP Server not running")
                return

        try:
            if self._context is not None:
                await self._context.shutdown()
            with self._lock:
                self._is_running = False
                self._context = None
                self._site = None
            logger.info("CoAP Server stopped")
        except Exception as e:
            logger.error(f"Error stopping CoAP Server: {e}")
            raise

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def _parse_effect(self, payload: str) -> Optional[EffectMetadata]:
        """Parse effect from JSON or YAML payload string."""
        try:
            return EffectMetadataParser.parse_json(payload)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            try:
                return EffectMetadataParser.parse_yaml(payload)
            except Exception as e:
                logger.warning(f"Failed to parse CoAP payload: {e}")
                return None

    def _json_response(self, obj: Dict[str, Any], code: str = "CHANGED"):
        """Create an aiocoap JSON response message with given code."""
        from aiocoap import Message, Code

        payload = json.dumps(obj).encode("utf-8")
        code_map = {
            "CHANGED": Code.CHANGED,
            "CONTENT": Code.CONTENT,
            "CREATED": Code.CREATED,
            "BAD_REQUEST": Code.BAD_REQUEST,
            "INTERNAL_SERVER_ERROR": Code.INTERNAL_SERVER_ERROR,
        }
        return Message(code=code_map.get(code, Code.CHANGED), payload=payload)
