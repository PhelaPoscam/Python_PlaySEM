#!/usr/bin/env python3
"""
WebSocket Server demo - demonstrates real-time bidirectional effect communication.

This example shows how to:
1. Start a WebSocket server for web apps and VR applications
2. Receive effect requests via WebSocket connections
3. Broadcast effects to all connected clients
4. Handle real-time bidirectional communication

Prerequisites:
- Install: pip install websockets

To test:
1. Run this script: python examples/websocket_server_demo.py
2. Open examples/websocket_client.html in a web browser
3. Send effects through the web interface
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher
from src.protocol_server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def on_effect_received(effect):
    """Callback when effect is received."""
    logger.info(f"✓ Received effect: {effect.effect_type} "
                f"(intensity={effect.intensity}, duration={effect.duration}ms)")


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
    mock_client = type('MockClient', (), {
        'publish': lambda *args: None
    })()
    device_manager = DeviceManager(client=mock_client)
    
    # Create dispatcher
    dispatcher = EffectDispatcher(device_manager)
    
    # Create WebSocket server
    server = WebSocketServer(
        host="localhost",
        port=8765,  # Changed from 8080 to avoid conflicts
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
        on_client_connected=on_client_connected,
        on_client_disconnected=on_client_disconnected
    )
    
    print("\n" + "=" * 60)
    print("WebSocket Server is starting...")
    print("=" * 60)
    print("\nServer URL: ws://localhost:8765")
    print("\nTo test the server:")
    print("1. Open 'examples/websocket_client.html' in your web browser")
    print("2. Or use a WebSocket client tool")
    print("3. Send JSON messages like:")
    print('   {"type":"effect","effect_type":"light","intensity":100,"duration":1000}')
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
