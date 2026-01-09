#!/usr/bin/env python3
"""
HTTP REST API Server Demo.

Demonstrates the HTTP REST server with FastAPI for sensory effects.
Provides REST endpoints and auto-generated documentation.

Endpoints:
  POST /api/effects  - Submit effect metadata
  GET  /api/status   - Server health check
  GET  /api/devices  - List connected devices
  GET  /docs         - Interactive API documentation (Swagger UI)
  GET  /redoc        - Alternative API documentation

Run:
  python examples/demos/http_server_demo.py

Test:
  curl -X POST http://localhost:8080/api/effects \\
    -H "Content-Type: application/json" \\
    -d '{"effect_type":"light","intensity":255,"duration":2000}'

  curl http://localhost:8080/api/status

  # Or visit http://localhost:8080/docs for interactive testing
"""

import asyncio
import logging

from playsem.device_manager import DeviceManager  # noqa: E402
from playsem.effect_dispatcher import EffectDispatcher  # noqa: E402
from playsem.protocol_servers import HTTPServer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    """Run HTTP REST server."""
    logger.info("=" * 60)
    logger.info("HTTP REST API Server Demo")
    logger.info("=" * 60)

    # Create device manager (without MQTT for this demo)
    device_manager = DeviceManager(client=None)

    # Create effect dispatcher
    dispatcher = EffectDispatcher(device_manager)

    # Create HTTP server
    server = HTTPServer(
        host="0.0.0.0",  # Listen on all interfaces
        port=8080,
        dispatcher=dispatcher,
        api_key=None,  # No authentication for demo
        on_effect_received=lambda effect: logger.info(
            f"✨ Effect received via HTTP: {effect.effect_type} "
            f"(intensity={effect.intensity}, duration={effect.duration}ms)"
        ),
    )

    logger.info("")
    logger.info("Server Info:")
    logger.info("  - REST API: http://localhost:8080/api")
    logger.info("  - Docs (Swagger): http://localhost:8080/docs")
    logger.info("  - Docs (ReDoc): http://localhost:8080/redoc")
    logger.info("")
    logger.info("Try these commands:")
    logger.info("  curl http://localhost:8080/api/status")
    logger.info("")
    logger.info("  curl -X POST http://localhost:8080/api/effects \\\\")
    logger.info('    -H "Content-Type: application/json" \\\\')
    logger.info(
        '    -d \'{"effect_type":"light","intensity":255,' '"duration":2000}\''
    )
    logger.info("")
    logger.info("Or open http://localhost:8080/docs in your browser")
    logger.info("for interactive API testing!")
    logger.info("")
    logger.info("Press Ctrl+C to stop server...")
    logger.info("=" * 60)

    try:
        # Start server (runs until interrupted)
        await server.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping HTTP server...")
        await server.stop()
        logger.info("✅ Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
