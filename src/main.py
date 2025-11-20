# src/main.py
import asyncio
import logging
from pathlib import Path

from .config_loader import load_protocols_yaml
from .device_manager import DeviceManager
from .effect_dispatcher import EffectDispatcher
from .protocol_server import (
    HTTPServer,
    WebSocketServer,
    MQTTServer,
    CoAPServer,
    UPnPServer,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the PythonPlaySEM application.
    """
    # Load protocol configurations
    protocols_config_path = (
        Path(__file__).parent.parent / "config" / "protocols.yaml"
    )
    protocols_config = load_protocols_yaml(str(protocols_config_path))

    # Create core components
    dm_config = protocols_config.get("device_manager", {})
    device_manager = DeviceManager(
        broker_address=dm_config.get("broker_address")
    )
    effect_dispatcher = EffectDispatcher(device_manager)

    tasks = []
    servers = []

    # Conditionally start servers based on configuration
    if protocols_config.get("http_server", {}).get("enabled"):
        http_config = protocols_config["http_server"]
        http_server = HTTPServer(
            host=http_config["host"],
            port=http_config["port"],
            api_key=http_config.get("api_key"),
            cors_origins=http_config.get("cors_origins"),
            dispatcher=effect_dispatcher,
        )
        tasks.append(http_server.start())
        servers.append(http_server)
        logger.info("HTTP Server is enabled.")

    if protocols_config.get("websocket_server", {}).get("enabled"):
        ws_config = protocols_config["websocket_server"]
        ws_server = WebSocketServer(
            host=ws_config["host"],
            port=ws_config["port"],
            auth_token=ws_config.get("auth_token"),
            use_ssl=ws_config.get("use_ssl", False),
            ssl_certfile=ws_config.get("ssl_certfile"),
            ssl_keyfile=ws_config.get("ssl_keyfile"),
            dispatcher=effect_dispatcher,
        )
        tasks.append(ws_server.start())
        servers.append(ws_server)
        logger.info("WebSocket Server is enabled.")

    if protocols_config.get("mqtt_server", {}).get("enabled"):
        mqtt_config = protocols_config["mqtt_server"]
        # Note: The current MQTTServer is a broker and runs in a separate thread.
        # It's not fully async and might not integrate perfectly with this model.
        # For now, we start it and assume it runs in the background.
        mqtt_server = MQTTServer(
            host=mqtt_config.get("broker_address", "localhost"),
            port=mqtt_config.get("port", 1883),
            dispatcher=effect_dispatcher,
        )
        mqtt_server.start()  # This is a blocking call in a thread
        servers.append(mqtt_server)
        logger.info("MQTT Server is enabled.")

    if protocols_config.get("coap_server", {}).get("enabled"):
        coap_config = protocols_config["coap_server"]
        coap_server = CoAPServer(
            host=coap_config["host"],
            port=coap_config["port"],
            dispatcher=effect_dispatcher,
        )
        tasks.append(coap_server.start())
        servers.append(coap_server)
        logger.info("CoAP Server is enabled.")

    if protocols_config.get("upnp_server", {}).get("enabled"):
        upnp_config = protocols_config["upnp_server"]
        upnp_server = UPnPServer(
            friendly_name=upnp_config.get(
                "friendly_name", "PlaySEM Python Server"
            ),
            http_port=upnp_config.get("http_port", 8080),
            dispatcher=effect_dispatcher,
        )
        tasks.append(upnp_server.start())
        servers.append(upnp_server)
        logger.info("UPnP Server is enabled.")

    if not tasks:
        logger.warning("No protocol servers are enabled. Exiting.")
        return

    logger.info("All enabled servers are starting...")

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        # Gracefully stop all servers
        stop_tasks = []
        for server in servers:
            # The MQTT server has a different stop method
            if isinstance(server, MQTTServer):
                server.stop()
            else:
                stop_tasks.append(server.stop())

        if stop_tasks:
            await asyncio.gather(*stop_tasks)

        logger.info("All servers have been shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user.")
