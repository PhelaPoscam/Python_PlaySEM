"""
UPnP Client for discovering PlaySEM servers.

This script discovers PlaySEM UPnP servers on the local network using SSDP.
It sends M-SEARCH requests and listens for responses from PlaySEM devices.

Usage:
    python examples/test_upnp_client.py

This will scan the network for PlaySEM servers and display their details.
"""

import asyncio
import socket
import struct
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class UPnPClient:
    """Simple UPnP/SSDP client for discovering devices."""

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 3  # Max wait time

    def __init__(self, search_target="ssdp:all"):
        """
        Initialize UPnP client.

        Args:
            search_target: SSDP search target (e.g., "ssdp:all",
                          "urn:schemas-upnp-org:device:PlaySEM:1")
        """
        self.search_target = search_target
        self.discovered_devices = []

    async def discover(self, timeout=5):
        """
        Discover UPnP devices on the network.

        Args:
            timeout: Discovery timeout in seconds

        Returns:
            List of discovered device information dictionaries
        """
        logger.info(f"Starting UPnP discovery (timeout: {timeout}s)...")
        logger.info(f"Search target: {self.search_target}")

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # Prepare M-SEARCH message
        msearch = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
            f'MAN: "ssdp:discover"\r\n'
            f"MX: {self.SSDP_MX}\r\n"
            f"ST: {self.search_target}\r\n"
            "\r\n"
        )

        try:
            # Send M-SEARCH request
            sock.sendto(
                msearch.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
            )
            logger.info("M-SEARCH request sent")

            # Listen for responses
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    data, addr = sock.recvfrom(2048)
                    response = data.decode("utf-8")

                    # Parse response
                    device_info = self._parse_response(response, addr)
                    if device_info:
                        self.discovered_devices.append(device_info)
                        logger.info(f"✅ Discovered device at {addr[0]}")

                except socket.timeout:
                    break
                except Exception as e:
                    logger.error(f"Error receiving response: {e}")

        except Exception as e:
            logger.error(f"Discovery error: {e}")
        finally:
            sock.close()

        logger.info(
            f"Discovery complete. Found {len(self.discovered_devices)} "
            f"device(s)"
        )
        return self.discovered_devices

    def _parse_response(self, response: str, addr: tuple):
        """Parse SSDP M-SEARCH response."""
        try:
            lines = response.split("\r\n")

            # Check if it's a valid response
            if not lines[0].startswith("HTTP/1.1 200"):
                return None

            info = {
                "address": addr[0],
                "port": addr[1],
            }

            # Parse headers
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().upper()
                    value = value.strip()

                    if key == "LOCATION":
                        info["location"] = value
                    elif key == "SERVER":
                        info["server"] = value
                    elif key == "ST":
                        info["search_target"] = value
                    elif key == "USN":
                        info["usn"] = value
                    elif key == "CACHE-CONTROL":
                        info["cache_control"] = value

            return info

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

    def print_devices(self):
        """Print discovered devices in a formatted way."""
        if not self.discovered_devices:
            print("\n❌ No devices discovered")
            return

        print("\n" + "=" * 70)
        print(f"📡 Discovered {len(self.discovered_devices)} UPnP Device(s)")
        print("=" * 70)

        for idx, device in enumerate(self.discovered_devices, 1):
            print(f"\n🔹 Device {idx}:")
            print(f"   Address:       {device.get('address', 'N/A')}")
            print(f"   Location:      {device.get('location', 'N/A')}")
            print(f"   Server:        {device.get('server', 'N/A')}")
            print(f"   USN:           {device.get('usn', 'N/A')}")
            print(f"   Search Target: {device.get('search_target', 'N/A')}")
            print(f"   Cache Control: {device.get('cache_control', 'N/A')}")

        print("\n" + "=" * 70)


async def main():
    """Run the UPnP discovery client."""
    logger.info("=" * 60)
    logger.info("PlaySEM UPnP Discovery Client")
    logger.info("=" * 60)

    # Discover PlaySEM devices specifically
    logger.info("\n🔍 Searching for PlaySEM devices...")
    playsem_client = UPnPClient(
        search_target="urn:schemas-upnp-org:device:PlaySEM:1"
    )
    await playsem_client.discover(timeout=5)
    playsem_client.print_devices()

    # Also search for all UPnP devices
    logger.info("\n🔍 Searching for all UPnP devices...")
    all_client = UPnPClient(search_target="ssdp:all")
    await all_client.discover(timeout=5)
    all_client.print_devices()

    logger.info("\n✅ Discovery complete!")
    logger.info(
        "\nTip: Make sure upnp_server_demo.py is running to discover "
        "PlaySEM servers"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Discovery cancelled by user")
