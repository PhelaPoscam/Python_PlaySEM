"""
WebSocket Handler - Bidirectional protocol handler.

Manages WebSocket server lifecycle and bidirectional effect communication.
Uses dependency injection to receive global_dispatcher.
"""

from typing import Optional

from pydantic import BaseModel, Field

from playsem import EffectDispatcher


class WebSocketConfig(BaseModel):
    """WebSocket server configuration."""

    host: str = Field(default="0.0.0.0", description="WebSocket server host")
    port: int = Field(default=8081, description="WebSocket server port")

    class Config:
        """Pydantic config."""

        frozen = True


class WebSocketHandler:
    """Handler for WebSocket protocol integration.

    Manages:
    - WebSocket server lifecycle (start/stop)
    - Bidirectional effect communication
    - Real-time device status updates
    - Client connection tracking
    """

    def __init__(
        self,
        global_dispatcher: EffectDispatcher,
        config: Optional[WebSocketConfig] = None,
    ):
        """Initialize WebSocket handler.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
            config: WebSocket configuration (uses defaults if None)
        """
        self.global_dispatcher = global_dispatcher
        self.config = config or WebSocketConfig()

        # Server state
        self.server = None
        self.is_running = False
        self.connected_clients = set()

        print(
            f"[*] WebSocketHandler initialized "
            f"(server={self.config.host}:{self.config.port})"
        )

    async def start(self) -> None:
        """Start WebSocket server."""
        if self.is_running:
            print("[*] WebSocket server already running")
            return

        try:
            from playsem.protocol_servers import WebSocketServer

            self.server = WebSocketServer(
                host=self.config.host,
                port=self.config.port,
                global_dispatcher=self.global_dispatcher,
            )

            await self.server.start()
            self.is_running = True

            print(
                f"[OK] WebSocket server started on "
                f"{self.config.host}:{self.config.port}"
            )
        except Exception as e:
            print(f"[ERROR] Failed to start WebSocket server: {e}")
            raise

    async def stop(self) -> None:
        """Stop WebSocket server."""
        if not self.is_running:
            print("[*] WebSocket server not running")
            return

        try:
            if self.server:
                await self.server.stop()

            self.is_running = False
            print("[OK] WebSocket server stopped")
        except Exception as e:
            print(f"[ERROR] Failed to stop WebSocket server: {e}")
            raise

    async def send_effect(
        self,
        device_id: str,
        effect_data: dict,
    ) -> bool:
        """Send effect to device via WebSocket.

        Args:
            device_id: Target device ID
            effect_data: Effect data to send

        Returns:
            True if effect was sent successfully
        """
        if not self.is_running or not self.server:
            return False

        try:
            await self.global_dispatcher.dispatch_effect(
                device_id=device_id,
                effect=effect_data,
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send effect: {e}")
            return False

    def get_status(self) -> dict:
        """Get WebSocket handler status."""
        return {
            "protocol": "WebSocket",
            "is_running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "connected_clients": len(self.connected_clients),
            "server_type": "asyncio-ws",
        }

    async def broadcast_status(self, status: dict) -> None:
        """Broadcast device status to all connected clients.

        Args:
            status: Device status data
        """
        if self.server:
            try:
                await self.server.broadcast(status)
            except Exception as e:
                print(f"[ERROR] Failed to broadcast status: {e}")

    async def register_client(self, client_id: str) -> None:
        """Register a connected WebSocket client.

        Args:
            client_id: Client identifier
        """
        self.connected_clients.add(client_id)
        print(f"[OK] Client registered: {client_id}")

    async def unregister_client(self, client_id: str) -> None:
        """Unregister a disconnected WebSocket client.

        Args:
            client_id: Client identifier
        """
        self.connected_clients.discard(client_id)
        print(f"[OK] Client unregistered: {client_id}")
