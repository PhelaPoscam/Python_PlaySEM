"""
MQTT server for receiving sensory effect requests.
"""

import asyncio
import json
import logging
import socket
import threading
from typing import Optional, Callable

try:
    from amqtt.broker import Broker

    AMQTT_AVAILABLE = True
except ImportError:
    AMQTT_AVAILABLE = False
    Broker = None

import paho.mqtt.client as mqtt

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata, EffectMetadataParser

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
        use_external_broker: bool = False,
        external_host: Optional[str] = None,
        external_port: Optional[int] = None,
    ):
        """
        Initialize the embedded MQTT Broker or external broker connection.
        """
        self.dispatcher = dispatcher
        self.host = host
        self.port = port
        self.subscribe_topic = subscribe_topic
        self.on_effect_broadcast = on_effect_broadcast
        self.use_external_broker = use_external_broker
        self.external_host = external_host
        self.external_port = external_port
        self.broker = None
        self._is_running = False
        self._lock = threading.Lock()
        self.loop = None
        self.internal_client = None
        self._ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._recent_message_ids: dict[str, float] = {}
        self._dedupe_window_seconds = 1.0
        self._subscribed = threading.Event()
        self.ws_port = self._pick_free_port()
        self.main_loop = None

        logger.info(
            f"MQTT Broker Server initialized - "
            f"Host: {host}:{port}, Topic: {subscribe_topic}, "
            f"external: {use_external_broker}"
        )

    def start(self):
        """
        Start the MQTT Broker or client connection.
        """
        with self._lock:
            if self._is_running:
                logger.warning("MQTT Broker/Client already running")
                return

            try:
                self.main_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.main_loop = None

            if self.use_external_broker:
                logger.info(
                    "Using external MQTT broker. Bypassing embedded broker startup."
                )
                self._is_running = True
                self._start_external_client()
                return

            logger.info(f"Starting embedded MQTT broker on {self.host}:{self.port}")
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
        try:
            self.loop.run_until_complete(self._start_broker())
            self.loop.run_until_complete(
                self._broker_main_loop_with_shutdown()
            )  # Run main loop until stop event
        except Exception as e:
            logger.error(f"MQTT broker failed to start or run: {e}")
            with self._lock:
                self._is_running = False
        finally:
            try:
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            except Exception:
                logger.exception(
                    "Failed to shutdown async generators during MQTT broker cleanup"
                )
            self.loop.close()  # Close the loop cleanly

    async def _start_broker(self):
        """
        Configure and start the amqtt broker.
        """
        if not AMQTT_AVAILABLE:
            logger.error("amqtt library is not installed. Cannot start MQTT broker.")
            return

        try:
            from amqtt.broker import BrokerConfig

            config = BrokerConfig.from_dict(
                {
                    "listeners": {
                        "default": {
                            "bind": f"{self.host}:{self.port}",
                            "type": "tcp",
                        },
                        "ws": {
                            "bind": f"{self.host}:{self.ws_port}",
                            "type": "ws",
                            "max_connections": 10,
                        },
                    },
                    "plugins": {
                        "amqtt.plugins.logging_amqtt.EventLoggerPlugin": {},
                        "amqtt.plugins.logging_amqtt.PacketLoggerPlugin": {},
                        "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                            "allow_anonymous": True,
                        },
                        "amqtt.plugins.sys.broker.BrokerSysPlugin": {
                            "sys_interval": 20,
                        },
                    },
                }
            )
            self.broker = Broker(config)
            logger.debug("amqtt Broker instance created.")
            await self.broker.start()
            logger.info(
                "amqtt Broker started and listening on " f"{self.host}:{self.port}"
            )
            logger.warning(
                "Embedded MQTT broker running with anonymous authentication — "
                "ensure only trusted network access"
            )

            self._setup_client()
            # Use localhost for client connection instead of
            # 0.0.0.0 (server binding address).
            connect_host = "localhost" if self.host == "0.0.0.0" else self.host
            self.internal_client.connect(connect_host, self.port, 60)
            self.internal_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to start MQTT broker: {e}")
            self.broker = None

    def _setup_client(self):
        """Helper to configure the internal paho-mqtt client."""
        # Prefer callback API v2 when available to avoid deprecation warnings.
        try:
            self.internal_client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except Exception:
            logger.warning(
                "Could not initialize MQTT client with VERSION2 API, falling back",
                exc_info=True,
            )
            self.internal_client = mqtt.Client()
        self.internal_client.on_message = self._on_internal_message

        def _on_connect(client, userdata, flags, rc, properties=None):
            try:
                client.subscribe(self.subscribe_topic, qos=0)
                logger.debug(
                    "Internal MQTT client subscribed to "
                    f"{self.subscribe_topic} (qos=0)"
                )
                self._ready_event.set()
            except Exception as e:
                logger.error(f"Internal MQTT subscribe error: {e}")

        self.internal_client.on_connect = _on_connect

        def _on_subscribe(client, userdata, mid, granted_qos, properties=None):
            try:
                self._subscribed.set()
                self._ready_event.set()
            except Exception as e:
                logger.error(f"Internal MQTT on_subscribe error: {e}")

        self.internal_client.on_subscribe = _on_subscribe

    def _start_external_client(self):
        """Connects and starts the MQTT client for an external broker."""
        try:
            self._setup_client()
            connect_host = self.external_host or "127.0.0.1"
            connect_port = self.external_port or 1883
            logger.info(
                f"Connecting to external MQTT broker at {connect_host}:{connect_port}..."
            )
            self.internal_client.connect(connect_host, connect_port, 60)
            self.internal_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to external MQTT broker: {e}")
            self._is_running = False

    def _on_internal_message(self, client, userdata, msg):
        """
        Callback when message is received by the internal paho-mqtt client.
        """
        topic = msg.topic
        payload = msg.payload
        try:
            payload_str = payload.decode("utf-8")
            logger.debug(f"Broker received message on topic '{topic}': {payload_str}")

            # Deduplicate only when the sender provides an explicit message
            # identity. Identical haptic pulses are valid timeline events.
            import time

            message_id = self._extract_message_id(topic, payload_str)
            now = time.monotonic()
            if message_id is not None:
                last_seen = self._recent_message_ids.get(message_id)
                if (
                    last_seen is not None
                    and (now - last_seen) < self._dedupe_window_seconds
                ):
                    logger.debug(
                        "Duplicate MQTT message id ignored "
                        f"(within {self._dedupe_window_seconds}s window)"
                    )
                    return
                self._recent_message_ids[message_id] = now
                self._prune_recent_message_ids(now)

            effect = self._parse_effect(payload_str)
            if effect:
                main_loop = self.main_loop
                dispatch_loop = (
                    main_loop
                    if (main_loop is not None and main_loop.is_running())
                    else self.loop
                )

                if dispatch_loop is None:
                    logger.error("MQTT effect dropped: no dispatch loop available")
                    return

                future = asyncio.run_coroutine_threadsafe(
                    self.dispatcher.async_dispatch_effect_metadata(effect),
                    dispatch_loop,
                )
                future.add_done_callback(
                    lambda f: f.exception()
                    and logger.error(
                        "MQTT effect dispatch failed", exc_info=f.exception()
                    )
                )
                logger.info("Effect " f"'{effect.effect_type}' " "submitted via MQTT")
                if self.on_effect_broadcast:
                    broadcast_future = asyncio.run_coroutine_threadsafe(
                        self.on_effect_broadcast(effect, "mqtt_broadcast"),
                        dispatch_loop,
                    )
                    broadcast_future.add_done_callback(
                        lambda f: f.exception()
                        and logger.error(
                            "MQTT broadcast callback failed", exc_info=f.exception()
                        )
                    )
            else:
                logger.warning(
                    f"Failed to parse effect from MQTT payload: {payload_str}"
                )

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _pick_free_port(self) -> int:
        """Reserve and return a currently free local TCP port."""
        bind_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((bind_host, 0))
            return int(sock.getsockname()[1])

    async def _broker_main_loop_with_shutdown(self):
        """
        Main loop for the broker, waits for a stop signal.
        """
        while not self._stop_event.is_set():
            await asyncio.sleep(0.05)
        logger.info("Stop event received, initiating amqtt broker shutdown.")
        if self.broker:
            try:
                await self.broker.shutdown()
            except Exception as e:
                logger.debug(f"amqtt broker shutdown note: {e}")
        logger.info("amqtt broker shutdown complete.")

    async def wait_until_ready(self):
        """
        Wait until the embedded MQTT Broker is fully started
        and ready to accept connections.
        """
        while not self._ready_event.is_set():
            await asyncio.sleep(0.05)

    def stop(self):
        """
        Stop the MQTT Broker/Client.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("MQTT Broker/Client not running")
                return

            logger.info("Stopping MQTT Broker/Client...")
            if self.internal_client:
                self.internal_client.loop_stop()
                self.internal_client.disconnect()

            if not self.use_external_broker:
                self._stop_event.set()
                self.thread.join(timeout=5.0)
                if self.thread.is_alive():
                    logger.warning(
                        "MQTT broker thread did not exit cleanly within timeout"
                    )
                    self.thread.join(timeout=5.0)

            self._is_running = False
            logger.info("MQTT Broker/Client stopped")

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
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            try:
                return EffectMetadataParser.parse_yaml(payload)
            except Exception:
                logger.warning(
                    "Failed to parse MQTT payload as JSON or YAML", exc_info=True
                )
                return None

    def _extract_message_id(
        self, topic: str, payload: str
    ) -> Optional[tuple[str, str]]:
        """Return an explicit sender-provided dedupe key if present."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        for key in ("idempotency_key", "message_id", "event_id"):
            value = data.get(key)
            if value is not None:
                return (topic, f"{key}:{value}")
        return None

    def _prune_recent_message_ids(self, now: float) -> None:
        """Bound memory used by short-window MQTT id dedupe."""
        expired = [
            message_id
            for message_id, last_seen in self._recent_message_ids.items()
            if (now - last_seen) >= self._dedupe_window_seconds
        ]
        for message_id in expired:
            self._recent_message_ids.pop(message_id, None)
