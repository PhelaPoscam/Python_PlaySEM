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
import logging
import socket

from playsem.protocol_servers import UPnPServer
from playsem.effect_dispatcher import EffectDispatcher
from playsem.device_manager import DeviceManager
from playsem.effect_metadata import EffectMetadata
from playsem.drivers.mock_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
    MockConnectivityDriver,
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
    mock_driver = MockConnectivityDriver()
    device_manager = DeviceManager(connectivity_driver=mock_driver)

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

    # Create UPnP server. The server will auto-detect the host IP.
    # The http_port is for serving the XML description files.
    server = UPnPServer(
        friendly_name="PlaySEM Python Server",
        dispatcher=dispatcher,
        http_port=8080,  # You can change this port if needed
        manufacturer="PlaySEM Community",
        model_name="PlaySEM Python Server",
        model_version="1.0.0",
    )

    logger.info("UPnP Server configured:")
    logger.info(f"  - Friendly Name: {server.friendly_name}")
    logger.info(f"  - Location URL: {server.location_url}")
    logger.info(f"  - UUID: {server.uuid}")

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
