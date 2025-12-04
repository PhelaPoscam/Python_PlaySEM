"""
WebSocket server for receiving sensory effect requests.
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata


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
        auth_token: Optional[str] = None,
        use_ssl: bool = False,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
        on_client_connected: Optional[Callable[[str], None]] = None,
        on_client_disconnected: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize WebSocket server.

        Args:
            host: Host address to bind to
                (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default: 8080)
            dispatcher: EffectDispatcher for executing effects
            auth_token: Optional token for authentication (sent as
                "token" in connect message)
            use_ssl: Enable WSS (secure WebSocket)
            ssl_certfile: Path to SSL certificate file
            ssl_keyfile: Path to SSL private key file
            on_effect_received: Optional callback when effect received
            on_client_connected: Optional callback when client connects
            on_client_disconnected: Optional callback when client
                disconnects
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.auth_token = auth_token
        self.use_ssl = use_ssl
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.on_effect_received = on_effect_received
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected

        self.clients = set()  # Connected WebSocket clients
        self._server = None
        self._is_running = False
        self._lock = threading.Lock()

        logger.info(
            f"WebSocket Server initialized - {host}:{port}, "
            f"auth: {'enabled' if auth_token else 'disabled'}, "
            f"ssl: {'enabled' if use_ssl else 'disabled'}"
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
            logger.info(
                f"Starting WebSocket server on {self.host}:{self.port}"
            )

            # Setup SSL if enabled
            ssl_context = None
            if self.use_ssl and self.ssl_certfile and self.ssl_keyfile:
                import ssl

                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(
                    self.ssl_certfile, self.ssl_keyfile
                )
                logger.info("WebSocket SSL/TLS enabled")

            # Start WebSocket server
            self._server = await websockets.serve(
                self._handle_client, self.host, self.port, ssl=ssl_context
            )

            with self._lock:
                self._is_running = True

            protocol = "wss" if self.use_ssl else "ws"
            logger.info(
                f"WebSocket Server started on "
                f"{protocol}://{self.host}:{self.port}"
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

        try:
            # Send welcome message
            await websocket.send(
                json.dumps(
                    {
                        "type": "welcome",
                        "message": (
                            "Connected to PythonPlaySEM WebSocket Server"
                        ),
                        "version": "0.1.0",
                        "auth_required": bool(self.auth_token),
                    }
                )
            )

            # Handle messages from client
            async for message in websocket:
                # Check authentication on first message if required
                if not authenticated:
                    try:
                        data = json.loads(message)
                        token = data.get("token")
                        if token == self.auth_token:
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
                                        "message": (
                                            "Authenticated successfully"
                                        ),
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
                            await websocket.close(
                                code=1008, reason="Auth failed"
                            )
                            return
                    except json.JSONDecodeError:
                        await websocket.send(
                            json.dumps(
                                {"type": "error", "message": "Invalid JSON"}
                            )
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
                    self.dispatcher.dispatch_effect_metadata(effect)

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
            await websocket.send(
                json.dumps({"type": "error", "message": str(e)})
            )

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
            client.send(message_str)
            for client in self.clients
            if client != exclude
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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
