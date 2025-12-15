"""
Effect Service - Effect dispatch and broadcasting.

Handles effect routing to devices and protocols including:
- Effect dispatch to connected devices
- Protocol-specific effect sending (MQTT, CoAP, HTTP, UPnP)
- Effect broadcasting to all connected clients
"""

import asyncio
import json
import time
from typing import Dict, Optional

from fastapi import WebSocket

from playsem import EffectDispatcher
from playsem.effect_metadata import create_effect


class EffectService:
    """Service for managing effect dispatch and broadcasting."""

    def __init__(self):
        """Initialize effect service."""
        self.stats = {
            "effects_sent": 0,
            "errors": 0,
        }

    async def send_effect(
        self,
        websocket: WebSocket,
        device_id: str,
        effect_data: dict,
        devices: Dict,
        web_clients: Dict,
    ) -> None:
        """Send effect to a device.

        Args:
            websocket: WebSocket connection for status updates
            device_id: ID of target device
            effect_data: Effect parameters
            devices: Dictionary of connected devices
            web_clients: Dictionary of web clients
        """
        if device_id not in devices:
            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": False,
                    "error": "Device not found",
                    "device_id": device_id,
                }
            )
            return

        try:
            device = devices[device_id]
            start_time = time.time()

            print(
                f"[ROUTE] send_effect => device='{device.name}' id={device_id}"
            )

            # Create effect object
            effect = create_effect(
                effect_type=effect_data.get("effect_type", "vibration"),
                intensity=effect_data.get("intensity", 50),
                duration=effect_data.get("duration", 1000),
                timestamp=0,
                parameters=effect_data.get("parameters", {}),
            )

            # Route based on device type
            if device.type == "mock":
                await self._send_to_mock_device(device, effect)
            elif device_id in web_clients:
                await self._send_to_web_client(web_clients[device_id], effect)
            elif device.dispatcher:
                device.dispatcher.dispatch_effect_metadata(effect)
            else:
                raise Exception(
                    f"Device {device.name} has no dispatcher or "
                    "WebSocket connection"
                )

            latency = int((time.time() - start_time) * 1000)
            self.stats["effects_sent"] += 1

            print(f"[OK] Effect sent to {device.name} (latency: {latency}ms)")

            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": True,
                    "latency": latency,
                    "device_id": device_id,
                    "effect_type": effect.effect_type,
                }
            )

        except Exception as e:
            print(f"[x] Effect send error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "effect_result",
                    "success": False,
                    "error": str(e),
                    "device_id": device_id,
                }
            )

    async def _send_to_mock_device(self, device, effect) -> None:
        """Send effect to mock device.

        Args:
            device: ConnectedDevice instance
            effect: EffectMetadata object
        """
        mock_device = device.driver
        if effect.effect_type == "light":
            brightness = int(effect.intensity * 2.55)
            mock_device.send_command(
                "set_brightness", {"brightness": brightness}
            )
        elif effect.effect_type == "wind":
            mock_device.send_command("set_speed", {"speed": effect.intensity})
        elif effect.effect_type == "vibration":
            mock_device.send_command(
                "set_intensity",
                {
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                },
            )
        else:
            mock_device.send_command(
                effect.effect_type,
                {
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                },
            )

        print(
            f"[OK] Mock device '{mock_device.device_id}' received "
            f"{effect.effect_type.upper()} command: "
            f"intensity={effect.intensity}, duration={effect.duration}"
        )

    async def _send_to_web_client(self, web_client: WebSocket, effect) -> None:
        """Send effect to web client via WebSocket.

        Args:
            web_client: WebSocket connection
            effect: EffectMetadata object
        """
        try:
            await web_client.send_json(
                {
                    "type": "effect",
                    "effect_type": effect.effect_type,
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                    "timestamp": effect.timestamp,
                    "parameters": effect.parameters,
                }
            )
        except Exception as e:
            print(f"[ERROR] WebSocket send failure: {e}")
            raise

    async def send_effect_protocol(
        self,
        websocket: WebSocket,
        protocol: str,
        effect_data: dict,
        mqtt_server=None,
        http_api_server=None,
        coap_server=None,
        upnp_server=None,
        web_clients: Dict = None,
    ) -> None:
        """Send effect over specific protocol.

        Args:
            websocket: WebSocket connection for status
            protocol: Protocol name ('mqtt', 'http', 'coap', 'upnp', 'websocket')
            effect_data: Effect parameters
            mqtt_server: MQTT server instance
            http_api_server: HTTP API server instance
            coap_server: CoAP server instance
            upnp_server: UPnP server instance
            web_clients: Dictionary of web clients
        """
        web_clients = web_clients or {}

        try:
            effect = create_effect(
                effect_type=effect_data.get("effect_type", "vibration"),
                intensity=effect_data.get("intensity", 50),
                duration=effect_data.get("duration", 1000),
                timestamp=0,
            )

            if protocol == "websocket":
                await self._send_via_websocket(effect, web_clients)

            elif protocol == "mqtt":
                await self._send_via_mqtt(effect, websocket, mqtt_server)

            elif protocol == "http":
                await self._send_via_http(effect, websocket, http_api_server)

            elif protocol == "coap":
                await self._send_via_coap(effect, websocket, coap_server)

            elif protocol == "upnp":
                await self._send_via_upnp(effect, websocket, upnp_server)

            else:
                raise ValueError(f"Unsupported protocol: {protocol}")

            await websocket.send_json(
                {
                    "type": "effect_protocol_result",
                    "success": True,
                    "protocol": protocol,
                    "effect_type": effect.effect_type,
                }
            )

        except Exception as e:
            print(f"[x] Effect protocol send error: {e}")
            await websocket.send_json(
                {
                    "type": "effect_protocol_result",
                    "success": False,
                    "error": str(e),
                    "protocol": protocol,
                }
            )

    async def _send_via_websocket(self, effect, web_clients: Dict) -> None:
        """Send via WebSocket protocol."""
        ws_devices = [dev_id for dev_id in web_clients.keys()]

        for dev_id in ws_devices:
            web_client = web_clients[dev_id]
            await web_client.send_json(
                {
                    "type": "effect",
                    "effect_type": effect.effect_type,
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                    "timestamp": effect.timestamp,
                    "parameters": {},
                }
            )

        print(f"[OK] Effect sent to {len(ws_devices)} WebSocket device(s)")

    async def _send_via_mqtt(
        self,
        effect,
        websocket: WebSocket,
        mqtt_server,
    ) -> None:
        """Send via MQTT protocol."""
        if not mqtt_server or not mqtt_server.is_running():
            raise Exception("MQTT server not running")

        ready = False
        if mqtt_server:
            # Increase retries for MQTT readiness
            for attempt in range(5):
                try:
                    await asyncio.wait_for(
                        mqtt_server.wait_until_ready(), timeout=2.0
                    )
                    ready = bool(mqtt_server.internal_client)
                    if ready:
                        break
                except asyncio.TimeoutError:
                    print(f"[WARN] MQTT readiness timeout (attempt {attempt + 1}/5)")
                    await asyncio.sleep(0.5)

        if not ready:
            raise Exception("MQTT server not ready")

        payload = json.dumps(
            {
                "effect_type": effect.effect_type,
                "intensity": effect.intensity,
                "duration": effect.duration,
            }
        )

        mqtt_server.internal_client.publish("effects/sem", payload)
        print(f"[OK] Effect sent via MQTT")

    async def _send_via_http(
        self,
        effect,
        websocket: WebSocket,
        http_api_server,
    ) -> None:
        """Send via HTTP protocol."""
        if not http_api_server:
            raise Exception("HTTP server not running")

        import httpx

        client = httpx.AsyncClient()
        try:
            target_host = getattr(http_api_server, "host", "127.0.0.1")
            target_port = getattr(http_api_server, "port", 8081)
            url = f"http://{target_host}:{target_port}/api/effects"

            response = await client.post(
                url,
                json={
                    "effect_type": effect.effect_type,
                    "timestamp": effect.timestamp,
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                },
            )
            response.raise_for_status()
            print(f"[OK] Effect sent via HTTP to {url}")
        finally:
            await client.aclose()

    async def _send_via_coap(
        self,
        effect,
        websocket: WebSocket,
        coap_server,
    ) -> None:
        """Send via CoAP protocol."""
        if not coap_server:
            raise Exception("CoAP server not running")

        try:
            from aiocoap import Context, Message, POST

            context = await Context.create_client_context()

            payload = json.dumps(
                {
                    "effect_type": effect.effect_type,
                    "timestamp": effect.timestamp,
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                }
            ).encode("utf-8")

            request = Message(
                code=POST,
                uri="coap://127.0.0.1:5683/effects",
                payload=payload,
            )

            response = await context.request(request).response
            print(f"[OK] Effect sent via CoAP - Response: {response.code}")

        except ImportError as e:
            raise Exception("aiocoap not installed")

    async def _send_via_upnp(
        self,
        effect,
        websocket: WebSocket,
        upnp_server,
    ) -> None:
        """Send via UPnP protocol."""
        if not upnp_server or not upnp_server.is_running():
            raise Exception("UPnP server not running")

        try:
            import aiohttp

            soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
    <u:SendEffect xmlns:u="urn:schemas-upnp-org:service:PlaySEM:1">
        <EffectType>{effect.effect_type}</EffectType>
        <Intensity>{effect.intensity}</Intensity>
        <Duration>{effect.duration}</Duration>
    </u:SendEffect>
