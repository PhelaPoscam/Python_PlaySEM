#!/usr/bin/env python3
"""
PlaySEM Control Panel Backend Server

Main entry point for the web-based control panel backend.
Provides WebSocket + FastAPI server with device discovery, effect dispatch, and protocol support.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import ServerConfig
from .server import ControlPanelServer


async def main():
    """Run the control panel server."""
    # Load configuration
    config = ServerConfig()

    # Create and run server
    server = ControlPanelServer(config=config)

    try:
        await server.run(
            host=config.host,
            port=config.port,
        )
    except KeyboardInterrupt:
        print("\n[*] Shutdown requested by user")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
