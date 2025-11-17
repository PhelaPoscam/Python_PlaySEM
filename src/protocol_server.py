"""
Protocol servers for receiving sensory effect requests.

This module implements various protocol servers (MQTT, WebSocket, etc.)
that can receive effect requests from external applications and dispatch
them to the effect dispatcher.
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable, Dict, Any
import paho.mqtt.client as mqtt

from .effect_dispatcher import EffectDispatcher
from .effect_metadata import EffectMetadata, EffectMetadataParser


logger = logging.getLogger(__name__)


class MQTTServer:
    """
    MQTT server for receiving sensory effect requests.

    Subscribes to MQTT topics and processes incoming effect metadata,
    dispatching effects to connected devices through the EffectDispatcher.

    Example:
        >>> dispatcher = EffectDispatcher(device_manager)
        >>> server = MQTTServer(
        ...     broker_address="localhost",
        ...     dispatcher=dispatcher,
        ...     subscribe_topic="effects/#"
        ... )
        >>> server.start()
        >>> # Server now listens for effects on "effects/*" topics
        >>> server.stop()
    """

    def __init__(
        self,
        broker_address: str,
        dispatcher: EffectDispatcher,
        subscribe_topic: str = "effects/#",
        status_topic: str = "status",
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        tls_ca_certs: Optional[str] = None,
        tls_certfile: Optional[str] = None,
        tls_keyfile: Optional[str] = None,
        reconnect_on_failure: bool = True,
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
    ):
        """
        Initialize MQTT server.

        Args:
            broker_address: MQTT broker hostname/IP
            dispatcher: EffectDispatcher instance for effect execution
            subscribe_topic: MQTT topic pattern to subscribe to
                (supports wildcards)
            status_topic: Topic for publishing server status messages
            port: MQTT broker port (default: 1883, 8883 for TLS)
            client_id: Optional MQTT client ID (auto-generated if None)
            username: Optional username for authentication
            password: Optional password for authentication
            use_tls: Enable TLS/SSL encryption
            tls_ca_certs: Path to CA certificates file for TLS
            tls_certfile: Path to client certificate for TLS
            tls_keyfile: Path to client private key for TLS
            reconnect_on_failure: Auto-reconnect on connection loss
            on_effect_received: Optional callback when effect is received
        """
        self.broker_address = broker_address
        self.port = port
        self.dispatcher = dispatcher
        self.subscribe_topic = subscribe_topic
        self.status_topic = status_topic
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.reconnect_on_failure = reconnect_on_failure
        self.on_effect_received = on_effect_received

        # Create MQTT client
        self.client = mqtt.Client(client_id=client_id or "playsem_server")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Setup authentication
        if username and password:
            self.client.username_pw_set(username, password)
            logger.info("MQTT authentication enabled")

        # Setup TLS
        if use_tls:
            import ssl

            self.client.tls_set(
                ca_certs=tls_ca_certs,
                certfile=tls_certfile,
                keyfile=tls_keyfile,
                cert_reqs=ssl.CERT_REQUIRED if tls_ca_certs else ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLS,
            )
            logger.info("MQTT TLS/SSL enabled")

        # Enable automatic reconnection
        if reconnect_on_failure:
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)

        self._is_running = False
        self._lock = threading.Lock()
        self._reconnect_attempts = 0

        logger.info(
            f"MQTT Server initialized - broker: {broker_address}:{port}, "
            f"topic: {subscribe_topic}, auth: "
            f"{'enabled' if username else 'disabled'}, "
            f"tls: {'enabled' if use_tls else 'disabled'}"
        )

    def start(self):
        """
        Start the MQTT server.

        Connects to broker and begins listening for effect requests.
        """
        with self._lock:
            if self._is_running:
                logger.warning("MQTT Server already running")
                return

            try:
                logger.info(
                    f"Connecting to MQTT broker at "
                    f"{self.broker_address}:{self.port}"
                )
                self.client.connect(
                    self.broker_address, self.port, keepalive=60
                )

                # Start network loop in background thread
                self.client.loop_start()

                self._is_running = True
                logger.info("MQTT Server started successfully")

            except Exception as e:
                logger.error(f"Failed to start MQTT Server: {e}")
                raise

    def stop(self):
        """
        Stop the MQTT server.

        Disconnects from broker and stops listening.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("MQTT Server not running")
                return

            try:
                logger.info("Stopping MQTT Server...")

                # Publish offline status
                self.client.publish(
                    self.status_topic,
                    json.dumps({"status": "offline"}),
                    retain=True,
                )

                # Stop loop and disconnect
                self.client.loop_stop()
                self.client.disconnect()

                self._is_running = False
                logger.info("MQTT Server stopped")

            except Exception as e:
                logger.error(f"Error stopping MQTT Server: {e}")
                raise

    def is_running(self) -> bool:
        """Check if server is running."""
        with self._lock:
            return self._is_running

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback when connected to MQTT broker.

        Args:
            rc: Connection result code (0 = success)
        """
        if rc == 0:
            logger.info(
                f"Connected to MQTT broker, subscribing to "
                f"{self.subscribe_topic}"
            )

            # Subscribe to effect topics
            client.subscribe(self.subscribe_topic)

            # Publish online status
            client.publish(
                self.status_topic,
                json.dumps({"status": "online", "version": "0.1.0"}),
                retain=True,
            )
        else:
            logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}"
            )

    def _on_disconnect(self, client, userdata, rc):
        """
        Callback when disconnected from MQTT broker.

        Args:
            rc: Disconnect reason code
        """
        if rc != 0:
            self._reconnect_attempts += 1
            logger.warning(
                f"Unexpected disconnect from MQTT broker (code: {rc}), "
                f"attempt #{self._reconnect_attempts}"
            )
            if self.reconnect_on_failure:
                logger.info("Attempting to reconnect...")
            else:
                self._is_running = False
        else:
            logger.info("Disconnected from MQTT broker")
            self._is_running = False

    def _on_message(self, client, userdata, msg):
        """
        Callback when message is received.

        Parses effect metadata and dispatches to devices.

        Args:
            msg: MQTT message object
        """
        topic = msg.topic if hasattr(msg, "topic") else "unknown"
        try:
            payload = msg.payload.decode("utf-8")

            logger.debug(f"Received message on topic '{topic}': {payload}")

            # Parse effect metadata from JSON/YAML payload
            effect = self._parse_effect(payload)

            if effect:
                # Call callback if provided
                if self.on_effect_received:
                    self.on_effect_received(effect)

                # Dispatch effect
                self.dispatcher.dispatch_effect_metadata(effect)

                # Publish success response
                self._publish_response(topic, effect, success=True)

                logger.info(
                    f"Effect '{effect.effect_type}' executed successfully"
                )
            else:
                logger.warning(
                    f"Failed to parse effect from payload: {payload}"
                )
                self._publish_response(
                    topic, None, success=False, error="Invalid effect format"
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._publish_response(topic, None, success=False, error=str(e))

    def _parse_effect(self, payload: str) -> Optional[EffectMetadata]:
        """
        Parse effect metadata from payload string.

        Supports both JSON and YAML formats.

        Args:
            payload: String payload (JSON or YAML)

        Returns:
            EffectMetadata object or None if parsing fails
        """
        try:
            # Try JSON first - parse_json expects a string
            return EffectMetadataParser.parse_json(payload)

        except (json.JSONDecodeError, ValueError):
            # Try YAML if JSON fails
            try:
                return EffectMetadataParser.parse_yaml(payload)
            except Exception as e:
                logger.warning(f"Failed to parse as YAML: {e}")
                return None

    def _publish_response(
        self,
        request_topic: str,
        effect: Optional[EffectMetadata],
        success: bool,
        error: Optional[str] = None,
    ):
        """
        Publish execution response.

        Args:
            request_topic: Original request topic
            effect: Effect that was executed (or None if failed)
            success: Whether execution succeeded
            error: Optional error message
        """
        try:
            # Create response topic
            # (e.g., "effects/light" -> "effects/light/response")
            response_topic = f"{request_topic}/response"

            response = {
                "success": success,
                "timestamp": effect.timestamp if effect else None,
                "effect_type": effect.effect_type if effect else None,
            }

            if error:
                response["error"] = error

            self.client.publish(response_topic, json.dumps(response))

        except Exception as e:
            logger.error(f"Error publishing response: {e}")


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
    ):
        """
        Initialize CoAP server.

        Args:
            host: Host address to bind to
                (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default CoAP port: 5683)
            dispatcher: EffectDispatcher for executing effects
            on_effect_received: Optional callback when effect received
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.on_effect_received = on_effect_received

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
                        self._outer.dispatcher.dispatch_effect_metadata(effect)

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
            bind = (self.host, self.port)
            self._context = await Context.create_server_context(
                site, bind=bind
            )
            self._site = site
            with self._lock:
                self._is_running = True
            logger.info(
                f"CoAP Server started on " f"coap://{self.host}:{self.port}"
            )

            # Keep running until explicitly stopped
            await asyncio.get_running_loop().create_future()
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
        except (json.JSONDecodeError, ValueError):
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


