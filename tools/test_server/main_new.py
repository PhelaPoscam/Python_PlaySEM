#!/usr/bin/env python3
"""
PlaySEM Control Panel Backend Server

Main entry point for the web-based control panel backend.
Provides WebSocket + FastAPI server with device discovery, effect dispatch, and protocol support.

This is the modular entry point using the new app factory.
Execute via module: python -m tools.test_server.main_new
"""

import sys

if __package__ in (None, ""):
    raise RuntimeError(
        "Execute this entrypoint as a module: python -m tools.test_server.main_new"
    )

import uvicorn

from .app import create_app
from .config import ServerConfig


def main():
    """Run the control panel server with modular app factory."""
    # Load configuration
    config = ServerConfig()

    # Create FastAPI application with dependency injection
    app = create_app(config=config)

    # Run with uvicorn
    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[*] Shutdown requested by user")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
