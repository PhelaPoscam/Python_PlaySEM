"""
UPnP server for device discovery and service advertisement.
"""
import asyncio
import html
import json
import logging
import socket
import struct
import threading
from typing import Optional

from aiohttp import web

from ..effect_dispatcher import EffectDispatcher
from ..effect_metadata import EffectMetadata


logger = logging.getLogger(__name__)


class UPnPServer:
    """
    UPnP server for device discovery and service advertisement using SSDP.

    Provides automatic device discovery compatible with original PlaySEM
    clients. Advertises the PlaySEM service on the local network and
    responds to M-SEARCH discovery requests. This implementation also serves
    the required device and service description XML files over HTTP.
    """

    class _SSDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, server: "UPnPServer"):
            self.server = server
            self.transport = None

        def connection_made(self, transport):
            self.transport = transport
            self.server._transport = transport
            # Add socket to multicast group
            sock = self.transport.get_extra_info("socket")
            group = socket.inet_aton(self.server.SSDP_ADDR)
            mreq = struct.pack("4sL", group, socket.INADDR_ANY)
            try:
                sock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq
                )
            except OSError as e:
                # This can happen on some systems if the address is already in use
                logger.warning(f"Could not join multicast group: {e}")

        def datagram_received(self, data, addr):
            asyncio.create_task(self.server._handle_datagram(data, addr))

        def error_received(self, exc):
            logger.error(f"SSDP error: {exc}")

        def connection_lost(self, exc):
            logger.info("SSDP connection closed")
            if self.server:
                self.server._transport = None

    # UPnP/SSDP constants
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    UPNP_VERSION = "1.1"

    def __init__(
        self,
        friendly_name: str = "PlaySEM Server",
        dispatcher: Optional[EffectDispatcher] = None,
        uuid: Optional[str] = None,
        http_host: Optional[str] = None,
        http_port: int = 8080,
        manufacturer: str = "PlaySEM",
        model_name: str = "PlaySEM Python Server",
        model_version: str = "1.0",
    ):
        """
        Initialize UPnP server.

        Args:
            friendly_name: Human-readable device name
            dispatcher: EffectDispatcher instance for effect execution
            uuid: Device UUID (auto-generated if None)
            http_host: The host IP address to advertise for the XML server.
                       If None, it will be auto-detected.
            http_port: The port for the XML description server.
            manufacturer: Device manufacturer name
            model_name: Device model name
            model_version: Device model version
        """
        import uuid as uuid_module

        self.friendly_name = friendly_name
        self.dispatcher = dispatcher
        self.uuid = uuid or f"uuid:{uuid_module.uuid4()}"
        self.http_port = http_port

        if http_host:
            self.http_host = http_host
        else:
            self.http_host = self._get_local_ip()

        self.location_url = (
            f"http://{self.http_host}:{self.http_port}/description.xml"
        )

        self.manufacturer = manufacturer
        self.model_name = model_name
        self.model_version = model_version

        self.service_type = "urn:schemas-upnp-org:service:PlaySEM:1"
        self.device_type = "urn:schemas-upnp-org:device:PlaySEM:1"

        self._is_running = False
        self._transport = None
        self._advertisement_task = None
        self._http_runner = None
        self._http_site = None
        self._lock = threading.Lock()
        self._ready_event = asyncio.Event()

        logger.info(
            f"UPnP Server initialized - "
            f"device: {friendly_name}, uuid: {self.uuid}, "
            f"location: {self.location_url}"
        )

    async def wait_until_ready(self):
        """Wait until the UPnP server's HTTP component is ready."""
        await self._ready_event.wait()

    def _get_local_ip(self):
        """Attempt to get the local IP address of the machine."""
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't have to be reachable
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            if s:
                s.close()
        return ip

    async def _handle_description(self, request):
        """HTTP handler to serve the device description XML."""
        xml = self.get_device_description_xml()
        return web.Response(text=xml, content_type="application/xml")

    async def _handle_scpd(self, request):
        """HTTP handler to serve the Service Control Protocol Description XML."""
        xml = self._get_scpd_xml()
        return web.Response(text=xml, content_type="application/xml")

    async def _handle_control(self, request):
        """HTTP handler for the SOAP control endpoint."""
        import xml.etree.ElementTree as ET

        body = await request.text()
        logger.debug(f"Received UPnP SOAP request on /control:\n{body}")

        try:
            # Parse the SOAP envelope
            root = ET.fromstring(body)
            ns = {
                "s": "http://schemas.xmlsoap.org/soap/envelope/",
                "u": self.service_type,
            }

            # Find the action node
            action_node = root.find(".//u:SendEffect", ns)
            if action_node is None:
                raise ValueError("SendEffect action not found in SOAP request")

            # Extract arguments
            effect_type = action_node.findtext("EffectType")
            duration_str = action_node.findtext("Duration")
            intensity_str = action_node.findtext("Intensity")
            location = action_node.findtext("Location", default="")
            parameters_str = action_node.findtext("Parameters", default="{}")

            if not all([effect_type, duration_str, intensity_str]):
                raise ValueError(
                    "Missing required arguments in SendEffect action"
                )

            # Create EffectMetadata
            effect = EffectMetadata(
                effect_type=effect_type,
                duration=int(duration_str),
                intensity=int(intensity_str),
                location=location,
                parameters=json.loads(parameters_str),
            )

            # Dispatch the effect
            if self.dispatcher:
                self.dispatcher.dispatch_effect_metadata(effect)
                logger.info(
                    f"Dispatched effect '{effect.effect_type}' via UPnP"
                )
            else:
                logger.warning(
                    "No dispatcher configured for UPnP server. Effect not dispatched."
                )

            # Send success response
            response_xml = f"""<s:Envelope xmlns:s=\"http://schemas.xmlsoap.org/soap/envelope/\">
    <s:Body>
        <u:SendEffectResponse xmlns:u=\"{self.service_type}\">
        </u:SendEffectResponse>
    </s:Body>
</s:Envelope>"""
            return web.Response(
                text=response_xml,
                content_type="text/xml",
                charset="utf-8",
                status=200,
            )

        except ET.ParseError as e:
            logger.error(f"Error parsing SOAP request: {e}")
            fault_xml = self._get_soap_fault("600", "Invalid XML")
            return web.Response(
                text=fault_xml,
                content_type="text/xml",
                charset="utf-8",
                status=500,
            )
        except Exception as e:
            logger.error(f"Error processing UPnP control request: {e}")
            fault_xml = self._get_soap_fault("501", str(e))
            return web.Response(
                text=fault_xml,
                content_type="text/xml",
                charset="utf-8",
                status=500,
            )

    async def start(self):
        """
        Start the UPnP server.

        This starts both the SSDP multicast listener for discovery and the
        HTTP server for serving description files.
        """
        with self._lock:
            if self._is_running:
                logger.warning("UPnP Server already running")
                return

        try:
            loop = asyncio.get_running_loop()

            # 1. Start the SSDP datagram endpoint
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("", self.SSDP_PORT))
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: self._SSDPProtocol(self), sock=sock
            )

            # 2. Start the HTTP server for XML files
            app = web.Application()
            app.router.add_get("/description.xml", self._handle_description)
            app.router.add_get("/scpd.xml", self._handle_scpd)
            app.router.add_post("/control", self._handle_control)

            self._http_runner = web.AppRunner(app)
            await self._http_runner.setup()
            self._http_site = web.TCPSite(
                self._http_runner, self.http_host, self.http_port
            )
            await self._http_site.start()
            self._advertisement_task = asyncio.create_task(
                self._advertise_periodically()
            )

            with self._lock:
                self._is_running = True

            logger.info(
                f"UPnP SSDP discovery started on {self.SSDP_ADDR}:{self.SSDP_PORT}"
            )
            await self._send_notify_alive()
            self._ready_event.set()

        except Exception as e:
            logger.error(f"Failed to start UPnP Server: {e}")
            raise

    async def stop(self):
        """
        Stop the UPnP server.

        Sends byebye notifications and closes all sockets.
        """
        with self._lock:
            if not self._is_running:
                logger.warning("UPnP Server not running")
                return

        try:
            logger.info("Stopping UPnP Server...")

            # Stop SSDP
            if self._advertisement_task:
                self._advertisement_task.cancel()
                try:
                    await self._advertisement_task
                except asyncio.CancelledError:
                    pass

            await self._send_notify_byebye()
            if self._transport:
                self._transport.close()

            # Stop HTTP server
            if self._http_runner:
                await self._http_runner.cleanup()

            with self._lock:
                self._is_running = False
                self._transport = None
                self._http_runner = None
                self._http_site = None

            logger.info("UPnP Server stopped")

        except Exception as e:
            logger.error(f"Error stopping UPnP Server: {e}")
            raise

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    async def _handle_datagram(self, data: bytes, addr: tuple):
        """Handle incoming SSDP datagram."""
        try:
            message = data.decode("utf-8")
            if message.startswith("M-SEARCH"):
                logger.debug(f"Received M-SEARCH from {addr[0]}:{addr[1]}")
                st_line = [
                    line
                    for line in message.split("\r\n")
                    if line.upper().startswith("ST:")
                ]
                if not st_line:
                    return
                search_target = st_line[0].split(":", 1)[1].strip()

                if search_target in [
                    "ssdp:all",
                    "upnp:rootdevice",
                    self.device_type,
                    self.service_type,
                    self.uuid,
                ]:
                    await self._send_msearch_response(addr, search_target)
        except Exception as e:
            logger.error(f"Error handling SSDP datagram: {e}")

    async def _send_msearch_response(self, addr: tuple, search_target: str):
        """Send M-SEARCH response to a discovery request."""
        usn = (
            self.uuid
            if search_target == "upnp:rootdevice"
            else f"{self.uuid}::{search_target}"
        )
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"CACHE-CONTROL: max-age=1800\r\n"
            f"EXT:\r\n"
            f"LOCATION: {self.location_url}\r\n"
            f"SERVER: Python/{self.model_version} UPnP/{self.UPNP_VERSION} PlaySEM/{self.model_version}\r\n"
            f"ST: {search_target}\r\n"
            f"USN: {usn}\r\n"
            f"\r\n"
        )
        if self._transport:
            self._transport.sendto(response.encode("utf-8"), addr)
            logger.debug(
                f"Sent M-SEARCH response to {addr[0]}:{addr[1]} for {search_target}"
            )

    async def _send_notify_alive(self):
        """Send NOTIFY alive announcements."""
        targets = {
            "upnp:rootdevice": self.uuid,
            self.uuid: self.uuid,
            self.device_type: f"{self.uuid}::{self.device_type}",
            self.service_type: f"{self.uuid}::{self.service_type}",
        }
        for nt, usn in targets.items():
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"CACHE-CONTROL: max-age=1800\r\n"
                f"LOCATION: {self.location_url}\r\n"
                f"NT: {nt}\r\n"
                f"NTS: ssdp:alive\r\n"
                f"SERVER: Python/{self.model_version} UPnP/{self.UPNP_VERSION} PlaySEM/{self.model_version}\r\n"
                f"USN: {usn}\r\n"
                f"\r\n"
            )
            if self._transport:
                self._transport.sendto(
                    notify.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )
        logger.info("Sent NOTIFY alive announcements")

    async def _send_notify_byebye(self):
        """Send NOTIFY byebye announcements."""
        targets = {
            "upnp:rootdevice": self.uuid,
            self.uuid: self.uuid,
            self.device_type: f"{self.uuid}::{self.device_type}",
            self.service_type: f"{self.uuid}::{self.service_type}",
        }
        for nt, usn in targets.items():
            notify = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
                f"NT: {nt}\r\n"
                f"NTS: ssdp:byebye\r\n"
                f"USN: {usn}\r\n"
                f"\r\n"
            )
            if self._transport:
                self._transport.sendto(
                    notify.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )
        logger.info("Sent NOTIFY byebye announcements")

    async def _advertise_periodically(self):
        """Periodically send NOTIFY alive messages (every 15 minutes)."""
        try:
            while True:
                await asyncio.sleep(900)
                if self._is_running:
                    await self._send_notify_alive()
        except asyncio.CancelledError:
            pass

    def get_device_description_xml(self) -> str:
        """Generate UPnP device description XML."""
        # Using f-string for multiline string for clarity
        return f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>{self.device_type}</deviceType>
        <friendlyName>{html.escape(self.friendly_name)}</friendlyName>
        <manufacturer>{html.escape(self.manufacturer)}</manufacturer>
        <modelName>{html.escape(self.model_name)}</modelName>
        <UDN>{self.uuid}</UDN>
        <serviceList>
            <service>
                <serviceType>{self.service_type}</serviceType>
                <serviceId>urn:upnp-org:serviceId:PlaySEM1</serviceId>
                <SCPDURL>/scpd.xml</SCPDURL>
                <controlURL>/control</controlURL>
                <eventSubURL>/event</eventSubURL>
            </service>
        </serviceList>
    </device>