</s:Body>
</s:Envelope>"""

            async with aiohttp.ClientSession() as session:
                soap_action = '"urn:schemas-upnp-org:service:SEM:1#SendEffect"'
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": soap_action,
                }
                async with session.post(
                    f"http://{upnp_server.http_host}:{upnp_server.http_port}/control",
                    headers=headers,
                    data=soap_body,
                    timeout=5.0,
                ) as response:
                    response.raise_for_status()
                    print(
                        f"[OK] Effect sent via UPnP - Status: {response.status}"
                    )

        except ImportError:
            raise Exception("aiohttp not installed")

    async def broadcast_effect(
        self,
        effect,
        device_id: str,
        protocol: str = "websocket",
        clients: set = None,
    ) -> None:
        """Broadcast effect to all connected clients.

        Args:
            effect: Effect object
            device_id: ID of originating device
            protocol: Protocol used
            clients: Set of WebSocket clients
        """
        clients = clients or set()

        print(
            f"[DEBUG] Broadcasting effect '{effect.effect_type}' to {len(clients)} clients"
        )

        message = {
            "type": "effect_broadcast",
            "effect_type": effect.effect_type,
            "duration": effect.duration,
            "intensity": effect.intensity,
            "device_id": device_id,
            "protocol": protocol,
        }

        disconnected = set()
        for client in clients:
            try:
                await client.send_json(message)
            except Exception as e:
                print(f"[DEBUG] Failed to broadcast to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        for client in disconnected:
            clients.discard(client)
