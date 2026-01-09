"""
UPnP Handler - UPnP/SSDP protocol handler.

Manages UPnP server lifecycle and device discovery.
Uses dependency injection to receive global_dispatcher.
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from playsem import EffectDispatcher


class UPnPConfig(BaseModel):
    """UPnP server configuration."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="0.0.0.0", description="UPnP server host")
    port: int = Field(default=1900, description="UPnP/SSDP port (multicast 239.255.255.250:1900)")
    device_name: str = Field(default="PlaySEM Device", description="UPnP device friendly name")
    device_type: str = Field(default="urn:schemas-upnp-org:device:HapticDevice:1", description="UPnP device type")


class UPnPHandler:
    """Handler for UPnP/SSDP (Universal Plug and Play) integration.

    Manages:
    - UPnP server lifecycle (start/stop)
    - SSDP device discovery and advertisement
    - Effect distribution from UPnP control points
    """

    def __init__(
        self,
        global_dispatcher: EffectDispatcher,
        config: Optional[UPnPConfig] = None,
    ):
        """Initialize UPnP handler.

        Args:
            global_dispatcher: Global effect dispatcher for all devices
            config: UPnP configuration (uses defaults if None)
        """
        self.global_dispatcher = global_dispatcher
        self.config = config or UPnPConfig()

        # Server state
        self.server = None
        self.is_running = False
        self.discovered_devices = set()

        print(
            f"[*] UPnPHandler initialized "
            f"(device={self.config.device_name}, port={self.config.port})"
        )

    async def start(self) -> None:
        """Start UPnP server and SSDP advertisement.

        Raises:
            RuntimeError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("UPnP server already running")

        try:
            print(
                f"[*] Starting UPnP server ({self.config.device_name})..."
            )

            from playsem.protocol_servers import UPnPServer

            self.server = UPnPServer(
                host=self.config.host,
                port=self.config.port,
                dispatcher=self.global_dispatcher,
                device_name=self.config.device_name,
                device_type=self.config.device_type,
            )

            # Start in background
            await self.server.start()
            self.is_running = True

            print(
                f"[OK] UPnP server started - advertising as '{self.config.device_name}'"
            )
            print(f"     SSDP multicast: 239.255.255.250:{self.config.port}")
            print(f"     Device type: {self.config.device_type}")

        except Exception as e:
            print(f"[ERROR] Failed to start UPnP server: {e}")
            raise RuntimeError(f"UPnP server failed: {e}") from e

    async def stop(self) -> None:
        """Stop UPnP server and SSDP advertisement.

        Raises:
            RuntimeError: If server fails to stop
        """
        if not self.is_running:
            print("[WARNING] UPnP server not running")
            return

        try:
            print("[*] Stopping UPnP server...")

            if self.server:
                await self.server.stop()

            self.is_running = False
            self.discovered_devices.clear()
            print("[OK] UPnP server stopped")

        except Exception as e:
            print(f"[ERROR] Failed to stop UPnP server: {e}")
            raise RuntimeError(f"UPnP server stop failed: {e}") from e

    async def send_effect(self, device_id: str, effect_name: str, **parameters) -> bool:
        """
        Send effect via UPnP handler (delegates to dispatcher).

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
            print(f"[ERROR] UPnP handler failed to send effect: {e}")
            return False

    def get_status(self) -> dict:
        """Get UPnP handler status.

        Returns:
            Status dictionary with server info
        """
        return {
            "protocol": "upnp",
            "running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "device_name": self.config.device_name,
            "device_type": self.config.device_type,
            "discovered_devices": len(self.discovered_devices),
        }