</root>"""

    def _get_scpd_xml(self) -> str:
        """Generates the Service Control Protocol Description (SCPD) XML."""
        return """<scpd xmlns="urn:schemas-upnp-org:service-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <actionList>
        <action>
            <name>SendEffect</name>
            <argumentList>
                <argument>
                    <name>EffectType</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_EffectType</relatedStateVariable>
                </argument>
                <argument>
                    <name>Duration</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Duration</relatedStateVariable>
                </argument>
                <argument>
                    <name>Intensity</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Intensity</relatedStateVariable>
                </argument>
                <argument>
                    <name>Location</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Location</relatedStateVariable>
                </argument>
                <argument>
                    <name>Parameters</name>
                    <direction>in</direction>
                    <relatedStateVariable>A_ARG_TYPE_Parameters</relatedStateVariable>
                </argument>
            </argumentList>
        </action>
    </actionList>
    <serviceStateTable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_EffectType</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Duration</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Intensity</name>
            <dataType>ui4</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Location</name>
            <dataType>string</dataType>
        </stateVariable>
        <stateVariable sendEvents="no">
            <name>A_ARG_TYPE_Parameters</name>
            <dataType>string</dataType>
        </stateVariable>
    </serviceStateTable>
</scpd>"""
    def _get_soap_fault(self, fault_code: str, fault_string: str) -> str:
        """Generates a UPnP SOAP Fault message."""
        return f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <s:Fault>
            <faultcode>s:Client</faultcode>
            <faultstring>UPnPError</faultstring>
            <detail>
                <UPnPError xmlns="urn:schemas-upnp-org:control-1-0">
                    <errorCode>{fault_code}</errorCode>
                    <errorDescription>{fault_string}</errorDescription>
                </UPnPError>
            </detail>
        </s:Fault>
    </s:Body>
</s:Envelope>"""
