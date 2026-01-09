"""
CoAP Handler - CoAP protocol handler.

Manages CoAP server lifecycle and effect distribution via CoAP.
Uses dependency injection to receive global_dispatcher.
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from playsem import EffectDispatcher


class CoAPConfig(BaseModel):
    """CoAP server configuration."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="0.0.0.0", description="CoAP server host")
    port: int = Field(default=5683, description="CoAP server port (default UDP 5683)")


class CoAPHandler:
    """Handler for CoAP (Constrained Application Protocol) integration.

    Manages:
    - CoAP server lifecycle (start/stop)
    - Effect distribution from CoAP clients
    - Resource discovery
    """

    def __init__(
        self,
        global_dispatcher: EffectDispatcher,
        config: Optional[CoAPConfig] = None,
    ):
        """Initialize CoAP handler.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
            config: CoAP configuration (uses defaults if None)
        """
        self.global_dispatcher = global_dispatcher
        self.config = config or CoAPConfig()

        # Server state
        self.server = None
        self.is_running = False

        print(
            f"[*] CoAPHandler initialized "
            f"(server={self.config.host}:{self.config.port})"
        )

    async def start(self) -> None:
        """Start CoAP server.

        Raises:
            RuntimeError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("CoAP server already running")

        try:
            print(
                f"[*] Starting CoAP server on {self.config.host}:"
                f"{self.config.port}..."
            )

            from playsem.protocol_servers import CoAPServer

            self.server = CoAPServer(
                host=self.config.host,
                port=self.config.port,
                dispatcher=self.global_dispatcher,
            )

            # Start in background
            await self.server.start()
            self.is_running = True

            print(
                f"[OK] CoAP server started on "
                f"coap://{self.config.host}:{self.config.port}"
            )
            print(f"     Resources: coap://{self.config.host}:{self.config.port}/.well-known/core")

        except Exception as e:
            print(f"[ERROR] Failed to start CoAP server: {e}")
            raise RuntimeError(f"CoAP server failed: {e}") from e

    async def stop(self) -> None:
        """Stop CoAP server.

        Raises:
            RuntimeError: If server fails to stop
        """
        if not self.is_running:
            print("[WARNING] CoAP server not running")
            return

        try:
            print("[*] Stopping CoAP server...")

            if self.server:
                await self.server.stop()

            self.is_running = False
            print("[OK] CoAP server stopped")

        except Exception as e:
            print(f"[ERROR] Failed to stop CoAP server: {e}")
            raise RuntimeError(f"CoAP server stop failed: {e}") from e

    async def send_effect(self, device_id: str, effect_name: str, **parameters) -> bool:
        """
        Send effect via CoAP handler (delegates to dispatcher).

        Args:
            device_id: Target device ID
            effect_name: Effect name
            **parameters: Effect parameters

        Returns:
            True if effect sent successfully
        """
        try:
            await self.global_dispatcher.dispatch_effect(
                device_id=device_id,
                effect_name=effect_name,
                parameters=parameters,
            )
            return True
        except Exception as e:
            print(f"[ERROR] CoAP handler failed to send effect: {e}")
            return False

    def get_status(self) -> dict:
        """Get CoAP handler status.

        Returns:
            Status dictionary with server info
        """
        return {
            "protocol": "coap",
            "running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "transport": "UDP",
        }
