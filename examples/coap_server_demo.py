#!/usr/bin/env python3
"""
CoAP Server demo - receive and process effects over CoAP.

This example starts a CoAP server listening on localhost:5683.
Use the provided test client to send effects.

Prerequisites:
- pip install aiocoap

Run:
  python examples/coap_server_demo.py

Send test effect (from another terminal):
  python examples/test_coap_client.py
"""

import sys
import asyncio
import logging
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.device_manager import DeviceManager  # noqa: E402
from src.effect_dispatcher import EffectDispatcher  # noqa: E402
from src.protocol_server import CoAPServer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def on_effect_received(effect):
    logger.info(
        "✓ Received effect: %s (intensity=%s, duration=%sms)",
        effect.effect_type,
        effect.intensity,
        effect.duration,
    )


async def main():
    print("\n" + "=" * 60)
    print("PythonPlaySEM CoAP Server Demo")
    print("=" * 60)

    logger.info("Initializing components...")

    # Mock MQTT client for DeviceManager to avoid real broker
    mock_client = type('MockClient', (), {'publish': lambda *args: None})()
    device_manager = DeviceManager(client=mock_client)
    dispatcher = EffectDispatcher(device_manager)

    server = CoAPServer(
        host="localhost",
        port=5683,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
    )

    print("\nCoAP Server is starting...\n")
    print("Server URL: coap://localhost:5683")
    print("\nTo test the server:")
    print("1. Run 'python examples/test_coap_client.py'")
    print("2. Or use 'aiocoap-client' CLI tool if installed")
    print("\nPress Ctrl+C to stop the server.\n")

    try:
        # Run server until cancelled
        await asyncio.gather(server.start())
    except KeyboardInterrupt:
        print("\nStopping CoAP server...")
        await server.stop()
        print("Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
