#!/usr/bin/env python3
"""
Unified Protocol Server - WebSocket, MQTT, and CoAP simultaneously.

This demo starts all three protocol servers at once, allowing the
control panel to connect and send effects via any protocol.

Run:
  python examples/unified_server_demo.py
"""

import sys
import asyncio
import logging
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_manager import DeviceManager  # noqa: E402
from src.effect_dispatcher import EffectDispatcher  # noqa: E402
from src.protocol_server import (  # noqa: E402
    WebSocketServer,
    MQTTServer,
    CoAPServer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class UnifiedServer:
    """Runs all protocol servers simultaneously."""

    def __init__(self):
        # DeviceManager can work without an MQTT client
        self.device_manager = DeviceManager(client=None)
        self.dispatcher = EffectDispatcher(self.device_manager)

        # Create protocol servers
        self.websocket_server = WebSocketServer(
            host="localhost",
            port=8765,
            dispatcher=self.dispatcher,
            on_effect_received=self.on_effect_received,
        )

        self.mqtt_server = MQTTServer(
            broker_address="localhost",
            port=1883,
            dispatcher=self.dispatcher,
            subscribe_topic="effects/#",
            on_effect_received=self.on_effect_received,
        )

        self.coap_server = CoAPServer(
            host="localhost",
            port=5683,
            dispatcher=self.dispatcher,
            on_effect_received=self.on_effect_received,
        )

        self.running = False
        self.mqtt_available = False

    def on_effect_received(self, effect):
        """Callback when any protocol receives an effect."""
        logger.info(
            "✓ Received effect: %s (intensity=%s, duration=%sms)",
            effect.effect_type,
            effect.intensity,
            effect.duration,
        )

    async def start(self):
        """Start all servers."""
        self.running = True

        print("\n" + "=" * 70)
        print("PythonPlaySEM Unified Protocol Server")
        print("=" * 70)
        print("\nStarting servers...\n")

        tasks = []

        # Start WebSocket server (always available)
        logger.info("Starting WebSocket server on ws://localhost:8765")
        ws_task = asyncio.create_task(self.websocket_server.start())
        tasks.append(ws_task)
        await asyncio.sleep(0.5)  # Give it time to bind

        # Start MQTT server (optional - requires broker)
        try:
            logger.info("Starting MQTT server (broker: localhost:1883)")
            mqtt_task = asyncio.create_task(
                asyncio.to_thread(self.mqtt_server.start)
            )
            tasks.append(mqtt_task)
            await asyncio.sleep(0.5)
            self.mqtt_available = True
        except Exception as e:
            logger.warning(
                f"MQTT server not started: {e}"
                "\n  → Mosquitto broker not available (optional)"
            )

        # Start CoAP server (always available)
        logger.info("Starting CoAP server on coap://localhost:5683")
        coap_task = asyncio.create_task(self.coap_server.start())
        tasks.append(coap_task)
        await asyncio.sleep(0.5)

        print("\n" + "=" * 70)
        print("Servers Running:")
        print("=" * 70)
        print("✅ WebSocket: ws://localhost:8765")
        print(
            f"{'✅' if self.mqtt_available else '⚠️ '} MQTT:      "
            f"localhost:1883 (topics: effects/#)"
        )
        print("✅ CoAP:      coap://localhost:5683/effects")
        print("\nControl Panel:")
        print("  → Open: examples/control_panel.html")
        print("\nPress Ctrl+C to stop all servers")
        print("=" * 70 + "\n")

        # Wait for all servers
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Stop all servers."""
        if not self.running:
            return

        print("\n\nStopping servers...")
        self.running = False

        # Stop servers
        try:
            await self.websocket_server.stop()
            logger.info("WebSocket server stopped")
        except Exception as e:
            logger.error(f"Error stopping WebSocket: {e}")

        try:
            if self.mqtt_available:
                await asyncio.to_thread(self.mqtt_server.stop)
                logger.info("MQTT server stopped")
        except Exception as e:
            logger.error(f"Error stopping MQTT: {e}")

        try:
            await self.coap_server.stop()
            logger.info("CoAP server stopped")
        except Exception as e:
            logger.error(f"Error stopping CoAP: {e}")

        print("All servers stopped.\n")


async def main():
    """Main entry point."""
    server = UnifiedServer()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
