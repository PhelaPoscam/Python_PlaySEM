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
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
    ):
        """
        Initialize MQTT server.
        
        Args:
            broker_address: MQTT broker hostname/IP
            dispatcher: EffectDispatcher instance for effect execution
            subscribe_topic: MQTT topic pattern to subscribe to (supports wildcards)
            status_topic: Topic for publishing server status messages
            port: MQTT broker port (default: 1883)
            client_id: Optional MQTT client ID (auto-generated if None)
            on_effect_received: Optional callback when effect is received
        """
        self.broker_address = broker_address
        self.port = port
        self.dispatcher = dispatcher
        self.subscribe_topic = subscribe_topic
        self.status_topic = status_topic
        self.on_effect_received = on_effect_received
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=client_id or "playsem_server")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self._is_running = False
        self._lock = threading.Lock()
        
        logger.info(f"MQTT Server initialized - broker: {broker_address}:{port}, "
                   f"topic: {subscribe_topic}")
    
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
                logger.info(f"Connecting to MQTT broker at {self.broker_address}:{self.port}")
                self.client.connect(self.broker_address, self.port, keepalive=60)
                
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
                    retain=True
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
            logger.info(f"Connected to MQTT broker, subscribing to {self.subscribe_topic}")
            
            # Subscribe to effect topics
            client.subscribe(self.subscribe_topic)
            
            # Publish online status
            client.publish(
                self.status_topic,
                json.dumps({"status": "online", "version": "0.1.0"}),
                retain=True
            )
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Callback when disconnected from MQTT broker.
        
        Args:
            rc: Disconnect reason code
        """
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker (code: {rc})")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """
        Callback when message is received.
        
        Parses effect metadata and dispatches to devices.
        
        Args:
            msg: MQTT message object
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
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
                
                logger.info(f"Effect '{effect.effect_type}' executed successfully")
            else:
                logger.warning(f"Failed to parse effect from payload: {payload}")
                self._publish_response(topic, None, success=False, 
                                     error="Invalid effect format")
                
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
        error: Optional[str] = None
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
            # Create response topic (e.g., "effects/light" -> "effects/light/response")
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
        on_effect_received: Optional[Callable[[EffectMetadata], None]] = None,
        on_client_connected: Optional[Callable[[str], None]] = None,
        on_client_disconnected: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize WebSocket server.
        
        Args:
            host: Host address to bind to (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default: 8080)
            dispatcher: EffectDispatcher for executing effects
            on_effect_received: Optional callback when effect is received
            on_client_connected: Optional callback when client connects
            on_client_disconnected: Optional callback when client disconnects
        """
        self.host = host
        self.port = port
        self.dispatcher = dispatcher
        self.on_effect_received = on_effect_received
        self.on_client_connected = on_client_connected
        self.on_client_disconnected = on_client_disconnected
        
        self.clients = set()  # Connected WebSocket clients
        self._server = None
        self._is_running = False
        self._lock = threading.Lock()
        
        logger.info(f"WebSocket Server initialized - {host}:{port}")
    
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
            
            # Start WebSocket server
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            
            with self._lock:
                self._is_running = True
            
            logger.info(f"WebSocket Server started on ws://{self.host}:{self.port}")
            
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
                    return_exceptions=True
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
        
        try:
            # Register client
            self.clients.add(websocket)
            logger.info(f"Client connected: {client_id}")
            
            if self.on_client_connected:
                self.on_client_connected(client_id)
            
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to PythonPlaySEM WebSocket Server",
                "version": "0.1.0"
            }))
            
            # Handle messages from client
            async for message in websocket:
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
                    await websocket.send(json.dumps({
                        "type": "response",
                        "success": True,
                        "effect_type": effect.effect_type,
                        "timestamp": effect.timestamp
                    }))
                    
                    # Broadcast effect to all clients
                    await self._broadcast({
                        "type": "effect_executed",
                        "effect_type": effect.effect_type,
                        "intensity": effect.intensity,
                        "duration": effect.duration
                    }, exclude=websocket)
                    
                    log_msg = f"Effect '{effect.effect_type}' from {client_id}"
                    logger.info(log_msg)
                    
                else:
                    # Send error response
                    await websocket.send(json.dumps({
                        "type": "response",
                        "success": False,
                        "error": "Invalid effect format"
                    }))
                    
            elif msg_type == "ping":
                # Respond to ping
                await websocket.send(json.dumps({"type": "pong"}))
                
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {client_id}: {message}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))
            
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
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
                location=data.get("location"),
                parameters=data.get("parameters", {})
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
        await self._broadcast({
            "type": "effect_triggered",
            "effect_type": effect.effect_type,
            "timestamp": effect.timestamp,
            "duration": effect.duration,
            "intensity": effect.intensity,
            "location": effect.location,
            "parameters": effect.parameters
        })


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
            host: Host address to bind to (e.g., "0.0.0.0" or "localhost")
            port: Port to listen on (default CoAP port: 5683)
            dispatcher: EffectDispatcher for executing effects
            on_effect_received: Optional callback when effect is received
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
                                "error": "Invalid effect format"
                            }
                            return self._outer._json_response(
                                response,
                                code="BAD_REQUEST"
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
                            code="INTERNAL_SERVER_ERROR"
                        )
            
            # Build resource site
            site = resource.Site()
            site.add_resource(["effects"], EffectsResource(self))
            
            # Create server context bound to host/port
            bind = (self.host, self.port)
            self._context = await Context.create_server_context(
                site,
                bind=bind
            )
            self._site = site
            with self._lock:
                self._is_running = True
            logger.info(
                f"CoAP Server started on coap://{self.host}:{self.port}"
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
    UPnP server for device discovery and service advertisement.
    
    Provides automatic device discovery compatible with original
    PlaySEM clients.
    
    TODO: Implement UPnP SSDP discovery and service description
    """
    
    def __init__(self):
        """Initialize UPnP server."""
        raise NotImplementedError("UPnP server not yet implemented")
