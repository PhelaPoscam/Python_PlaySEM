import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from playsem.effect_dispatcher import EffectDispatcher
from playsem.protocol_servers import CoAPServer, MQTTServer, UPnPServer
from playsem.effect_metadata import EffectMetadata

logger = logging.getLogger(__name__)


class _BridgeDispatcher(EffectDispatcher):
    """Dispatcher that forwards metadata to a bridge callback."""

    def __init__(self, bridge_cb: Callable[[Any, str], Any], source: str):
        self._bridge_cb = bridge_cb
        self._source = source

    def dispatch_effect_metadata(self, effect: Any):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        loop.create_task(self._bridge_cb(effect, self._source))


class ProtocolService:
    """Provides protocol bootstrap helpers for device registration."""

    def __init__(
        self,
        *,
        server_port: int,
        mqtt_port: int,
        coap_port: int,
        upnp_http_port: int,
    ) -> None:
        self.server_port = server_port
        self.mqtt_port = mqtt_port
        self.coap_port = coap_port
        self.upnp_http_port = upnp_http_port

        self._mqtt_server: Optional[MQTTServer] = None
        self._coap_server: Optional[CoAPServer] = None
        self._upnp_server: Optional[UPnPServer] = None

        self._on_protocol_effect: Optional[Callable] = None
        self._custom_handlers: Dict[str, Any] = {}

    def register_handler(self, protocol_name: str, handler: Any) -> None:
        """Register a custom protocol handler used by publish_effect."""
        key = (protocol_name or "").strip().lower()
        if not key:
            raise ValueError("protocol_name must be a non-empty string")
        self._custom_handlers[key] = handler

    def set_effect_callback(self, callback: Callable):
        """Set callback for effects received from embedded servers."""
        self._on_protocol_effect = callback

    async def _dispatch_bridge(self, effect_metadata: Any, source: str):
        """Bridge incoming protocol effects to the main application."""
        if self._on_protocol_effect:
            effect_dict = {
                "type": "effect",
                "device_id": "broadcast",
                "broadcast": True,
                "effect_type": getattr(
                    effect_metadata, "effect_type", "unknown"
                ),
                "modality": getattr(effect_metadata, "modality", "unknown"),
                "intensity": getattr(effect_metadata, "intensity", 50),
                "duration": getattr(effect_metadata, "duration", 1000),
                "parameters": getattr(effect_metadata, "parameters", {}),
                "source": source,
            }
            await self._on_protocol_effect(effect_dict)

    async def ensure_protocol_servers(self, protocols: List[str]) -> None:
        """Start embedded servers needed for requested protocols."""

        if "mqtt" in protocols and (
            not self._mqtt_server or not self._mqtt_server.is_running()
        ):
            try:
                self._mqtt_server = MQTTServer(
                    dispatcher=_BridgeDispatcher(
                        self._dispatch_bridge,
                        "mqtt",
                    ),
                    host="0.0.0.0",
                    port=self.mqtt_port,
                    on_effect_broadcast=lambda e, s: self._dispatch_bridge(
                        e,
                        s,
                    ),
                )
                await asyncio.to_thread(self._mqtt_server.start)
                logger.info(
                    f"[BOOT] Embedded MQTT broker started on :{self.mqtt_port}"
                )
            except Exception as e:
                logger.error(f"[BOOT] Failed to start MQTT broker: {e}")

        if "coap" in protocols and (
            not self._coap_server or not self._coap_server.is_running()
        ):
            try:
                self._coap_server = CoAPServer(
                    host="0.0.0.0",
                    port=self.coap_port,
                    dispatcher=_BridgeDispatcher(
                        self._dispatch_bridge,
                        "coap",
                    ),
                )
                await self._coap_server.start()
                logger.info(
                    f"[BOOT] Embedded CoAP server started on :{self.coap_port}"
                )
            except Exception as e:
                logger.error(f"[BOOT] Failed to start CoAP server: {e}")

        if "upnp" in protocols and (
            not self._upnp_server or not self._upnp_server.is_running()
        ):
            try:
                self._upnp_server = UPnPServer(
                    friendly_name="PlaySEM Modular Server",
                    http_port=self.upnp_http_port,
                )
                await self._upnp_server.start()
                logger.info(
                    f"[BOOT] UPnP server started on :{self.upnp_http_port}"
                )
            except Exception as e:
                logger.error(f"[BOOT] Failed to start UPnP server: {e}")

    async def stop_servers(self):
        """Shutdown all embedded servers."""
        if self._mqtt_server:
            await asyncio.to_thread(self._mqtt_server.stop)
        if self._coap_server:
            await self._coap_server.stop()
        if self._upnp_server:
            await self._upnp_server.stop()

    async def publish_effect(
        self,
        device_id: str,
        effect: Dict[str, Any],
        protocol: Optional[str] = None,
    ) -> bool:
        """Publish an effect through the embedded protocol servers."""
        effect_type = effect.get("effect_type", "unknown")
        intensity = effect.get("intensity", 50)
        duration = effect.get("duration", 1000)
        modality = effect.get("modality", "vibration")
        parameters = effect.get("parameters", {})

        protocol = (protocol or "mqtt").lower()

        try:
            if protocol == "mqtt" and self._mqtt_server:
                # Wait for the broker to be ready before publishing
                if self._mqtt_server.is_running():
                    await self._mqtt_server.wait_until_ready()

                # Publish via MQTT broker - include modality for proper parsing
                payload = json.dumps(
                    {
                        "effect_type": effect_type,
                        "intensity": intensity,
                        "duration": duration,
                        "modality": modality,
                        "parameters": parameters,
                        "device_id": device_id,
                    }
                )
                # The MQTTServer subscribes to effects/# topic internally
                # We need to use the internal client to publish
                if hasattr(self._mqtt_server, "internal_client"):
                    self._mqtt_server.internal_client.publish(
                        f"effects/{device_id}", payload
                    )
                    logger.info(
                        f"Published effect via MQTT: {effect_type} "
                        f"to effects/{device_id}"
                    )
                return True

            elif protocol == "coap" and self._coap_server:
                # For CoAP, we'd need to send a request to the server
                # This is more complex - just return True for now
                return True

            elif protocol == "upnp" and self._upnp_server:
                # UPnP is one-way discovery, not really for sending effects
                return True

            # Fall back to user-registered custom handlers.
            handler = self._custom_handlers.get(protocol)
            if handler is not None:
                send = getattr(handler, "send", None)
                if callable(send):
                    payload = {
                        "device_id": device_id,
                        "effect_type": effect_type,
                        "intensity": intensity,
                        "duration": duration,
                        "modality": modality,
                        "parameters": parameters,
                    }
                    result = send(payload)
                    if inspect.isawaitable(result):
                        result = await result
                    return bool(result)

            return False

        except Exception as e:
            logger.error(f"Failed to publish effect via {protocol}: {e}")
            return False

    def build_protocol_endpoints(
        self,
        *,
        device_id: str,
        protocols: List[str],
        provided_endpoints: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        endpoints = dict(provided_endpoints or {})

        if "mqtt" in protocols and "mqtt" not in endpoints:
            endpoints["mqtt"] = {
                "host": "localhost",
                "port": self.mqtt_port,
                "topic": f"effects/{device_id}",
                "ws_port": 9001,
            }

        if "coap" in protocols and "coap" not in endpoints:
            endpoints["coap"] = {
                "host": "localhost",
                "port": self.coap_port,
                "path": "effects",
            }

        if "http" in protocols and "http" not in endpoints:
            endpoints["http"] = {
                "url": f"http://localhost:{self.server_port}/api/effects/inbox"
            }

        if "upnp" in protocols and "upnp" not in endpoints:
            endpoints["upnp"] = {
                "control_url": (
                    f"http://localhost:{self.upnp_http_port}/control"
                )
            }

        return endpoints
