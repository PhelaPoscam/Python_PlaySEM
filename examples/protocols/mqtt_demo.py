#!/usr/bin/env python3
"""
MQTT Protocol Demo - demonstrates the embedded MQTT broker.

This example starts the PlaySEM MQTT broker, publishes a few effects from
an external client, and shows the effects being dispatched through the
embedded server -> dispatcher -> DeviceManager -> driver path.
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
from playsem.protocol_servers import MQTTServer


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
    return device_manager, EffectDispatcher(device_manager), driver


async def publish_sample_effects(host, port):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.error("paho-mqtt is required for this demo")
        return

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(client, userdata, flags, rc, properties=None):
        logger.info("Publisher connected to MQTT broker (rc=%s)", rc)

    client.on_connect = on_connect
    client.connect(host, port, 60)
    client.loop_start()
    await asyncio.sleep(0.5)

    effects = [
        {
            "effect_type": "light",
            "duration": 1000,
            "intensity": 80,
            "parameters": {"color": "white"},
        },
        {
            "effect_type": "wind",
            "duration": 750,
            "intensity": 60,
            "parameters": {"speed": 3},
        },
        {
            "effect_type": "vibration",
            "duration": 500,
            "intensity": 90,
            "parameters": {"pattern": "pulse"},
        },
    ]

    print("\n" + "=" * 60)
    print("Publishing sample MQTT effects")
    print("=" * 60)

    for index, effect in enumerate(effects, start=1):
        payload = json.dumps(effect)
        info = client.publish("effects/demo_device", payload)
        if hasattr(info, "wait_for_publish"):
            info.wait_for_publish()
        print(f"{index}. {effect['effect_type']} -> {payload}")
        await asyncio.sleep(0.5)

    client.loop_stop()
    client.disconnect()


async def main():
    print("\n" + "=" * 60)
    print("PlaySEM MQTT Protocol Demo")
    print("=" * 60)

    _, dispatcher, driver = build_dispatcher()
    received_effects = []

    async def on_effect_broadcast(effect, source):
        received_effects.append(effect)
        logger.info(
            "Effect received from %s: %s (%s ms, intensity=%s)",
            source,
            effect.effect_type,
            effect.duration,
            effect.intensity,
        )

    mqtt_port = 1883
    mqtt_server = MQTTServer(
        dispatcher=dispatcher,
        host="127.0.0.1",
        port=mqtt_port,
        subscribe_topic="effects/#",
        on_effect_broadcast=on_effect_broadcast,
    )

    print("\nMQTT broker configuration")
    print(f"  broker: mqtt://127.0.0.1:{mqtt_port}")
    print("  subscribe topic: effects/#")
    print(f"  local address: {get_local_ip()}")

    print("\nStarting embedded MQTT broker...")
    mqtt_server.start()

    try:
        await asyncio.wait_for(mqtt_server.wait_until_ready(), timeout=15.0)
    except asyncio.TimeoutError:
        print("Broker failed to become ready within 15 seconds")
        mqtt_server.stop()
        return 1

    await asyncio.sleep(0.5)
    await publish_sample_effects("127.0.0.1", mqtt_port)
    await asyncio.sleep(1.0)

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

    print("\nStopping MQTT broker...")
    mqtt_server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
