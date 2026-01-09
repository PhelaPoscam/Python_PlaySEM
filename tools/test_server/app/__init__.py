"""
PlaySEM Control Panel Application Package

Thin orchestrator for the FastAPI application factory.
All business logic is delegated to services.
"""

from .main import create_app

__all__ = ["create_app"]
