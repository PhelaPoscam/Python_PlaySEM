"""
MQTT Handler - Isolated protocol-specific handler.

Manages MQTT server lifecycle and effect distribution.
Uses dependency injection to receive global_dispatcher.
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from playsem import EffectDispatcher


class MQTTConfig(BaseModel):
    """MQTT server configuration."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="127.0.0.1", description="MQTT broker host")
    port: int = Field(default=1883, description="MQTT broker port")
    broker_id: str = Field(default="playsem-mqtt", description="Broker ID")
    username: Optional[str] = Field(default=None, description="MQTT username")
    password: Optional[str] = Field(default=None, description="MQTT password")
    keepalive: int = Field(default=60, description="Keep-alive interval")


class MQTTHandler:
    """Handler for MQTT protocol integration.

    Manages:
    - MQTT server lifecycle (start/stop)
    - Effect distribution from MQTT clients
    - Client connection/disconnection tracking
    """

    def __init__(
        self,
        global_dispatcher: EffectDispatcher,
        config: Optional[MQTTConfig] = None,
    ):
        """Initialize MQTT handler.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
            config: MQTT configuration (uses defaults if None)
        """
        self.global_dispatcher = global_dispatcher
        self.config = config or MQTTConfig()

        # Server state
        self.server = None
        self.is_running = False
        self.connected_clients = set()

        print(
            f"[*] MQTTHandler initialized "
            f"(broker={self.config.host}:{self.config.port})"
        )

    async def start(self) -> None:
        """Start MQTT server.

        Raises:
            RuntimeError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("MQTT server already running")

        try:
            print(
                f"[*] Starting MQTT server on {self.config.host}:"
                f"{self.config.port}..."
            )

            from playsem.protocol_servers import MQTTServer

            self.server = MQTTServer(
                host=self.config.host,
                port=self.config.port,
                broker_id=self.config.broker_id,
            )

            await self.server.start()
            self.is_running = True

            print(
                f"[OK] MQTT server started on "
                f"{self.config.host}:{self.config.port}"
            )

        except ImportError as e:
            raise RuntimeError(f"MQTT dependencies not installed: {e}")
        except Exception as e:
            self.is_running = False
            raise RuntimeError(f"Failed to start MQTT server: {e}")

    async def stop(self) -> None:
        """Stop MQTT server.

        Handles both sync and async stop methods gracefully.
        """
        if not self.is_running or not self.server:
            return

        try:
            print("[*] Stopping MQTT server...")

            if hasattr(self.server, "stop"):
                # Try to call stop method
                stop_method = self.server.stop
                if hasattr(stop_method, "__await__"):
                    await stop_method()
                else:
                    # Sync stop in thread to avoid blocking
                    import asyncio

                    await asyncio.to_thread(stop_method)

            elif hasattr(self.server, "shutdown"):
                await self.server.shutdown()

            self.is_running = False
            print("[OK] MQTT server stopped")

        except Exception as e:
            print(f"[WARNING] Error stopping MQTT server: {e}")
            self.is_running = False

    async def broadcast_effect(
        self,
        effect_type: str,
        intensity: int,
        duration: int,
        device_id: str = "mqtt_client",
    ) -> None:
        """Broadcast effect from MQTT to all devices.

        Args:
            effect_type: Type of effect (vibration, light, wind, etc)
            intensity: Effect intensity (0-100)
            duration: Duration in milliseconds
            device_id: Source device ID
        """
        if not self.is_running:
            raise RuntimeError("MQTT server not running")

        try:
            from playsem.effect_metadata import create_effect

            effect = create_effect(
                effect_type=effect_type,
                intensity=intensity,
                duration=duration,
                timestamp=0,
            )

            # Dispatch to all connected devices
            self.global_dispatcher.dispatch_effect_metadata(effect)

            print(
                f"[OK] MQTT broadcast: {effect_type} "
                f"(intensity={intensity}, duration={duration})"
            )

        except Exception as e:
            print(f"[ERROR] Failed to broadcast effect: {e}")
            raise

    async def handle_client_connect(self, client_id: str) -> None:
        """Handle MQTT client connection.

        Args:
            client_id: Connected client ID
        """
        self.connected_clients.add(client_id)
        print(f"[MQTT] Client connected: {client_id}")

    async def handle_client_disconnect(self, client_id: str) -> None:
        """Handle MQTT client disconnection.

        Args:
            client_id: Disconnected client ID
        """
        self.connected_clients.discard(client_id)
        print(f"[MQTT] Client disconnected: {client_id}")

    def get_status(self) -> dict:
        """Get MQTT handler status.

        Returns:
            Status dictionary with server state and connected clients
        """
        return {
            "protocol": "mqtt",
            "is_running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "connected_clients": len(self.connected_clients),
            "clients": list(self.connected_clients),
        }
