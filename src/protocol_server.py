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
import html
import struct
import paho.mqtt.client as mqtt
from typing import Optional, Callable, Dict, Any

try:
    from amqtt.broker import Broker
    from amqtt.mqtt.constants import QOS_0

    AMQTT_AVAILABLE = True
except ImportError:
    AMQTT_AVAILABLE = False
    Broker = None
    QOS_0 = None

from .effect_dispatcher import EffectDispatcher
from .effect_metadata import EffectMetadata, EffectMetadataParser


logger = logging.getLogger(__name__)


class MQTTServer:
    """
    Embedded MQTT Broker for receiving sensory effect requests.

    Runs a self-contained MQTT broker using hbmqtt and listens for effect
    metadata on the 'effects/#' topic. This removes the need for an
    external MQTT broker.
    """

    def __init__(
        self,
        dispatcher: EffectDispatcher,
        host: str = "0.0.0.0",
        port: int = 1883,
        subscribe_topic: str = "effects/#",
        on_effect_broadcast: Optional[Callable] = None,
    ):
        """
        Initialize the embedded MQTT Broker.
        """
        self.dispatcher = dispatcher
        self.host = host
        self.port = port
        self.subscribe_topic = subscribe_topic
        self.on_effect_broadcast = on_effect_broadcast
        self.broker = None
        self._is_running = False
        self._lock = threading.Lock()
        self.loop = None
        self.internal_client = None
        self._ready_event = asyncio.Event()
        self._stop_event = asyncio.Event()  # New stop event
        self._last_msg_sig = None
        self._last_msg_time = 0.0
        self._subscribed = threading.Event()

        logger.info(
            f"Embedded MQTT Broker initialized - "
            f"Host: {host}:{port}, Topic: {subscribe_topic}"
        )

    def start(self):
        """
        Start the embedded MQTT Broker in a separate thread.
        """
        with self._lock:
            if self._is_running:
                logger.warning("Embedded MQTT Broker already running")
                return

            logger.info(
                f"Starting embedded MQTT broker on {self.host}:{self.port}"
            )
            self.thread = threading.Thread(target=self._run_broker_loop)
            self.thread.daemon = True
            self.thread.start()
            self._is_running = True
            logger.info("Embedded MQTT Broker started successfully")

    def _run_broker_loop(self):
        """
        Run the asyncio event loop for the broker in a thread.
        """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_broker())
        self.loop.run_until_complete(
            self._broker_main_loop_with_shutdown()
        )  # Run main loop until stop event

        self.loop.close()  # Close the loop cleanly

    async def _start_broker(self):
        """
        Configure and start the amqtt broker.
        """
        if not AMQTT_AVAILABLE:
            logger.error(
                "amqtt library is not installed. Cannot start MQTT broker."
            )
            return

        config = {
            "listeners": {
                "default": {
                    "bind": f"{self.host}:{self.port}",
                    "type": "tcp",
                },
            }
        }
        self.broker = Broker(config)
        logger.debug("amqtt Broker instance created.")
        await self.broker.start()
        logger.info(
            f"amqtt Broker started and listening on {self.host}:{self.port}"
        )

        # Create an internal client to subscribe to topics and dispatch messages
        self.internal_client = mqtt.Client()
        self.internal_client.on_message = self._on_internal_message

        # Subscribe upon successful connection to avoid duplicate or missed subs
        def _on_connect(client, userdata, flags, rc):
            try:
                client.subscribe(self.subscribe_topic, qos=0)
                logger.debug(
                    f"Internal MQTT client subscribed to {self.subscribe_topic} (qos=0)"
                )
                # Signal readiness after successful subscribe
                if self.loop is not None:
                    try:
                        self.loop.call_soon_threadsafe(self._ready_event.set)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Internal MQTT subscribe error: {e}")

        self.internal_client.on_connect = _on_connect

        def _on_subscribe(client, userdata, mid, granted_qos):
            try:
                self._subscribed.set()
                if self.loop is not None:
                    self.loop.call_soon_threadsafe(self._ready_event.set)
            except Exception as e:
                logger.error(f"Internal MQTT on_subscribe error: {e}")

        self.internal_client.on_subscribe = _on_subscribe
        self.internal_client.connect(self.host, self.port, 60)
        self.internal_client.loop_start()

    def _on_internal_message(self, client, userdata, msg):
        """
        Callback when message is received by the internal paho-mqtt client.
        """
        topic = msg.topic
        payload = msg.payload
        try:
            payload_str = payload.decode("utf-8")
            logger.debug(
                f"Broker received message on topic '{topic}': {payload_str}"
            )

            # Deduplicate quick successive identical messages observed on some setups
            import time

            sig = (topic, payload_str)
            now = time.monotonic()
            if self._last_msg_sig == sig and (now - self._last_msg_time) < 1.0:
                logger.debug(
                    "Duplicate MQTT message ignored (within 1s window)"
                )
                return
            self._last_msg_sig = sig
            self._last_msg_time = now

            effect = self._parse_effect(payload_str)
            if effect:
                self.dispatcher.dispatch_effect_metadata(effect)
                logger.info(
                    f"Effect '{effect.effect_type}' executed successfully via MQTT"
                )
                if self.on_effect_broadcast:
                    # Run async callback in the broker's event loop
                    asyncio.run_coroutine_threadsafe(
                        self.on_effect_broadcast(effect, "mqtt_broadcast"),
                        self.loop,
                    )
            else:
                logger.warning(
                    f"Failed to parse effect from MQTT payload: {payload_str}"
                )

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    async def _broker_main_loop_with_shutdown(self):
        """
        Main loop for the broker, waits for a stop signal.
        """
        await self._stop_event.wait()  # Wait until stop event is set
        logger.info("Stop event received, initiating amqtt broker shutdown.")
        if self.broker:
            await self.broker.shutdown()  # Await the broker shutdown
        logger.info("amqtt broker shutdown complete.")

    async def wait_until_ready(self):
        """
        Wait until the embedded MQTT Broker is fully started and ready to accept connections.
        """
        await self._ready_event.wait()

    def stop(self):
        """
        Stop the embedded MQTT Broker.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("Embedded MQTT Broker not running")
                return

            logger.info("Stopping embedded MQTT Broker...")
            if self.internal_client:
                self.internal_client.loop_stop()
                self.internal_client.disconnect()

            self._stop_event.set()  # Signal the broker main loop to stop

            # Wait for the thread to finish. It should now exit cleanly after broker shutdown.
            self.thread.join(timeout=15)  # Increased timeout just in case

            self._is_running = False
            logger.info("Embedded MQTT Broker stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        with self._lock:
            return self._is_running

    def _parse_effect(self, payload: str) -> Optional[EffectMetadata]:
        """
        Parse effect metadata from payload string.
        Supports both JSON and YAML formats.
        """
        try:
            return EffectMetadataParser.parse_json(payload)
        except (json.JSONDecodeError, ValueError):
            try:
                return EffectMetadataParser.parse_yaml(payload)
            except Exception:
                return None


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
            # Small delay to ensure UDP socket readiness on Windows
            await asyncio.sleep(0.2)
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


import socket
from aiohttp import web


class UPnPServer:
    """
    UPnP server for device discovery and service advertisement using SSDP.

    Provides automatic device discovery compatible with original PlaySEM
    clients. Advertises the PlaySEM service on the local network and
    responds to M-SEARCH discovery requests. This implementation also serves
    the required device and service description XML files over HTTP.
    """

    class _SSDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, server: "UPnPServer"):
            self.server = server
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.server._transport = transport
            # Add socket to multicast group
            sock = self.transport.get_extra_info("socket")
            group = socket.inet_aton(self.server.SSDP_ADDR)
            mreq = struct.pack("4sL", group, socket.INADDR_ANY)
            try:
                sock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq
                )
            except OSError as e:
                # This can happen on some systems if the address is already in use
                logger.warning(f"Could not join multicast group: {e}")

        def datagram_received(self, data, addr):
            asyncio.create_task(self.server._handle_datagram(data, addr))

        def error_received(self, exc):
            logger.error(f"SSDP error: {exc}")

        def connection_lost(self, exc):
            logger.info("SSDP connection closed")
            if self.server:
                self.server._transport = None

    # UPnP/SSDP constants
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    UPNP_VERSION = "1.1"

    def __init__(
        self,
        friendly_name: str = "PlaySEM Server",
        dispatcher: Optional[EffectDispatcher] = None,
        uuid: Optional[str] = None,
        http_host: Optional[str] = None,
        http_port: int = 8080,
        manufacturer: str = "PlaySEM",
        model_name: str = "PlaySEM Python Server",
        model_version: str = "1.0",
    ):
        """
        Initialize UPnP server.

        Args:
            friendly_name: Human-readable device name
            dispatcher: EffectDispatcher instance for effect execution
            uuid: Device UUID (auto-generated if None)
            http_host: The host IP address to advertise for the XML server.
                       If None, it will be auto-detected.
            http_port: The port for the XML description server.
            manufacturer: Device manufacturer name
            model_name: Device model name
            model_version: Device model version
        """
        import uuid as uuid_module

        self.friendly_name = friendly_name
        self.dispatcher = dispatcher
        self.uuid = uuid or f"uuid:{uuid_module.uuid4()}"
        self.http_port = http_port

        if http_host:
            self.http_host = http_host
        else:
            self.http_host = self._get_local_ip()

        self.location_url = (
            f"http://{self.http_host}:{self.http_port}/description.xml"
        )

        self.manufacturer = manufacturer
        self.model_name = model_name
        self.model_version = model_version

        self.service_type = "urn:schemas-upnp-org:service:PlaySEM:1"
        self.device_type = "urn:schemas-upnp-org:device:PlaySEM:1"

        self._is_running = False
        self._transport = None
        self._advertisement_task = None
        self._http_runner = None
        self._http_site = None
        self._lock = threading.Lock()
        self._ready_event = asyncio.Event()

        logger.info(
            f"UPnP Server initialized - "
            f"device: {friendly_name}, uuid: {self.uuid}, "
            f"location: {self.location_url}"
        )

    async def wait_until_ready(self):
        """Wait until the UPnP server's HTTP component is ready."""
        await self._ready_event.wait()

    def _get_local_ip(self):
        """Attempt to get the local IP address of the machine."""
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't have to be reachable
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            if s:
                s.close()
        return ip

    async def _handle_description(self, request):
        """HTTP handler to serve the device description XML."""
        xml = self.get_device_description_xml()
        return web.Response(text=xml, content_type="application/xml")

    async def _handle_scpd(self, request):
        """HTTP handler to serve the Service Control Protocol Description XML."""
        xml = self._get_scpd_xml()
        return web.Response(text=xml, content_type="application/xml")

    async def _handle_control(self, request):
        """HTTP handler for the SOAP control endpoint."""
        import xml.etree.ElementTree as ET

        body = await request.text()
        logger.debug(f"Received UPnP SOAP request on /control:\n{body}")

        try:
            # Parse the SOAP envelope
            root = ET.fromstring(body)
            ns = {
                "s": "http://schemas.xmlsoap.org/soap/envelope/",
                "u": self.service_type,
            }

            # Find the action node
            action_node = root.find(".//u:SendEffect", ns)
            if action_node is None:
                raise ValueError("SendEffect action not found in SOAP request")

            # Extract arguments
            effect_type = action_node.findtext("EffectType")
            duration_str = action_node.findtext("Duration")
            intensity_str = action_node.findtext("Intensity")
            location = action_node.findtext("Location", default="")
            parameters_str = action_node.findtext("Parameters", default="{}")

            if not all([effect_type, duration_str, intensity_str]):
                raise ValueError(
                    "Missing required arguments in SendEffect action"
                )

            # Create EffectMetadata
            effect = EffectMetadata(
                effect_type=effect_type,
                duration=int(duration_str),
                intensity=int(intensity_str),
                location=location,
                parameters=json.loads(parameters_str),
            )

            # Dispatch the effect
            if self.dispatcher:
                self.dispatcher.dispatch_effect_metadata(effect)
                logger.info(
                    f"Dispatched effect '{effect.effect_type}' via UPnP"
                )
            else:
                logger.warning(
                    "No dispatcher configured for UPnP server. Effect not dispatched."
                )

            # Send success response
            response_xml = f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:SendEffectResponse xmlns:u="{self.service_type}">
        </u:SendEffectResponse>
    </s:Body>
