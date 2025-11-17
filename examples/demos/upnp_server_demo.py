"""
UPnP Server Demo for PlaySEM.

This demo shows how to use the UPnP server for automatic device discovery.
The server advertises itself on the local network using SSDP (Simple Service
Discovery Protocol), allowing UPnP clients to discover the PlaySEM service.

Usage:
    python examples/upnp_server_demo.py

Once running, use a UPnP discovery tool or the test_upnp_client.py to
discover the server on your local network.
"""

import asyncio
import sys
import logging
import socket
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.protocol_server import UPnPServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.effect_metadata import EffectMetadata
from src.device_driver.mock_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the UPnP server demo."""
    logger.info("=" * 60)
    logger.info("PlaySEM UPnP Server Demo")
    logger.info("=" * 60)

    # Create device manager with mock devices
    device_manager = DeviceManager()

    # Create some mock devices for demonstration
    # Note: In a real application, these would be registered with the manager
    mock_devices = [
        MockLightDevice("light_01"),
        MockWindDevice("wind_01"),
        MockVibrationDevice("vibration_01"),
        MockScentDevice("scent_01"),
    ]

    logger.info(f"Created {len(mock_devices)} mock devices for demonstration")

    # Create effect dispatcher
    dispatcher = EffectDispatcher(device_manager)
    logger.info("Effect dispatcher created")

    # Define callback for received effects
    def on_effect_received(effect: EffectMetadata):
        logger.info(f"📨 Effect received via UPnP: {effect.effect_type}")
        logger.info(
            f"   Duration: {effect.duration}ms, "
            f"Intensity: {effect.intensity}"
        )

    # Create UPnP server
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    server = UPnPServer(
        friendly_name="PlaySEM Python Server",
        dispatcher=dispatcher,
        location_url=f"http://{local_ip}:8080/description.xml",
        manufacturer="PlaySEM Community",
        model_name="PlaySEM Python Server",
        model_version="1.0.0",
        on_effect_received=on_effect_received,
    )

    logger.info("UPnP Server configured:")
    logger.info("  - Friendly Name: PlaySEM Python Server")
    logger.info(f"  - Local IP: {local_ip}")
    logger.info(f"  - UUID: {server.uuid}")
    logger.info(f"  - Device Type: {server.device_type}")
    logger.info(f"  - Service Type: {server.service_type}")

    try:
        # Start the server
        await server.start()

        logger.info("")
        logger.info("🎯 Server is now discoverable on the local network!")
        logger.info("")
        logger.info("To discover this server:")
        logger.info("  1. Run: python examples/test_upnp_client.py")
        logger.info("  2. Use any UPnP browser/scanner on your network")
        logger.info("  3. Use Windows Network Discovery")
        logger.info("")
        logger.info("Device Description XML:")
        logger.info(server.get_device_description_xml())
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received")
    finally:
        logger.info("Stopping UPnP server...")
        await server.stop()
        logger.info("✅ Server stopped gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
