#!/usr/bin/env python3
"""
WebSocket Server demo - demonstrates real-time bidirectional effect
communication.

This example shows how to:
1. Start a WebSocket server for web apps and VR applications
2. Receive effect requests via WebSocket connections
3. Broadcast effects to all connected clients
4. Handle real-time bidirectional communication

Prerequisites:
- Install: pip install websockets qrcode[pil]

To test:
1. Run this script: python examples/websocket_server_demo.py
2. Scan the generated QR code with your phone
3. Send effects through the web interface
"""

import asyncio
import logging
import qrcode
import socket

from playsem import DeviceManager, EffectDispatcher
from playsem.protocol_servers import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def get_local_ip():
    """Gets the local IP address of the machine."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't have to be reachable
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        if s:
            s.close()
    return ip


def on_effect_received(effect):
    """Callback when effect is received."""
    logger.info(
        f"✓ Received effect: {effect.effect_type} "
        f"(intensity={effect.intensity}, duration={effect.duration}ms)"
    )


def on_client_connected(client_id):
    """Callback when client connects."""
    logger.info(f"🔗 Client connected: {client_id}")


def on_client_disconnected(client_id):
    """Callback when client disconnects."""
    logger.info(f"❌ Client disconnected: {client_id}")


async def main():
    print("\n" + "=" * 60)
    print("PythonPlaySEM WebSocket Server Demo")
    print("=" * 60)

    # Create components
    logger.info("Initializing components...")

    # Use mock client for demo (in production, use real DeviceManager)
    mock_client = type("MockClient", (), {"publish": lambda *args: None})()
    device_manager = DeviceManager(client=mock_client)  # type: ignore

    # Create dispatcher
    dispatcher = EffectDispatcher(device_manager)

    # --- QR Code Generation ---
    host_ip = get_local_ip()
    http_port = 8000  # Standard port for the simple HTTP server
    ws_port = 8765
    client_url = f"http://{host_ip}:{http_port}/websocket_client.html?ws_url=ws://{host_ip}:{ws_port}"

    print("\n" + "=" * 60)
    print("📱 Connect with your phone")
    print("=" * 60)
    print("\nScan the QR code below to open the client:")

    qr = qrcode.QRCode()
    qr.add_data(client_url)
    qr.print_ascii(invert=True)

    print(f"\nOr open manually: {client_url}")
    # --- End of QR Code Generation ---

    # Create WebSocket server
    server = WebSocketServer(
        host="0.0.0.0",
        port=ws_port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
        on_client_connected=on_client_connected,
        on_client_disconnected=on_client_disconnected,
    )

    print("\n" + "=" * 60)
    print("WebSocket Server is starting...")
    print("=" * 60)
    print(f"\nServer URL: ws://{host_ip}:{ws_port}")
    print("\nPress Ctrl+C to stop the server.\n")

    try:
        # Start server (this will run until interrupted)
        await server.start()

    except KeyboardInterrupt:
        logger.info("\n\nShutting down server...")
        await server.stop()
        logger.info("Server stopped. Goodbye!")

    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nServer interrupted.")