</s:Envelope>"""
            return web.Response(
                text=response_xml,
                content_type="text/xml",
                charset="utf-8",
                status=200,
            )

        except ET.ParseError as e:
            logger.error(f"Error parsing SOAP request: {e}")
            fault_xml = self._get_soap_fault("600", "Invalid XML")
            return web.Response(
                text=fault_xml,
                content_type="text/xml",
                charset="utf-8",
                status=500,
            )
        except Exception as e:
            logger.error(f"Error processing UPnP control request: {e}")
            fault_xml = self._get_soap_fault("501", str(e))
            return web.Response(
                text=fault_xml,
                content_type="text/xml",
                charset="utf-8",
                status=500,
            )

    async def start(self):
        """
        Start the UPnP server.

        This starts both the SSDP multicast listener for discovery and the
        HTTP server for serving description files.
        """
        with self._lock:
            if self._is_running:
                logger.warning("UPnP Server already running")
                return

        try:
            loop = asyncio.get_running_loop()

            # 1. Start the SSDP datagram endpoint
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("", self.SSDP_PORT))
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: self._SSDPProtocol(self), sock=sock
            )

            # 2. Start the HTTP server for XML files
            app = web.Application()
            app.router.add_get("/description.xml", self._handle_description)
            app.router.add_get("/scpd.xml", self._handle_scpd)
            app.router.add_post("/control", self._handle_control)

            self._http_runner = web.AppRunner(app)
            await self._http_runner.setup()
            self._http_site = web.TCPSite(
                self._http_runner, self.http_host, self.http_port
            )
            await self._http_site.start()
            self._advertisement_task = asyncio.create_task(
                self._advertise_periodically()
            )

            with self._lock:
                self._is_running = True

            logger.info(
                f"UPnP SSDP discovery started on {self.SSDP_ADDR}:{self.SSDP_PORT}"
            )
            await self._send_notify_alive()
            self._ready_event.set()

        except Exception as e:
            logger.error(f"Failed to start UPnP Server: {e}")
            raise

    async def stop(self):
        """
        Stop the UPnP server.

        Sends byebye notifications and closes all sockets.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("UPnP Server not running")
                return

        try:
            logger.info("Stopping UPnP Server...")

            # Stop SSDP
            if self._advertisement_task:
                self._advertisement_task.cancel()
                try:
                    await self._advertisement_task
                except asyncio.CancelledError:
                    pass

            await self._send_notify_byebye()
            if self._transport:
                self._transport.close()

            # Stop HTTP server
            if self._http_runner:
                await self._http_runner.cleanup()

            with self._lock:
                self._is_running = False
                self._transport = None
                self._http_runner = None
                self._http_site = None

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
            if message.startswith("M-SEARCH"):
                logger.debug(f"Received M-SEARCH from {addr[0]}:{addr[1]}")
                st_line = [
                    line
                    for line in message.split("\r\n")
                    if line.upper().startswith("ST:")
                ]
                if not st_line:
                    return
                search_target = st_line[0].split(":", 1)[1].strip()

                if search_target in [
                    "ssdp:all",
                    "upnp:rootdevice",
                    self.device_type,
                    self.service_type,
                    self.uuid,
                ]:
                    await self._send_msearch_response(addr, search_target)
        except Exception as e:
            logger.error(f"Error handling SSDP datagram: {e}")

    async def _send_msearch_response(self, addr: tuple, search_target: str):
        """Send M-SEARCH response to a discovery request."""
        usn = (
            self.uuid
            if search_target == "upnp:rootdevice"
            else f"{self.uuid}::{search_target}"
        )
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"CACHE-CONTROL: max-age=1800\r\n"
            f"EXT:\r\n"
            f"LOCATION: {self.location_url}\r\n"
            f"SERVER: Python/{self.model_version} UPnP/{self.UPNP_VERSION} PlaySEM/{self.model_version}\r\n"
            f"ST: {search_target}\r\n"
            f"USN: {usn}\r\n"
            f"\r\n"
        )
        if self._transport:
            self._transport.sendto(response.encode("utf-8"), addr)
            logger.debug(
                f"Sent M-SEARCH response to {addr[0]}:{addr[1]} for {search_target}"
            )

    async def _send_notify_alive(self):
        """Send NOTIFY alive announcements."""
        targets = {
            "upnp:rootdevice": self.uuid,
            self.uuid: self.uuid,
            self.device_type: f"{self.uuid}::{self.device_type}",
            self.service_type: f"{self.uuid}::{self.service_type}",
        }
        for nt, usn in targets.items():
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"CACHE-CONTROL: max-age=1800\r\n"
                f"LOCATION: {self.location_url}\r\n"
                f"NT: {nt}\r\n"
                f"NTS: ssdp:alive\r\n"
                f"SERVER: Python/{self.model_version} UPnP/{self.UPNP_VERSION} PlaySEM/{self.model_version}\r\n"
                f"USN: {usn}\r\n"
                f"\r\n"
            )
            if self._transport:
                self._transport.sendto(
                    notify.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )
        logger.info("Sent NOTIFY alive announcements")

    async def _send_notify_byebye(self):
        """Send NOTIFY byebye announcements."""
        targets = {
            "upnp:rootdevice": self.uuid,
            self.uuid: self.uuid,
            self.device_type: f"{self.uuid}::{self.device_type}",
            self.service_type: f"{self.uuid}::{self.service_type}",
        }
        for nt, usn in targets.items():
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"NT: {nt}\r\n"
                f"NTS: ssdp:byebye\r\n"
                f"USN: {usn}\r\n"
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
                await asyncio.sleep(900)
                if self._is_running:
                    await self._send_notify_alive()
        except asyncio.CancelledError:
            pass

    def get_device_description_xml(self) -> str:
        """Generate UPnP device description XML."""
        # Using f-string for multiline string for clarity
        return f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>{self.device_type}</deviceType>
        <friendlyName>{html.escape(self.friendly_name)}</friendlyName>
        <manufacturer>{html.escape(self.manufacturer)}</manufacturer>
        <modelName>{html.escape(self.model_name)}</modelName>
        <UDN>{self.uuid}</UDN>
        <serviceList>
            <service>
                <serviceType>{self.service_type}</serviceType>
                <serviceId>urn:upnp-org:serviceId:PlaySEM1</serviceId>
                <SCPDURL>/scpd.xml</SCPDURL>
                <controlURL>/control</controlURL>
                <eventSubURL>/event</eventSubURL>
            </service>
        </serviceList>
    </device>
