"""
HTTP Handler - HTTP REST API protocol handler.

Manages HTTP server lifecycle and RESTful effect requests.
Uses dependency injection to receive global_dispatcher.
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from playsem import EffectDispatcher


class HTTPConfig(BaseModel):
    """HTTP server configuration."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="0.0.0.0", description="HTTP server host")
    port: int = Field(default=8080, description="HTTP server port")
    api_key: Optional[str] = Field(default=None, description="Optional API key for authentication")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")


class HTTPHandler:
    """Handler for HTTP REST API protocol integration.

    Manages:
    - HTTP server lifecycle (start/stop)
    - RESTful effect requests
    - API authentication (optional)
    - CORS configuration
    """

    def __init__(
        self,
        global_dispatcher: EffectDispatcher,
        config: Optional[HTTPConfig] = None,
    ):
        """Initialize HTTP handler.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
            config: HTTP configuration (uses defaults if None)
        """
        self.global_dispatcher = global_dispatcher
        self.config = config or HTTPConfig()

        # Server state
        self.server = None
        self.is_running = False

        print(
            f"[*] HTTPHandler initialized "
            f"(server={self.config.host}:{self.config.port}, "
            f"auth={'enabled' if self.config.api_key else 'disabled'})"
        )

    async def start(self) -> None:
        """Start HTTP server.

        Raises:
            RuntimeError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("HTTP server already running")

        try:
            print(
                f"[*] Starting HTTP server on {self.config.host}:"
                f"{self.config.port}..."
            )

            from playsem.protocol_servers import HTTPServer

            self.server = HTTPServer(
                host=self.config.host,
                port=self.config.port,
                dispatcher=self.global_dispatcher,
                api_key=self.config.api_key,
                cors_origins=self.config.cors_origins,
            )

            # Start in background
            await self.server.start()
            self.is_running = True

            print(
                f"[OK] HTTP server started on "
                f"http://{self.config.host}:{self.config.port}"
            )
            print(f"     API docs: http://{self.config.host}:{self.config.port}/docs")

        except Exception as e:
            print(f"[ERROR] Failed to start HTTP server: {e}")
            raise RuntimeError(f"HTTP server failed: {e}") from e

    async def stop(self) -> None:
        """Stop HTTP server.

        Raises:
            RuntimeError: If server fails to stop
        """
        if not self.is_running:
            print("[WARNING] HTTP server not running")
            return

        try:
            print("[*] Stopping HTTP server...")

            if self.server:
                await self.server.stop()

            self.is_running = False
            print("[OK] HTTP server stopped")

        except Exception as e:
            print(f"[ERROR] Failed to stop HTTP server: {e}")
            raise RuntimeError(f"HTTP server stop failed: {e}") from e

    async def send_effect(self, device_id: str, effect_name: str, **parameters) -> bool:
        """
        Send effect via HTTP handler (delegates to dispatcher).

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
            print(f"[ERROR] HTTP handler failed to send effect: {e}")
            return False

    def get_status(self) -> dict:
        """Get HTTP handler status.

        Returns:
            Status dictionary with server info
        """
        return {
            "protocol": "http",
            "running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "auth_enabled": self.config.api_key is not None,
            "cors_origins": self.config.cors_origins,
        }
