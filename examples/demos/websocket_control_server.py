#!/usr/bin/env python3
"""
WebSocket-Only Server - Simple demo for the control panel.

This runs only the WebSocket server for easy testing with the control panel.
No MQTT broker or CoAP setup needed.

Run:
  python examples/websocket_control_server.py
"""

import sys
import asyncio
import logging
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_manager import DeviceManager  # noqa: E402
from src.effect_dispatcher import EffectDispatcher  # noqa: E402
from src.protocol_server import WebSocketServer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def on_effect_received(effect):
    """Callback when effect is received."""
    logger.info(
        "✓ Received: %s (intensity=%s, duration=%sms, location=%s)",
        effect.effect_type,
        effect.intensity,
        effect.duration,
        effect.location or "none",
    )


async def main():
    """Main entry point."""
    # No MQTT client needed for WebSocket-only server
    device_manager = DeviceManager(client=None)
    dispatcher = EffectDispatcher(device_manager)

    # Create WebSocket server
    server = WebSocketServer(
        host="localhost",
        port=8765,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
    )

    print("\n" + "=" * 70)
    print("PythonPlaySEM WebSocket Control Server")
    print("=" * 70)
    print("\n🚀 Server: ws://localhost:8765")
    print("🎮 Control Panel: Open examples/control_panel.html in your browser")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await server.stop()
        print("\nServer stopped.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
