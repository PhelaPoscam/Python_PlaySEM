"""Routes module - API and UI route handlers."""

from .devices import DeviceRoutes
from .effects import EffectRoutes
from .ui import UIRoutes

__all__ = [
    "DeviceRoutes",
    "EffectRoutes",
    "UIRoutes",
]
