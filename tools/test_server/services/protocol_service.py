"""
Protocol Service - Protocol server lifecycle management.

Handles:
- Starting protocol servers (MQTT, CoAP, HTTP, UPnP)
- Stopping protocol servers
- Server status tracking
- Error handling and recovery
"""

import asyncio
from typing import Dict, Optional

from fastapi import WebSocket


class ProtocolService:
    """Service for managing protocol servers."""

    def __init__(self):
        """Initialize protocol service."""
        self.servers = {}  # protocol_name -> server instance
        self.server_tasks = {}  # protocol_name -> asyncio task
        self.server_status = {}  # protocol_name -> status info
        self.stats = {
            "servers_started": 0,
            "servers_stopped": 0,
            "errors": 0,
        }

    async def start_protocol_server(
        self,
        websocket: WebSocket,
        protocol: str,
        port: int,
        host: str = "127.0.0.1",
        **kwargs,
    ) -> None:
        """Start a protocol server.

        Args:
            websocket: WebSocket connection for status
            protocol: Protocol name ('mqtt', 'coap', 'http', 'upnp')
            port: Server port
            host: Server host address
            **kwargs: Additional protocol-specific arguments
        """
        try:
            if protocol in self.servers and self.servers[protocol]:
                raise ValueError(f"{protocol.upper()} server already running")

            print(
                f"[*] Starting {protocol.upper()} server on {host}:{port}..."
            )

            if protocol == "mqtt":
                server = await self._start_mqtt_server(host, port, **kwargs)
            elif protocol == "coap":
                server = await self._start_coap_server(host, port, **kwargs)
            elif protocol == "http":
                server = await self._start_http_server(host, port, **kwargs)
            elif protocol == "upnp":
                server = await self._start_upnp_server(host, port, **kwargs)
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")

            self.servers[protocol] = server
            self.server_status[protocol] = {
                "state": "running",
                "host": host,
                "port": port,
                "started_at": asyncio.get_event_loop().time(),
            }

            self.stats["servers_started"] += 1

            print(f"[OK] {protocol.upper()} server started on {host}:{port}")

            await websocket.send_json(
                {
                    "type": "protocol_started",
                    "protocol": protocol,
                    "host": host,
                    "port": port,
                }
            )

        except Exception as e:
            print(f"[x] {protocol.upper()} start error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "protocol_error",
                    "protocol": protocol,
                    "error": str(e),
                }
            )

    async def _start_mqtt_server(
        self, host: str, port: int, **kwargs
    ) -> object:
        """Start MQTT server.

        Args:
            host: Server host
            port: Server port
            **kwargs: Additional arguments

        Returns:
            MQTT server instance
        """
        try:
            from playsem.mqtt_driver import MQTTServer

            server = MQTTServer(
                host=host,
                port=port,
                broker_id="playsem-server",
                **kwargs,
            )

            await server.start()
            return server

        except ImportError:
            raise Exception("MQTT dependencies not installed")

    async def _start_coap_server(
        self, host: str, port: int, **kwargs
    ) -> object:
        """Start CoAP server.

        Args:
            host: Server host
            port: Server port
            **kwargs: Additional arguments

        Returns:
            CoAP server instance
        """
        try:
            from playsem.coap_driver import CoAPServer

            server = CoAPServer(
                host=host,
                port=port,
                **kwargs,
            )

            await server.start()
            return server

        except ImportError:
            raise Exception("CoAP dependencies not installed")

    async def _start_http_server(
        self, host: str, port: int, **kwargs
    ) -> object:
        """Start HTTP server.

        Args:
            host: Server host
            port: Server port
            **kwargs: Additional arguments

        Returns:
            HTTP server instance
        """
        try:
            from playsem.http_driver import HTTPServer

            server = HTTPServer(
                host=host,
                port=port,
                **kwargs,
            )

            await server.start()
            return server

        except ImportError:
            raise Exception("HTTP dependencies not installed")

    async def _start_upnp_server(
        self, host: str, port: int, **kwargs
    ) -> object:
        """Start UPnP server.

        Args:
            host: Server host
            port: Server port
            **kwargs: Additional arguments

        Returns:
            UPnP server instance
        """
        try:
            from playsem.upnp_driver import UPnPServer

            server = UPnPServer(
                host=host,
                port=port,
                **kwargs,
            )

            await server.start()
            return server

        except ImportError:
            raise Exception("UPnP dependencies not installed")

    async def stop_protocol_server(
        self,
        websocket: WebSocket,
        protocol: str,
    ) -> None:
        """Stop a protocol server.

        Args:
            websocket: WebSocket connection for status
            protocol: Protocol name
        """
        try:
            if protocol not in self.servers or not self.servers[protocol]:
                raise ValueError(f"{protocol.upper()} server not running")

            print(f"[*] Stopping {protocol.upper()} server...")

            server = self.servers[protocol]

            # Stop server
            if hasattr(server, "stop"):
                await server.stop()
            elif hasattr(server, "shutdown"):
                await server.shutdown()

            self.servers[protocol] = None
            self.server_status[protocol]["state"] = "stopped"
            self.stats["servers_stopped"] += 1

            print(f"[OK] {protocol.upper()} server stopped")

            await websocket.send_json(
                {
                    "type": "protocol_stopped",
                    "protocol": protocol,
                }
            )

        except Exception as e:
            print(f"[x] {protocol.upper()} stop error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "protocol_error",
                    "protocol": protocol,
                    "error": str(e),
                }
            )

    async def get_protocol_status(
        self,
        websocket: WebSocket,
        protocol: str = None,
    ) -> None:
        """Get protocol server status.

        Args:
            websocket: WebSocket connection
            protocol: Protocol name (None for all)
        """
        try:
            if protocol:
                if protocol not in self.server_status:
                    status = {"state": "not_running"}
                else:
                    status = self.server_status[protocol]

                await websocket.send_json(
                    {
                        "type": "protocol_status",
                        "protocol": protocol,
                        "status": status,
                    }
                )
            else:
                # Get status of all protocols
                statuses = {}
                for p in ["mqtt", "coap", "http", "upnp"]:
                    if p in self.server_status:
                        statuses[p] = self.server_status[p]
                    else:
                        statuses[p] = {"state": "not_running"}

                await websocket.send_json(
                    {
                        "type": "protocol_status_all",
                        "protocols": statuses,
                    }
                )

        except Exception as e:
            print(f"[x] Status error: {e}")
            await websocket.send_json(
                {
                    "type": "protocol_error",
                    "error": str(e),
                }
            )

    def get_server(self, protocol: str) -> Optional[object]:
        """Get protocol server instance.

        Args:
            protocol: Protocol name

        Returns:
            Server instance or None
        """
        return self.servers.get(protocol)

    def is_running(self, protocol: str) -> bool:
        """Check if protocol server is running.

        Args:
            protocol: Protocol name

        Returns:
            True if running
        """
        status = self.server_status.get(protocol, {})
        return status.get("state") == "running"

    async def stop_all(self) -> None:
        """Stop all protocol servers."""
        protocols = list(self.servers.keys())
        for protocol in protocols:
            if self.servers.get(protocol):
                try:
                    server = self.servers[protocol]
                    if hasattr(server, "stop"):
                        await server.stop()
                    elif hasattr(server, "shutdown"):
                        await server.shutdown()
                except Exception as e:
                    print(f"[ERROR] Failed to stop {protocol}: {e}")
                finally:
                    self.servers[protocol] = None
                    self.server_status[protocol]["state"] = "stopped"

        print("[OK] All protocol servers stopped")

    def get_all_statuses(self) -> dict:
        """Get status of all protocol servers.

        Returns:
            Dictionary mapping protocol names to status
        """
        statuses = {}
        for protocol in ["mqtt", "coap", "http", "upnp"]:
            if protocol in self.server_status:
                statuses[protocol] = self.server_status[protocol]
            else:
                statuses[protocol] = {"state": "not_running"}
        return statuses
