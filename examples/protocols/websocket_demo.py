#!/usr/bin/env python3
"""
WebSocket Server demo - demonstrates real-time bidirectional effect
communication.

This example starts the PlaySEM WebSocket server, connects a local client,
and exchanges valid effect messages over the socket.
"""

import asyncio
import json
import logging
import socket
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from playsem import DeviceManager, EffectDispatcher
from playsem.drivers import MockConnectivityDriver
from playsem.protocol_servers import WebSocketServer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


class RecordingConnectivityDriver(MockConnectivityDriver):
    def __init__(self):
        super().__init__(interface_name="recording_mock")
        self.commands = []

    def send_command(self, device_id, command, params=None):
        payload = params or {}
        self.commands.append(
            {"device_id": device_id, "command": command, "params": payload}
        )
        return super().send_command(device_id, command, params)


def get_local_ip():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        if s:
            s.close()


def build_dispatcher():
    driver = RecordingConnectivityDriver()
    device_manager = DeviceManager(connectivity_driver=driver)
    device_manager.connect()
    return EffectDispatcher(device_manager), driver


async def main():
    print("\n" + "=" * 60)
    print("PlaySEM WebSocket Server Demo")
    print("=" * 60)

    dispatcher, driver = build_dispatcher()
    host_ip = get_local_ip()
    ws_port = 8765
    ws_url = f"ws://127.0.0.1:{ws_port}"

    received_effects = []
    connected_clients = []
    disconnected_clients = []

    def on_effect_received(effect):
        received_effects.append(effect)
        logger.info(
            "Effect received: %s (%s ms, intensity=%s)",
            effect.effect_type,
            effect.duration,
            effect.intensity,
        )

    def on_client_connected(client_id):
        connected_clients.append(client_id)
        logger.info("Client connected: %s", client_id)

    def on_client_disconnected(client_id):
        disconnected_clients.append(client_id)
        logger.info("Client disconnected: %s", client_id)

    server = WebSocketServer(
        host="127.0.0.1",
        port=ws_port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
        on_client_connected=on_client_connected,
        on_client_disconnected=on_client_disconnected,
    )

    print("\nWebSocket server configuration")
    print(f"  server: {ws_url}")
    print(f"  host address: {host_ip}")

    print("\nStarting embedded WebSocket server...")
    server_task = asyncio.create_task(server.start())

    try:
        import websockets
    except ImportError:
        print("websockets is required for this demo")
        server_task.cancel()
        return 1

    websocket = None
    for _ in range(40):
        try:
            websocket = await websockets.connect(ws_url)
            break
        except OSError:
            await asyncio.sleep(0.25)

    if websocket is None:
        print("WebSocket server failed to become ready within 10 seconds")
        await server.stop()
        await asyncio.sleep(0.2)
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        return 1

    try:
        welcome = await websocket.recv()
        print("Welcome message:")
        print(welcome)

        effects = [
            {"effect_type": "light", "intensity": 70, "duration": 1000},
            {"effect_type": "vibration", "intensity": 90, "duration": 500},
            {"effect_type": "wind", "intensity": 60, "duration": 750},
        ]

        print("\nSending sample WebSocket effects")
        print("=" * 60)
        for index, effect in enumerate(effects, start=1):
            message = json.dumps({"type": "effect", **effect})
            await websocket.send(message)
            response = await websocket.recv()
            print(f"{index}. sent {effect['effect_type']} -> {response}")
            await asyncio.sleep(0.25)
    finally:
        await websocket.close()

    print("\nReceived effects")
    print("=" * 60)
    if received_effects:
        for index, effect in enumerate(received_effects, start=1):
            print(
                f"{index}. {effect.effect_type} - "
                f"intensity={effect.intensity}, duration={effect.duration}ms"
            )
    else:
        print("No callbacks were captured during the demo run.")

    if connected_clients:
        print("\nConnected clients")
        for client_id in connected_clients:
            print(f"  {client_id}")

    if disconnected_clients:
        print("\nDisconnected clients")
        for client_id in disconnected_clients:
            print(f"  {client_id}")

    print("\nDriver commands")
    print("=" * 60)
    if driver.commands:
        for index, command in enumerate(driver.commands, start=1):
            print(
                f"{index}. {command['device_id']} -> {command['command']} "
                f"{command['params']}"
            )
    else:
        print("No driver commands were captured during the demo run.")

    print("\nStopping WebSocket server...")
    await server.stop()
    await asyncio.sleep(0.2)
    try:
        await server_task
    except asyncio.CancelledError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
