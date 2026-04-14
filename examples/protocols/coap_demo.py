#!/usr/bin/env python3
"""
CoAP Protocol Demo - demonstrates the embedded CoAP server.

This example starts the PlaySEM CoAP server, sends a few sample requests to
its /effects endpoint, and shows the effect dispatch path through the
embedded server, dispatcher, DeviceManager, and driver.
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
from playsem.protocol_servers import CoAPServer


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


async def send_coap_request(host, port, effect):
    try:
        from aiocoap import Code, Context, Message
    except ImportError:
        logger.error("aiocoap is required for this demo")
        return {"success": False, "error": "aiocoap is not installed"}

    ctx = await Context.create_client_context()
    try:
        payload = json.dumps(effect).encode("utf-8")
        uri = f"coap://{host}:{port}/effects"
        request = Message(code=Code.POST, uri=uri, payload=payload)
        response = await ctx.request(request).response
        response_text = (
            response.payload.decode("utf-8") if response.payload else ""
        )
        return json.loads(response_text) if response_text else {}
    except Exception as exc:
        logger.error("CoAP request failed: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        await ctx.shutdown()


async def main():
    print("\n" + "=" * 60)
    print("PlaySEM CoAP Protocol Demo")
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

    coap_port = 5683
    coap_server = CoAPServer(
        host="127.0.0.1",
        port=coap_port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
    )

    print("\nCoAP server configuration")
    print(f"  server: coap://127.0.0.1:{coap_port}")
    print("  endpoint: /effects")
    print(f"  local address: {get_local_ip()}")

    print("\nStarting embedded CoAP server...")
    await coap_server.start()

    effects = [
        {"effect_type": "vibration", "intensity": 80, "duration": 500},
        {"effect_type": "light", "intensity": 70, "duration": 1000},
        {"effect_type": "wind", "intensity": 60, "duration": 800},
    ]

    print("\nSending sample CoAP effects")
    print("=" * 60)
    for index, effect in enumerate(effects, start=1):
        result = await send_coap_request("127.0.0.1", coap_port, effect)
        print(f"{index}. {effect['effect_type']} -> {result}")
        await asyncio.sleep(0.5)

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

    print("\nStopping CoAP server...")
    await coap_server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
