"""
WebSocket Handler - Client connection and message routing.

Handles:
- WebSocket client connections
- Message routing to appropriate handlers
- Device registration via WebSocket
- Broadcasting device lists and effects
"""

import json
import time
from typing import Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from ..models import ConnectedDevice
from playsem.effect_metadata import create_effect


class WebSocketHandler:
    """Handler for WebSocket connections and message routing."""

    def __init__(self):
        """Initialize WebSocket handler."""
        self.clients: Set[WebSocket] = set()
        self.web_clients: Dict[str, WebSocket] = {}  # device_id -> WebSocket
        self.stats = {
            "connections": 0,
            "disconnections": 0,
            "messages_received": 0,
            "messages_sent": 0,
        }

    async def handle_client(
        self,
        websocket: WebSocket,
        devices: Dict,
        message_handler,
    ):
        """Handle WebSocket client connection.

        Args:
            websocket: WebSocket connection
            devices: Dictionary of connected devices
            message_handler: Callback for handling messages
        """
        await websocket.accept()
        self.clients.add(websocket)
        self.stats["connections"] += 1
        registered_device_id = None

        print(f"[OK] Client connected. Total clients: {len(self.clients)}")

        try:
            # Handle incoming messages
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    self.stats["messages_received"] += 1

                    if "protocol" in message and "effect" in message:
                        # Super controller message
                        await self._handle_super_controller_message(
                            websocket, message, message_handler
                        )
                    elif message.get("type") == "register_device":
                        # Device registration
                        registered_device_id = await self.register_web_device(
                            websocket, message, devices
                        )
                    else:
                        # Normal message routing
                        await self._route_message(
                            websocket, message, devices, message_handler
                        )

                except json.JSONDecodeError:
                    await self._route_message(
                        websocket, {"type": data}, devices, message_handler
                    )
                except Exception as e:
                    print(f"[ERROR] Message processing: {e}")
                    await self._route_message(
                        websocket, {"type": "error"}, devices, message_handler
                    )

        except WebSocketDisconnect:
            self.stats["disconnections"] += 1
            print(
                f"[x] Client disconnected. "
                f"Remaining clients: {len(self.clients) - 1}"
            )
        except Exception as e:
            print(f"[x] WebSocket error: {e}")
        finally:
            self.clients.discard(websocket)
            if registered_device_id:
                await self.unregister_web_device(registered_device_id, devices)

    async def _handle_super_controller_message(
        self,
        websocket: WebSocket,
        message: dict,
        message_handler,
    ) -> None:
        """Handle super controller message with protocol specification.

        Args:
            websocket: WebSocket connection
            message: Message with protocol and effect
            message_handler: Handler callback
        """
        protocol = message.get("protocol")
        effect_data = message.get("effect", {})

        # Ensure effect_type is present
        if not effect_data.get("effect_type"):
            effect_data["effect_type"] = "vibration"

        print(
            f"[RECV] Super controller message for protocol {protocol} "
            f"with effect: {effect_data.get('effect_type')}"
        )

        if message_handler:
            await message_handler(
                websocket=websocket,
                protocol=protocol,
                effect_data=effect_data,
                message_type="send_effect_protocol",
            )

    async def register_web_device(
        self,
        websocket: WebSocket,
        message: dict,
        devices: Dict,
    ) -> str:
        """Register a web client as a device.

        Args:
            websocket: WebSocket connection
            message: Registration message
            devices: Devices dictionary

        Returns:
            Device ID of registered web device
        """
        device_id = message.get("device_id")
        device_name = message.get("device_name", "Web Device")
        device_type = message.get("device_type", "web_client")
        capabilities = message.get("capabilities", [])
        protocols = message.get("protocols", ["websocket"])
        connection_mode = message.get("connection_mode", "direct")

        print(
            f"[REGISTER] Web device: {device_id} ({device_name}) "
            f"capabilities: {capabilities} "
            f"protocols: {protocols} [{connection_mode.upper()} MODE]"
        )

        # Store WebSocket connection
        self.web_clients[device_id] = websocket

        # Create device entry
        device = ConnectedDevice(
            id=device_id,
            name=device_name,
            type=device_type,
            address=f"multi-protocol:{','.join(protocols)}",
            driver=None,
            manager=None,
            dispatcher=None,
            connected_at=time.time(),
        )

        # Add metadata
        device.capabilities = capabilities
        device.protocols = protocols
        device.connection_mode = connection_mode
        devices[device_id] = device

        # Send confirmation
        await websocket.send_json(
            {
                "type": "device_registered",
                "device_id": device_id,
                "message": f"Registered as {device_name}",
            }
        )
        self.stats["messages_sent"] += 1

        # Broadcast device list update
        await self.broadcast_device_list(devices)

        # Announce on protocols
        await self.announce_device_discovery(device_id, devices)

        return device_id

    async def unregister_web_device(
        self,
        device_id: str,
        devices: Dict,
    ) -> None:
        """Unregister a web device.

        Args:
            device_id: Device ID to unregister
            devices: Devices dictionary
        """
        if device_id in self.web_clients:
            del self.web_clients[device_id]
        if device_id in devices:
            del devices[device_id]
            print(f"[UNREGISTER] Web device: {device_id}")
            await self.broadcast_device_list(devices)

    async def broadcast_device_list(self, devices: Dict) -> None:
        """Broadcast updated device list to all clients.

        Args:
            devices: Dictionary of devices
        """
        device_list = [
            {
                "id": dev.id,
                "name": dev.name,
                "type": dev.type,
                "address": dev.address,
                "protocols": getattr(dev, "protocols", []),
                "capabilities": getattr(dev, "capabilities", []),
                "connection_mode": getattr(dev, "connection_mode", "direct"),
            }
            for dev in devices.values()
        ]

        message = {"type": "device_list", "devices": device_list}

        disconnected = set()
        for client in self.clients:
            try:
                await client.send_json(message)
                self.stats["messages_sent"] += 1
            except Exception:
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def announce_device_discovery(
        self,
        device_id: str,
        devices: Dict,
    ) -> None:
        """Announce device discovery on registered protocols.

        Args:
            device_id: Device ID
            devices: Devices dictionary
        """
        device = devices.get(device_id)
        if not device:
            return

        protocols = getattr(device, "protocols", [])
        device_info = {
            "device_id": device.id,
            "device_name": device.name,
            "device_type": device.type,
            "capabilities": getattr(device, "capabilities", []),
            "protocols": protocols,
        }

        # MQTT announcement
        if "mqtt" in protocols:
            print(
                f"[MQTT-ANNOUNCE] Device {device_id} - "
                f"{json.dumps(device_info)}"
            )

        # CoAP announcement
        if "coap" in protocols:
            print(f"[COAP-ANNOUNCE] Device {device_id} registered")

        # UPnP announcement
        if "upnp" in protocols:
            print(f"[UPNP-ANNOUNCE] Device {device_id} via SSDP")

    async def _route_message(
        self,
        websocket: WebSocket,
        message: dict,
        devices: Dict,
        message_handler,
    ) -> None:
        """Route message to appropriate handler.

        Args:
            websocket: WebSocket connection
            message: Message to route
            devices: Devices dictionary
            message_handler: Handler callback
        """
        msg_type = message.get("type")

        # Silently handle acknowledgments and pings
        if msg_type in ["effect_ack", "ping", "pong"]:
            return

        print(f"[RECV] Message type: {msg_type}")

        if msg_type == "get_devices":
            await websocket.send_json(
                {
                    "type": "device_list",
                    "devices": [
                        {
                            "id": dev.id,
                            "name": dev.name,
                            "type": dev.type,
                            "address": dev.address,
                        }
                        for dev in devices.values()
                    ],
                }
            )
            self.stats["messages_sent"] += 1

        elif msg_type == "scan_devices":
            driver_type = message.get("driver_type")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    driver_type=driver_type,
                    message_type="scan_devices",
                )

        elif msg_type == "connect_device":
            address = message.get("address")
            driver_type = message.get("driver_type")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    address=address,
                    driver_type=driver_type,
                    message_type="connect_device",
                )

        elif msg_type == "disconnect_device":
            device_id = message.get("device_id")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    device_id=device_id,
                    message_type="disconnect_device",
                )

        elif msg_type == "send_effect":
            device_id = message.get("device_id")
            effect_data = message.get("effect")
            protocol = message.get("protocol")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    device_id=device_id,
                    effect_data=effect_data,
                    protocol=protocol,
                    message_type="send_effect",
                )

        elif msg_type == "send_effect_protocol":
            protocol = message.get("protocol")
            effect_data = message.get("effect")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    protocol=protocol,
                    effect_data=effect_data,
                    message_type="send_effect_protocol",
                )

        elif msg_type == "effect":
            # Broadcast-only effect
            effect = create_effect(
                effect_type=message.get("effect_type", "vibration"),
                intensity=message.get("intensity", 50),
                duration=message.get("duration", 1000),
            )
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    effect=effect,
                    message_type="broadcast_effect",
                )

        elif msg_type == "start_protocol_server":
            protocol = message.get("protocol")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    protocol=protocol,
                    message_type="start_protocol_server",
                )

        elif msg_type == "stop_protocol_server":
            protocol = message.get("protocol")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    protocol=protocol,
                    message_type="stop_protocol_server",
                )

        elif msg_type == "upload_timeline":
            file_content = message.get("file_content")
            file_type = message.get("file_type")
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    file_content=file_content,
                    file_type=file_type,
                    message_type="upload_timeline",
                )

        elif msg_type in [
            "play_timeline",
            "pause_timeline",
            "resume_timeline",
            "stop_timeline",
            "get_timeline_status",
        ]:
            if message_handler:
                await message_handler(
                    websocket=websocket,
                    message_type=msg_type,
                )

        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }
            )
            self.stats["messages_sent"] += 1

    async def broadcast_effect(
        self,
        effect,
        device_id: str,
        protocol: str = "websocket",
    ) -> None:
        """Broadcast effect to all connected clients.

        Args:
            effect: Effect object
            device_id: Originating device ID
            protocol: Protocol used
        """
        message = {
            "type": "effect_broadcast",
            "effect_type": effect.effect_type,
            "duration": effect.duration,
            "intensity": effect.intensity,
            "device_id": device_id,
            "protocol": protocol,
        }

        disconnected = set()
        for client in self.clients:
            try:
                await client.send_json(message)
                self.stats["messages_sent"] += 1
            except Exception:
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    def get_web_client(self, device_id: str) -> Optional[WebSocket]:
        """Get WebSocket for web device.

        Args:
            device_id: Device ID

        Returns:
            WebSocket connection or None
        """
        return self.web_clients.get(device_id)

    def is_web_device(self, device_id: str) -> bool:
        """Check if device is web client.

        Args:
            device_id: Device ID

        Returns:
            True if web device
        """
        return device_id in self.web_clients

    def get_stats(self) -> dict:
        """Get WebSocket statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
