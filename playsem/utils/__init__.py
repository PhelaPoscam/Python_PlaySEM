"""
Utility modules for PlaySEM.
"""

from __future__ import annotations

import importlib
from typing import Any


def _optional_import(module_path: str, attr: str) -> Any:
    """Import an optional dependency; returns None if not installed."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    except ImportError:
        return None
