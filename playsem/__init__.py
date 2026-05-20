"""
PlaySEM - Multisensory Effect Manager Library
"""

from .device_manager import DeviceManager
from .effect_dispatcher import DispatchResult, EffectDispatcher
from .effect_metadata import EffectMetadata
from .device_registry import DeviceRegistry, DeviceInfo
from .timeline import Timeline
from .drivers.base_driver import BaseDiscovery
from .drivers.upnp_discovery import UPnPDiscovery

__all__ = [
    "DeviceManager",
    "EffectDispatcher",
    "DispatchResult",
    "EffectMetadata",
    "DeviceRegistry",
    "DeviceInfo",
    "Timeline",
    "BaseDiscovery",
    "UPnPDiscovery",
]
