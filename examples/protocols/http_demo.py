#!/usr/bin/env python3
"""
HTTP Protocol Demo - demonstrates the embedded HTTP REST server.

This example starts the PlaySEM HTTP server, waits for it to become ready,
and sends a few valid effect payloads through the REST API.
"""

import asyncio
import json
import logging
import socket
import urllib.error
import urllib.request

from playsem import DeviceManager, EffectDispatcher
from playsem.drivers import MockConnectivityDriver
from playsem.protocol_servers import HTTPServer


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


def send_http_request(url, effect):
    payload = json.dumps(effect).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def http_status_ready(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


async def wait_for_http_ready(url, timeout=15.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(http_status_ready, url):
            return True
        await asyncio.sleep(0.25)
    return False


async def main():
    print("\n" + "=" * 60)
    print("PlaySEM HTTP Protocol Demo")
    print("=" * 60)

    dispatcher, driver = build_dispatcher()
    received_effects = []

    def on_effect_received(effect):
        received_effects.append(effect)
        logger.info(
            "Effect received: %s (%s ms, intensity=%s)",
            effect.effect_type,
            effect.duration,
            effect.intensity,
        )

    http_port = 8080
    http_server = HTTPServer(
        host="127.0.0.1",
        port=http_port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
    )

    host_ip = get_local_ip()
    print("\nHTTP server configuration")
    print(f"  server: http://{host_ip}:{http_port}")
    print(f"  api: http://{host_ip}:{http_port}/api/effects")
    print(f"  docs: http://{host_ip}:{http_port}/docs")

    print("\nStarting embedded HTTP server...")
    server_task = asyncio.create_task(http_server.start())
    ready = await wait_for_http_ready(
        f"http://127.0.0.1:{http_port}/api/status"
    )
    if not ready:
        print("HTTP server failed to become ready within 15 seconds")
        server_task.cancel()
        return 1

    effects = [
        {"effect_type": "vibration", "intensity": 80, "duration": 500},
        {"effect_type": "light", "intensity": 70, "duration": 1000},
        {"effect_type": "wind", "intensity": 60, "duration": 800},
    ]

    print("\nSending sample HTTP effects")
    print("=" * 60)
    for index, effect in enumerate(effects, start=1):
        result = await asyncio.to_thread(
            send_http_request,
            f"http://127.0.0.1:{http_port}/api/effects",
            effect,
        )
        print(f"{index}. {effect['effect_type']} -> {result}")
        await asyncio.sleep(0.25)

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

    print("\nStopping HTTP server...")
    await http_server.stop()
    await asyncio.sleep(0.2)
    try:
        await server_task
    except asyncio.CancelledError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