class UPnPServer:
    """
    UPnP server for device discovery and service advertisement using SSDP.

    Provides automatic device discovery compatible with original PlaySEM
    clients. Advertises the PlaySEM service on the local network and
    responds to M-SEARCH discovery requests.

    Example:
        >>> dispatcher = EffectDispatcher(device_manager)
        >>> server = UPnPServer(
        ...     friendly_name="PlaySEM Server",
        ...     dispatcher=dispatcher,
        ...     location_url="http://192.168.1.100:8080/description.xml"
        ... )
        >>> await server.start()
        >>> # Server now advertises on SSDP multicast
        >>> await server.stop()
    """

    # UPnP/SSDP constants
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 3  # Max wait time for responses
    UPNP_VERSION = "1.1"

    def __init__(
        self,
        friendly_name: str = "PlaySEM Server",
        dispatcher: Optional[EffectDispatcher] = None,
        uuid: Optional[str] = None,
        location_url: Optional[str] = None,
        manufacturer: str = "PlaySEM",
        model_name: str = "PlaySEM Python Server",
        model_version: str = "1.0",
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
    ):
        """
        Initialize UPnP server.

        Args:
            friendly_name: Human-readable device name
            dispatcher: EffectDispatcher instance for effect execution
            uuid: Device UUID (auto-generated if None)
            location_url: URL to device description XML
            manufacturer: Device manufacturer name
            model_name: Device model name
            model_version: Device model version
            on_effect_received: Optional callback when effect is received
        """
        import uuid as uuid_module

        self.friendly_name = friendly_name
        self.dispatcher = dispatcher
        self.uuid = uuid or f"uuid:{uuid_module.uuid4()}"
        self.location_url = (
            location_url or "http://0.0.0.0:8080/description.xml"
        )
        self.manufacturer = manufacturer
        self.model_name = model_name
        self.model_version = model_version
        self.on_effect_received = on_effect_received

        # Service type for PlaySEM
        self.service_type = "urn:schemas-upnp-org:service:PlaySEM:1"
        self.device_type = "urn:schemas-upnp-org:device:PlaySEM:1"

        self._is_running = False
        self._transport = None
        self._advertisement_task = None
        self._lock = threading.Lock()

        logger.info(
            f"UPnP Server initialized - "
            f"device: {friendly_name}, uuid: {self.uuid}"
        )

    async def start(self):
        """
        Start the UPnP server.

        Begins advertising the device via SSDP and responds to
        discovery requests.
        """
        with self._lock:
            if self._is_running:
                logger.warning("UPnP Server already running")
                return

        try:
            logger.info(
                f"Starting UPnP Server on "
                f"{self.SSDP_ADDR}:{self.SSDP_PORT}"
            )

            # Create UDP socket for SSDP multicast
            loop = asyncio.get_event_loop()

            class SSDPProtocol(asyncio.DatagramProtocol):
                def __init__(self, server):
                    self.server = server

                def connection_made(self, transport):
                    self.transport = transport
                    self.server._transport = transport

                def datagram_received(self, data, addr):
                    asyncio.create_task(
                        self.server._handle_datagram(data, addr)
                    )

                def error_received(self, exc):
                    logger.error(f"SSDP protocol error: {exc}")

                def connection_lost(self, exc):
                    logger.info("SSDP connection closed")

            # Create multicast socket
            import socket
            import struct

            # Create and configure socket manually for multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.SSDP_PORT))

            # Join multicast group
            mreq = struct.pack(
                "4sl", socket.inet_aton(self.SSDP_ADDR), socket.INADDR_ANY
            )
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Create endpoint with pre-configured socket
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: SSDPProtocol(self), sock=sock
            )

            # Start periodic advertisements
            self._advertisement_task = asyncio.create_task(
                self._advertise_periodically()
            )

            with self._lock:
                self._is_running = True

            logger.info("UPnP Server started successfully")

            # Send initial NOTIFY alive messages
            await self._send_notify_alive()

        except Exception as e:
            logger.error(f"Failed to start UPnP Server: {e}")
            raise

    async def stop(self):
        """
        Stop the UPnP server.

        Sends byebye notifications and closes the SSDP socket.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("UPnP Server not running")
                return

        try:
            logger.info("Stopping UPnP Server")

            # Send NOTIFY byebye
            await self._send_notify_byebye()

            # Cancel advertisement task
            if self._advertisement_task:
                self._advertisement_task.cancel()
                try:
                    await self._advertisement_task
                except asyncio.CancelledError:
                    pass

            # Close transport
            if self._transport:
                self._transport.close()

            with self._lock:
                self._is_running = False
                self._transport = None

            logger.info("UPnP Server stopped")

        except Exception as e:
            logger.error(f"Error stopping UPnP Server: {e}")
            raise

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    async def _handle_datagram(self, data: bytes, addr: tuple):
        """Handle incoming SSDP datagram."""
        try:
            message = data.decode("utf-8")

            # Check if it's an M-SEARCH request
            if message.startswith("M-SEARCH"):
                logger.debug(f"Received M-SEARCH from {addr[0]}:{addr[1]}")

                # Parse search target
                st_line = [
                    line
                    for line in message.split("\r\n")
                    if line.startswith("ST:")
                ]
                if not st_line:
                    return

                search_target = st_line[0].split(":", 1)[1].strip()

                # Respond if searching for our device/service
                # or all devices
                if search_target in [
                    "ssdp:all",
                    self.device_type,
                    self.service_type,
                    self.uuid,
                ]:
                    await self._send_msearch_response(addr, search_target)

        except Exception as e:
            logger.error(f"Error handling SSDP datagram: {e}")

    async def _send_msearch_response(self, addr: tuple, search_target: str):
        """Send M-SEARCH response to a discovery request."""
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"CACHE-CONTROL: max-age=1800\r\n"
            f"EXT:\r\n"
            f"LOCATION: {self.location_url}\r\n"
            f"SERVER: Python/3.14 UPnP/{self.UPNP_VERSION} "
            f"PlaySEM/{self.model_version}\r\n"
            f"ST: {search_target}\r\n"
            f"USN: {self.uuid}::{search_target}\r\n"
            f"\r\n"
        )

        if self._transport:
            self._transport.sendto(response.encode("utf-8"), addr)
            logger.info(
                f"Sent M-SEARCH response to {addr[0]}:{addr[1]} "
                f"for {search_target}"
            )

    async def _send_notify_alive(self):
        """Send NOTIFY alive announcements."""
        targets = [
            "upnp:rootdevice",
            self.uuid,
            self.device_type,
            self.service_type,
        ]

        for target in targets:
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"CACHE-CONTROL: max-age=1800\r\n"
                f"LOCATION: {self.location_url}\r\n"
                f"NT: {target}\r\n"
                f"NTS: ssdp:alive\r\n"
                f"SERVER: Python/3.14 "
                f"UPnP/{self.UPNP_VERSION} "
                f"PlaySEM/{self.model_version}\r\n"
                f"USN: {self.uuid}::{target}\r\n"
                f"\r\n"
            )

            if self._transport:
                self._transport.sendto(
                    notify.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )

        logger.info("Sent NOTIFY alive announcements")

    async def _send_notify_byebye(self):
        """Send NOTIFY byebye announcements."""
        targets = [
            "upnp:rootdevice",
            self.uuid,
            self.device_type,
            self.service_type,
        ]

        for target in targets:
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"NT: {target}\r\n"
                f"NTS: ssdp:byebye\r\n"
                f"USN: {self.uuid}::{target}\r\n"
                f"\r\n"
            )

            if self._transport:
                self._transport.sendto(
                    notify.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )

        logger.info("Sent NOTIFY byebye announcements")

    async def _advertise_periodically(self):
        """Periodically send NOTIFY alive messages (every 15 minutes)."""
        try:
            while True:
                await asyncio.sleep(900)  # 15 minutes
                if self._is_running:
                    await self._send_notify_alive()
        except asyncio.CancelledError:
            pass

    def get_device_description_xml(self) -> str:
        """
        Generate UPnP device description XML.

        Returns:
            XML string describing the device and its services
        """
        xml = f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>1</minor>
  </specVersion>
  <device>
    <deviceType>{self.device_type}</deviceType>
    <friendlyName>{self.friendly_name}</friendlyName>
    <manufacturer>{self.manufacturer}</manufacturer>
    <modelName>{self.model_name}</modelName>
    <modelNumber>{self.model_version}</modelNumber>
    <UDN>{self.uuid}</UDN>
    <serviceList>
      <service>
        <serviceType>{self.service_type}</serviceType>
        <serviceId>urn:upnp-org:serviceId:PlaySEM</serviceId>
        <SCPDURL>/scpd.xml</SCPDURL>
        <controlURL>/control</controlURL>
        <eventSubURL>/event</eventSubURL>
      </service>
    </serviceList>
  </device>
</root>"""
        return xml


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

        self._server = None
        self._app = None
        self._setup_app()

        logger.info(
            f"HTTP Server initialized - {host}:{port}, "
            f"auth: {'enabled' if api_key else 'disabled'}"
        )

    def _setup_app(self):
        """Setup FastAPI application with routes and middleware."""
        try:
            from fastapi import (
                FastAPI,
                HTTPException,
                Security,
                Depends,
                status,
            )
            from fastapi.security.api_key import APIKeyHeader
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel, Field
            import uvicorn
        except ImportError:
            raise ImportError(
                "FastAPI not installed. Run: pip install fastapi uvicorn"
            )

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
        from fastapi import Body

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

                # Call callback if provided
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