</root>"""

    def _get_scpd_xml(self) -> str:
        """Generates the Service Control Protocol Description (SCPD) XML."""
        return """<scpd xmlns="urn:schemas-upnp-org:service-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <actionList>
        <action>
            <name>SendEffect</name>
            <argumentList>
                <argument>
                    <name>EffectType</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_EffectType</relatedStateVariable>
                </argument>
                <argument>
                    <name>Duration</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Duration</relatedStateVariable>
                </argument>
                <argument>
                    <name>Intensity</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Intensity</relatedStateVariable>
                </argument>
                <argument>
                    <name>Location</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Location</relatedStateVariable>
                </argument>
                <argument>
                    <name>Parameters</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Parameters</relatedStateVariable>
                </argument>
            </argumentList>
        </action>
    </actionList>
    <serviceStateTable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_EffectType</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Duration</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Intensity</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Location</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Parameters</name>
            <dataType>string</dataType>
        </stateVariable>
    </serviceStateTable>
</scpd>"""

    def _get_soap_fault(self, fault_code: str, fault_string: str) -> str:
        """Generates a UPnP SOAP Fault message."""
        return f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <s:Fault>
            <faultcode>s:Client</faultcode>
            <faultstring>UPnPError</faultstring>
            <detail>
                <UPnPError xmlns="urn:schemas-upnp-org:control-1-0">
                    <errorCode>{fault_code}</errorCode>
                    <errorDescription>{fault_string}</errorDescription>
                </UPnPError>
            </detail>
        </s:Fault>
    </s:Body>
</s:Envelope>"""


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
        from fastapi.responses import HTMLResponse

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
                "async function loadDevices(){"
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
                "    const res=await fetch('/api/capabilities/' +"
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
