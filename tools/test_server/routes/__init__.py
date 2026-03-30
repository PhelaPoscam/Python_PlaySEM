"""Route modules for the modular PlaySEM test server."""

from .devices import router as devices_router
from .effects import router as effects_router
from .ui import router as ui_router

__all__ = ["devices_router", "effects_router", "ui_router"]
