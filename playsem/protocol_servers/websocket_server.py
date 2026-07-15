"""
WebSocket server for receiving sensory effect requests.
"""

import asyncio
import hmac
import json
import logging
import threading
from typing import Optional, Callable

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata
from ..utils.rate_limiter import SlidingWindowLimiter

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for real-time bidirectional communication.

    Provides low-latency effect streaming for web apps and VR applications.
    Supports JSON effect messages and broadcasts events to all clients.

    Example:
        >>> dispatcher = EffectDispatcher(device_manager)
        >>> server = WebSocketServer(
        ...     host="0.0.0.0",
        ...     port=8080,
        ...     dispatcher=dispatcher
        ... )
        >>> await server.start()
        >>> # Server now accepts WebSocket connections on port 8080
        >>> await server.stop()
    """

    def __init__(
        self,
        host: str,
        port: int,
        dispatcher: EffectDispatcher,
        process_managed_queue: bool = False,
        auth_token: Optional[str] = None,
        use_ssl: bool = False,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
        on_client_connected: Optional[Callable[[str], None]] = None,
        on_client_disconnected: Optional[Callable[[str], None]] = None,
        max_message_size: int = 64 * 1024,
        rate_limit_messages: int = 100,
        rate_limit_window: float = 60.0,
        max_connections: int = 100,
    ):
        """
        Initialize WebSocket server.

        Args:
            host: Host address to bind to
                (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default: 8080)
            dispatcher: EffectDispatcher for executing effects
            process_managed_queue: If True, process queued effects when
                dispatcher managed mode is enabled
            auth_token: Optional token for authentication (sent as
                "token" in connect message)
            use_ssl: Enable WSS (secure WebSocket)
            ssl_certfile: Path to SSL certificate file
            ssl_keyfile: Path to SSL private key file
            on_effect_received: Optional callback when effect received
            on_client_connected: Optional callback when client connects
            on_client_disconnected: Optional callback when client
                disconnects
            max_message_size: Maximum message size in bytes (default: 64KB)
            rate_limit_messages: Max messages per client per window (default: 100)
            rate_limit_window: Rate limit window in seconds (default: 60.0)
            max_connections: Maximum concurrent connections (default: 100)
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.process_managed_queue = process_managed_queue
        self.auth_token = auth_token
        self.use_ssl = use_ssl
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.on_effect_received = on_effect_received
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected
        self.max_message_size = max_message_size
        self.max_connections = max_connections
        self._rate_limit_messages = rate_limit_messages
        self._rate_limit_window = rate_limit_window
        self._client_rate_limiters: dict[str, SlidingWindowLimiter] = {}
        self._rate_limiters_lock = threading.Lock()

        self.clients: set = set()  # Connected WebSocket clients
        self._server = None
        self._is_running = False
        self._lock = threading.Lock()

        logger.info(
            f"WebSocket Server initialized - {host}:{port}, "
            f"auth: {'enabled' if auth_token else 'disabled'}, "
            f"ssl: {'enabled' if use_ssl else 'disabled'}, "
            f"max_msg: {max_message_size}B, "
            f"max_conn: {max_connections}, "
            f"rate: {rate_limit_messages}/{rate_limit_window}s"
        )

    async def start(self):
        """
        Start the WebSocket server.

        This is an async method - must be called with await or asyncio.run().
        """
        import websockets

        with self._lock:
            if self._is_running:
                logger.warning("WebSocket Server already running")
                return

        try:
            logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

            # Setup SSL if enabled
            ssl_context = None
            if self.use_ssl and self.ssl_certfile and self.ssl_keyfile:
                import ssl

                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
                logger.info("WebSocket SSL/TLS enabled")

            # Start WebSocket server
            try:
                self._server = await websockets.serve(
                    self._handle_client, self.host, self.port, ssl=ssl_context
                )
            except NotImplementedError:
                logger.error(
                    "websockets.serve() not supported on this platform "
                    "(e.g. Windows without signal handler support)"
                )
                raise RuntimeError(
                    "WebSocket server not supported on this platform"
                ) from None

            with self._lock:
                self._is_running = True

            protocol = "wss" if self.use_ssl else "ws"
            logger.info(
                f"WebSocket Server started on " f"{protocol}://{self.host}:{self.port}"
            )

            # Keep server running
            await self._server.wait_closed()

        except Exception as e:
            logger.error(f"Failed to start WebSocket Server: {e}")
            raise

    async def stop(self):
        """
        Stop the WebSocket server.

        This is an async method - must be called with await.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("WebSocket Server not running")
                return

        try:
            logger.info("Stopping WebSocket Server...")

            # Close all client connections
            if self.clients:
                await asyncio.gather(
                    *[client.close() for client in self.clients],
                    return_exceptions=True,
                )

            # Close server
            if self._server:
                self._server.close()
                await self._server.wait_closed()

            with self._lock:
                self._is_running = False
                self.clients.clear()

            logger.info("WebSocket Server stopped")

        except Exception as e:
            logger.error(f"Error stopping WebSocket Server: {e}")
            raise

    def is_running(self) -> bool:
        """Check if server is running."""
        with self._lock:
            return self._is_running

    async def _handle_client(self, websocket):
        """
        Handle a WebSocket client connection.

        Args:
            websocket: WebSocket connection object
        """
        addr = websocket.remote_address
        client_id = f"{addr[0]}:{addr[1]}"
        authenticated = not self.auth_token  # No auth = auto-authenticated

        # Check connection limit
        with self._lock:
            if len(self.clients) >= self.max_connections:
                logger.warning(
                    f"Connection limit reached ({self.max_connections}), "
                    f"rejecting client {client_id}"
                )
                await websocket.close(
                    code=1013, reason="Server connection limit reached"
                )
                return

        try:
            # Send welcome message
            await websocket.send(
                json.dumps(
                    {
                        "type": "welcome",
                        "message": ("Connected to PythonPlaySEM WebSocket Server"),
                        "version": "0.1.0",
                        "auth_required": bool(self.auth_token),
                    }
                )
            )

            # Handle messages from client
            async for message in websocket:
                # Reject binary frames
                if not isinstance(message, str):
                    logger.warning(
                        f"Binary frame received from {client_id}, closing connection"
                    )
                    await websocket.close(
                        code=1003, reason="Binary frames not supported"
                    )
                    return

                # Validate message size
                if len(message) > self.max_message_size:
                    logger.warning(
                        f"Message too large from {client_id}: "
                        f"{len(message)} bytes (max: {self.max_message_size})"
                    )
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"Message size {len(message)} exceeds maximum {self.max_message_size} bytes",  # noqa: E501
                            }
                        )
                    )
                    await websocket.close(code=1009, reason="Message too large")
                    return

                # Check rate limit
                if not self._check_rate_limit(client_id):
                    logger.warning(f"Rate limit exceeded for client {client_id}")
                    await websocket.send(
                        json.dumps({"type": "error", "message": "Rate limit exceeded"})
                    )
                    await websocket.close(code=1008, reason="Rate limit exceeded")
                    return

                # Check authentication on first message if required
                if not authenticated:
                    try:
                        data = json.loads(message)
                        token = data.get("token")
                        if token and hmac.compare_digest(token, self.auth_token):
                            authenticated = True
                            self.clients.add(websocket)
                            logger.info(f"Client authenticated: {client_id}")

                            if self.on_client_connected:
                                self.on_client_connected(client_id)

                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "auth_response",
                                        "success": True,
                                        "message": ("Authenticated successfully"),
                                    }
                                )
                            )
                            continue
                        else:
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "auth_response",
                                        "success": False,
                                        "message": "Invalid token",
                                    }
                                )
                            )
                            await websocket.close(code=1008, reason="Auth failed")
                            return
                    except json.JSONDecodeError:
                        await websocket.send(
                            json.dumps({"type": "error", "message": "Invalid JSON"})
                        )
                        continue
                else:
                    # Register client if not registered yet (no auth case)
                    if websocket not in self.clients:
                        self.clients.add(websocket)
                        logger.info(f"Client connected: {client_id}")
                        if self.on_client_connected:
                            self.on_client_connected(client_id)

                await self._process_message(websocket, message, client_id)

        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")

        finally:
            # Unregister client
            self.clients.discard(websocket)
            self._cleanup_rate_limiter(client_id)
            logger.info(f"Client disconnected: {client_id}")

            if self.on_client_disconnected:
                self.on_client_disconnected(client_id)

    async def _process_message(self, websocket, message: str, client_id: str):
        """
        Process a message from client.

        Args:
            websocket: Client WebSocket connection
            message: Message string (JSON)
            client_id: Client identifier
        """
        try:
            # Parse message
            data = json.loads(message)
            msg_type = data.get("type", "effect")

            if msg_type == "effect":
                # Parse and execute effect
                effect = self._parse_effect(data)

                if effect:
                    # Call callback if provided
                    if self.on_effect_received:
                        self.on_effect_received(effect)

                    # Dispatch effect
                    # Submit the effect to the async dispatch queue instead of blocking
                    await self.dispatcher.async_dispatch_effect_metadata(effect)
                    if (
                        self.process_managed_queue
                        and getattr(self.dispatcher, "managed_mode", False)
                        and hasattr(self.dispatcher, "process_all_pending")
                    ):
                        self.dispatcher.process_all_pending()

                    # Send success response
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response",
                                "success": True,
                                "effect_type": effect.effect_type,
                                "timestamp": effect.timestamp,
                            }
                        )
                    )

                    # Broadcast effect to all clients
                    await self._broadcast(
                        {
                            "type": "effect_executed",
                            "effect_type": effect.effect_type,
                            "intensity": effect.intensity,
                            "duration": effect.duration,
                        },
                        exclude=websocket,
                    )

                    log_msg = f"Effect '{effect.effect_type}' from {client_id}"
                    logger.info(log_msg)

                else:
                    # Send error response
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response",
                                "success": False,
                                "error": "Invalid effect format",
                            }
                        )
                    )

            elif msg_type == "ping":
                # Respond to ping
                await websocket.send(json.dumps({"type": "pong"}))

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {client_id}: {message}")
            await websocket.send(
                json.dumps({"type": "error", "message": "Invalid JSON format"})
            )

        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    def _parse_effect(self, data: dict) -> Optional[EffectMetadata]:
        """
        Parse effect metadata from message data.

        Args:
            data: Dictionary containing effect data

        Returns:
            EffectMetadata object or None if parsing fails
        """
        try:
            # Check for required field
            effect_type = data.get("effect_type")
            if not effect_type:
                return None

            # Extract effect fields
            return EffectMetadata(
                effect_type=effect_type,
                timestamp=data.get("timestamp", 0),
                duration=data.get("duration", 1000),
                intensity=data.get("intensity", 50),
                location=data.get("location", ""),
                parameters=data.get("parameters", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to parse effect: {e}")
            return None

    async def _broadcast(self, message: dict, exclude=None):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dictionary to broadcast
            exclude: Optional websocket to exclude from broadcast
        """
        if not self.clients:
            return

        message_str = json.dumps(message)

        # Send to all clients except excluded one
        tasks = [
            client.send(message_str) for client in self.clients if client != exclude
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _check_rate_limit(self, client_id: str) -> bool:
        """
        Check if a client has exceeded their rate limit.

        Args:
            client_id: Client identifier

        Returns:
            True if request is allowed, False if rate limited
        """
        with self._rate_limiters_lock:
            if client_id not in self._client_rate_limiters:
                self._client_rate_limiters[client_id] = SlidingWindowLimiter(
                    max_requests=self._rate_limit_messages,
                    window_seconds=self._rate_limit_window,
                )

            limiter = self._client_rate_limiters[client_id]
            return limiter.allow(client_id)

    def _cleanup_rate_limiter(self, client_id: str):
        """
        Clean up rate limiter for a disconnected client.

        Args:
            client_id: Client identifier
        """
        with self._rate_limiters_lock:
            if client_id in self._client_rate_limiters:
                del self._client_rate_limiters[client_id]

    async def broadcast_effect(self, effect: EffectMetadata):
        """
        Broadcast an effect to all connected clients.

        Useful for server-side triggered effects.

        Args:
            effect: EffectMetadata to broadcast
        """
        await self._broadcast(
            {
                "type": "effect_triggered",
                "effect_type": effect.effect_type,
                "timestamp": effect.timestamp,
                "duration": effect.duration,
                "intensity": effect.intensity,
                "location": effect.location,
                "parameters": effect.parameters,
            }
        )
