"""
Control Panel Server for PythonPlaySEM.

A FastAPI-based backend server providing WebSocket and REST APIs
for device management, effect dispatch, and timeline control.

Main Components:
- Server: FastAPI application orchestrator
- Services: Business logic for devices, effects, timeline, protocols
- Handlers: Protocol handlers (WebSocket, HTTP)
- Routes: API endpoint definitions
- Models: Data structures
- Config: Configuration management

Usage:
    from tools.test_server import ControlPanelServer, ServerConfig

    server = ControlPanelServer(config=ServerConfig(host="0.0.0.0", port=8090))
    server.run()
"""

from .config import ServerConfig, DEFAULT_HOST, DEFAULT_PORT
from .models import ConnectedDevice

__all__ = [
    "ServerConfig",
    "ConnectedDevice",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
]

__version__ = "0.1.0"
