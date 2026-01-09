"""
Data models for Control Panel Server.

Defines core data structures used throughout the server.
"""

from dataclasses import dataclass
from typing import Any

from playsem import DeviceManager, EffectDispatcher


@dataclass
class ConnectedDevice:
    """Represents a connected device in the control panel.

    Attributes:
        id: Unique device identifier
        name: Human-readable device name
        type: Device type ('bluetooth', 'serial', 'mqtt', 'mock')
        address: Device address/location
        driver: Device driver instance
        manager: Device manager for this connection
        dispatcher: Effect dispatcher for this connection
        connected_at: Unix timestamp of connection time
    """

    id: str
    name: str
    type: str  # 'bluetooth', 'serial', 'mqtt', 'mock'
    address: str
    driver: Any
    manager: DeviceManager
    dispatcher: EffectDispatcher
    connected_at: float
