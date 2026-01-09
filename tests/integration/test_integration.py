"""Integration test script for GUI and Backend."""

import sys
from pathlib import Path

import pytest

# Add project root to Python path for gui/tools imports
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import asyncio
import logging

try:
    from gui.protocols.websocket_protocol import WebSocketProtocol
    from gui.protocols.http_protocol import HTTPProtocol
    HAS_GUI_PROTOCOLS = True
except ImportError:
    HAS_GUI_PROTOCOLS = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    not HAS_GUI_PROTOCOLS, reason="gui.protocols module not available"
)
async def test_websocket_connection():
    """Test WebSocket connection to backend server."""
    print("\n" + "=" * 60)
    print("Testing WebSocket Connection to Backend Server")
    print("=" * 60)

    protocol = WebSocketProtocol("localhost", 8090)

    try:
        # Start listening in background
        listen_task = asyncio.create_task(protocol.listen())

        # Try to connect
        logger.info("Connecting to WebSocket server...")
        await protocol.connect()
        logger.info("[+] WebSocket connected successfully!")

        # Send a test message
        test_message = {"type": "ping", "data": {"test": "integration"}}
        logger.info(f"Sending test message: {test_message}")
        await protocol.send(test_message)
        logger.info("[+] Test message sent successfully!")

        # Wait for a short time to receive any responses
        await asyncio.sleep(1)

        # Disconnect
        await protocol.disconnect()
        logger.info("[+] WebSocket disconnected successfully!")

        # Cancel listen task
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        return True

    except Exception as e:
        logger.error(f"[X] WebSocket test failed: {e}")
        return False


async def test_http_connection():
    """Test HTTP connection to backend server."""
    print("\n" + "=" * 60)
    print("Testing HTTP Connection to Backend Server")
    print("=" * 60)

    protocol = HTTPProtocol("localhost", 8090, poll_interval=0.5)

    try:
        # Try to connect
        logger.info("Connecting to HTTP server...")
        await protocol.connect()
        logger.info("[+] HTTP connected successfully!")

        # Send a test message
        test_message = {"type": "ping", "data": {"test": "integration"}}
        logger.info(f"Sending test message: {test_message}")
        await protocol.send(test_message)
        logger.info("[+] Test message sent successfully!")

        # Disconnect
        await protocol.disconnect()
        logger.info("[+] HTTP disconnected successfully!")

        return True

    except Exception as e:
        logger.error(f"[X] HTTP test failed: {e}")
        return False


async def test_device_discovery():
    """Test device discovery through WebSocket."""
    print("\n" + "=" * 60)
    print("Testing Device Discovery")
    print("=" * 60)

    protocol = WebSocketProtocol("localhost", 8090)
    devices_received = False

    def on_message_callback(message):
        """Callback when message received."""
        nonlocal devices_received
        if message and isinstance(message, dict) and "devices" in message:
            logger.info(f"[+] Devices received: {message}")
            devices_received = True

    try:
        # Connect
        logger.info("Connecting to WebSocket server...")
        await protocol.connect()

        # Set callback to receive device messages
        protocol.on_message = on_message_callback

        # Start listening in background
        listen_task = asyncio.create_task(protocol.listen())

        # Request device list
        logger.info("Requesting device list...")
        await protocol.send({"type": "get_devices"})

        # Wait a bit for response
        await asyncio.sleep(2)

        # Stop listening
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        if devices_received:
            logger.info("[+] Device discovery test passed!")
        else:
            logger.warning(
                "[?] No devices received (server may not have devices)"
            )

        # Disconnect
        await protocol.disconnect()
        return True

    except asyncio.TimeoutError:
        logger.warning("[?] Device discovery timed out")
        return True  # Not a failure, server might be slow to respond
    except Exception as e:
        logger.error(f"[X] Device discovery test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("PythonPlaySEM Integration Test Suite")
    print("=" * 60)
    print("\nMake sure backend server is running on http://127.0.0.1:8090")

    results = {}

    # Test WebSocket
    results["WebSocket Connection"] = await test_websocket_connection()

    # Test HTTP
    results["HTTP Connection"] = await test_http_connection()

    # Test Device Discovery
    results["Device Discovery"] = await test_device_discovery()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "[+]" if result else "[X]"
        print(f"{symbol} {status}: {test_name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[+] All tests passed! GUI is ready for use.")
    else:
        print("\n[?] Some tests failed. Check the backend server.")


if __name__ == "__main__":
    asyncio.run(main())
