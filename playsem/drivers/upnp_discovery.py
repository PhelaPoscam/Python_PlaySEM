import socket
import asyncio
import logging
from typing import List, Dict, Any
from playsem.drivers.base_driver import BaseDiscovery

logger = logging.getLogger(__name__)

class UPnPDiscovery(BaseDiscovery):
    """UPnP discovery scanner using SSDP M-SEARCH."""

    def get_interface_name(self) -> str:
        return "upnp"

    async def discover_devices(self) -> List[Dict[str, Any]]:
        """Scan for UPnP devices using SSDP multicast."""
        devices = []
        ssdp_addr = "239.255.255.250"
        ssdp_port = 1900
        
        m_search = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {ssdp_addr}:{ssdp_port}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 2\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        )
        
        try:
            def _scan():
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.settimeout(2.0)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                
                try:
                    sock.sendto(m_search.encode("utf-8"), (ssdp_addr, ssdp_port))
                    discovered_ips = set()
                    
                    while True:
                        try:
                            data, addr = sock.recvfrom(1024)
                            ip = addr[0]
                            if ip not in discovered_ips:
                                discovered_ips.add(ip)
                                headers = data.decode("utf-8", errors="ignore").split("\r\n")
                                location = ""
                                server_name = "UPnP Device"
                                for header in headers:
                                    if header.lower().startswith("location:"):
                                        location = header.split(":", 1)[1].strip()
                                    elif header.lower().startswith("server:"):
                                        server_name = header.split(":", 1)[1].strip()
                                        
                                devices.append({
                                    "id": f"upnp_{ip.replace('.', '_')}",
                                    "name": server_name,
                                    "type": "upnp_device",
                                    "address": location or ip,
                                    "protocols": ["upnp"],
                                    "metadata": {
                                        "ip": ip,
                                        "location": location,
                                        "raw_headers": headers,
                                    }
                                })
                        except socket.timeout:
                            break
                finally:
                    sock.close()
                return devices

            return await asyncio.to_thread(_scan)
        except Exception as e:
            logger.error(f"UPnP SSDP M-SEARCH scan failed: {e}")
            return devices
