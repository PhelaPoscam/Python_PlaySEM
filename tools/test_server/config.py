"""
Configuration for Control Panel Server.

Centralized configuration management including constants,
settings, and environment variables.
"""

from pathlib import Path
from typing import Dict, Any

# Server Configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
API_TITLE = "PythonPlaySEM Control Panel API"
API_VERSION = "0.1.0"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Root for static UI assets served by the control panel
UI_ROOT = PROJECT_ROOT / "tools" / "ui_demos"  # Phase 3D: renamed from tools/ui

# UI Files
UI_FILES = {
    "controller": UI_ROOT / "controller.html",
    "receiver": UI_ROOT / "receiver.html",
    "super_controller": UI_ROOT / "super_controller.html",
    "super_receiver": UI_ROOT / "super_receiver.html",
    "mobile_device": UI_ROOT / "mobile_device.html",
}

# Protocol Servers
PROTOCOL_PORTS = {
    "mqtt": 1883,
    "coap": 5683,
    "http": 8080,
    "upnp": 1900,
}

# Device Type Constants
DEVICE_TYPES = {
    "bluetooth": "Bluetooth",
    "serial": "Serial",
    "mqtt": "MQTT",
    "mock": "Mock",
}

# WebSocket Configuration
WS_RECONNECT_TIMEOUT = 30  # seconds
WS_HEARTBEAT_INTERVAL = 30  # seconds

# Effect Configuration
EFFECT_TIMEOUT = 60  # seconds
MAX_EFFECT_QUEUE = 1000


class ServerConfig:
    """Server configuration container."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        debug: bool = False,
    ):
        """Initialize server configuration.

        Args:
            host: Server host address
            port: Server port number
            debug: Enable debug mode
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.base_url = f"http://{host}:{port}"

    def get_ui_path(self, ui_name: str | None = None) -> Path:
        """Get path to a UI file or the UI root directory.

        Args:
            ui_name: Optional UI file key (e.g., 'super_controller'). If omitted,
                returns the UI root directory.

        Returns:
            Path to the requested UI resource.
        """
        if ui_name is None:
            return UI_ROOT
        return UI_FILES.get(ui_name, UI_ROOT / ui_name)

    def get_protocol_port(self, protocol: str) -> int:
        """Get port for protocol server.

        Args:
            protocol: Protocol name (e.g., 'mqtt')

        Returns:
            Port number for protocol
        """
        return PROTOCOL_PORTS.get(protocol, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "base_url": self.base_url,
        }
