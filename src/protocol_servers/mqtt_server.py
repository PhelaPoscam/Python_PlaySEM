"""
MQTT server for receiving sensory effect requests.
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable

try:
    from amqtt.broker import Broker
    from amqtt.mqtt.constants import QOS_0

    AMQTT_AVAILABLE = True
except ImportError:
    AMQTT_AVAILABLE = False
    Broker = None
    QOS_0 = None

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
