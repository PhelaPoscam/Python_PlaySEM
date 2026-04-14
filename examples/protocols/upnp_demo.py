#!/usr/bin/env python3
"""
UPnP Protocol Demo - demonstrates the embedded UPnP server.

This example starts the PlaySEM UPnP server, fetches the generated device
description, and sends a local SOAP control request to the /control endpoint.
"""

import asyncio
import json
import logging
import socket
import sys
import urllib.request
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from playsem import DeviceManager, EffectDispatcher
from playsem.drivers import MockConnectivityDriver
from playsem.protocol_servers import UPnPServer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


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


def fetch_text(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def send_soap_request(host, port, effect):
    envelope = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SendEffect xmlns:u="urn:schemas-upnp-org:service:PlaySEM:1">
      <EffectType>{effect['effect_type']}</EffectType>
      <Duration>{effect['duration']}</Duration>
      <Intensity>{effect['intensity']}</Intensity>
      <Location>everywhere</Location>
      <Parameters>{json.dumps(effect.get('parameters', {}))}</Parameters>
    </u:SendEffect>
  </s:Body>
</s:Envelope>"""

    request = urllib.request.Request(
        f"http://{host}:{port}/control",
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": '"urn:schemas-upnp-org:service:PlaySEM:1#SendEffect"',
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


async def main():
    print("\n" + "=" * 60)
    print("PlaySEM UPnP Protocol Demo")
    print("=" * 60)

    driver = RecordingConnectivityDriver()
    device_manager = DeviceManager(connectivity_driver=driver)
    device_manager.connect()
    dispatcher = EffectDispatcher(device_manager)
    upnp_http_port = 8088
    upnp_server = UPnPServer(
        friendly_name="PlaySEM Demo Server",
        dispatcher=dispatcher,
        http_port=upnp_http_port,
    )

    print("\nUPnP server configuration")
    print(
        f"  description: http://{upnp_server.http_host}:{upnp_http_port}/description.xml"
    )
    print(
        f"  control: http://{upnp_server.http_host}:{upnp_http_port}/control"
    )
    print(f"  local address: {get_local_ip()}")

    print("\nStarting embedded UPnP server...")
    await upnp_server.start()
    await asyncio.wait_for(upnp_server.wait_until_ready(), timeout=10.0)

    description_url = (
        f"http://{upnp_server.http_host}:{upnp_http_port}/description.xml"
    )
    description_xml = await asyncio.to_thread(fetch_text, description_url)
    print("\nDevice description preview")
    print("=" * 60)
    for line in description_xml.splitlines()[:10]:
        print(line)

    effects = [
        {"effect_type": "light", "intensity": 70, "duration": 1000},
        {"effect_type": "vibration", "intensity": 90, "duration": 500},
    ]

    print("\nSending sample UPnP control requests")
    print("=" * 60)
    for index, effect in enumerate(effects, start=1):
        status, body = await asyncio.to_thread(
            send_soap_request, upnp_server.http_host, upnp_http_port, effect
        )
        print(f"{index}. {effect['effect_type']} -> status={status}")
        print(body.strip())

    print("\nReceived effects")
    print("=" * 60)
    if driver.commands:
        for index, command in enumerate(driver.commands, start=1):
            print(
                f"{index}. {command['device_id']} -> {command['command']} "
                f"{command['params']}"
            )
    else:
        print("No driver commands were captured during the demo run.")

    print("\nStopping UPnP server...")
    await upnp_server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
