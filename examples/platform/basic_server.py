#!/usr/bin/env python3
"""
Basic Modular Server Example

Demonstrates the simplest usage of the PlaySEM modular architecture.
This is a minimal working server with device and effect management.

Run:
    python examples/platform/basic_server.py

Then open:
    http://localhost:8090/health
    http://localhost:8090/api/devices
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path (for examples/ to import from tools/)
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn
from tools.test_server.app import create_app
from tools.test_server.config import ServerConfig


def main():
    """Create and run the basic server."""
    
    print("=" * 60)
    print("PlaySEM Basic Modular Server Example")
    print("=" * 60)
    print()
    print("This demonstrates the Phase 3 modular architecture:")
    print("  [OK] Factory pattern (create_app)")
    print("  [OK] Service layer (DeviceService, EffectService)")
    print("  [OK] Route layer (DeviceRoutes, EffectRoutes)")
    print("  [OK] WebSocket handler")
    print()
    print("Endpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /api/devices         - List devices")
    print("  POST /api/devices/connect - Connect device")
    print("  POST /api/effects/send    - Send effect")
    print("  WS   /ws                  - WebSocket for real-time updates")
    print()
    print("-" * 60)
    print()
    
    # Configure server
    config = ServerConfig(
        host="127.0.0.1",
        port=8090,
        debug=False,  # Set True for development
    )
    
    # Create app using factory
    app = create_app(config)
    
    # Run server
    print(f"Starting server on http://{config.host}:{config.port}")
    print("Press Ctrl+C to stop")
    print()
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
