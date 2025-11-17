"""Integration tests for MQTT Server - tests with real MQTT client"""

import pytest
import json
import time
from unittest.mock import Mock

from src.protocol_server import MQTTServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.device_driver.mock_driver import MockDriver


# Note: These tests require a running MQTT broker
# Skip if broker not available
def check_mqtt_broker():
    """Check if MQTT broker is available."""
    import socket
    try:
        sock = socket.socket(socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 1883))
        sock.close()
        return result == 0
    except:
        return False


mqtt_available = check_mqtt_broker()
requires_mqtt = pytest.mark.skipif(
    not mqtt_available,
    reason="MQTT broker not running on localhost:1883"
)


@requires_mqtt
def test_mqtt_server_real_connection():
    """
    Integration test: Connect to real MQTT broker.
    
    Requires: mosquitto or other MQTT broker running on localhost:1883
    """
    manager = DeviceManager()
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    
    # Start server (connects to broker)
    server.start()
    
    # Give it time to connect
    time.sleep(0.5)
    
    try:
        # Verify connection
        assert server.is_running()
        
    finally:
        # Cleanup
        server.stop()
        time.sleep(0.2)


@requires_mqtt
def test_mqtt_send_and_receive_effect():
    """
    Integration test: Send real MQTT message and receive effect.
    
    This is the REAL test that would catch integration bugs!
    """
    import paho.mqtt.client as mqtt_client
    
    # Setup device and dispatcher
    manager = DeviceManager()
    driver = MockDriver("mqtt_device")
    manager.register_device("mqtt_device", "light", driver)
    dispatcher = EffectDispatcher(manager)
    
    # Track received effects
    received_effects = []
    
    def on_effect(effect):
        received_effects.append(effect)
    
    # Start MQTT server
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    server.on_effect_received = on_effect
    server.start()
    
    time.sleep(0.5)
    
    try:
        # Create real MQTT client to send effect
        client = mqtt_client.Client(client_id="test_publisher")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        time.sleep(0.2)
        
        # Send effect via MQTT
        effect_payload = json.dumps({
            "effect_type": "light",
            "timestamp": 0,
            "duration": 1000,
            "intensity": 90
        })
        
        client.publish("effects/light", effect_payload)
        
        # Wait for processing
        time.sleep(0.5)
        
        # Verify effect received
        assert len(received_effects) == 1
        assert received_effects[0].effect_type == "light"
        assert received_effects[0].intensity == 90
        
        # Verify device received effect
        assert len(driver.effects_sent) == 1
        assert driver.effects_sent[0] == ("light", 90, 1000)
        
        # Cleanup client
        client.loop_stop()
        client.disconnect()
        
    finally:
        server.stop()
        time.sleep(0.2)


@requires_mqtt
def test_mqtt_multiple_effects_sequence():
    """
    Integration test: Send multiple effects via MQTT.
    """
    import paho.mqtt.client as mqtt_client
    
    manager = DeviceManager()
    driver = MockDriver("multi_device")
    manager.register_device("multi_device", "light", driver)
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    server.start()
    time.sleep(0.5)
    
    try:
        client = mqtt_client.Client(client_id="multi_publisher")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(0.2)
        
        # Send multiple effects
        effects = [
            ("light", 50),
            ("light", 75),
            ("light", 100),
        ]
        
        for effect_type, intensity in effects:
            payload = json.dumps({
                "effect_type": effect_type,
                "timestamp": 0,
                "duration": 500,
                "intensity": intensity
            })
            client.publish(f"effects/{effect_type}", payload)
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        # Verify all received
        assert len(driver.effects_sent) == 3
        
        client.loop_stop()
        client.disconnect()
        
    finally:
        server.stop()


@requires_mqtt
def test_mqtt_different_topics():
    """
    Integration test: Test effects on different MQTT topics.
    """
    import paho.mqtt.client as mqtt_client
    
    manager = DeviceManager()
    
    # Create devices for different types
    light_driver = MockDriver("light")
    vibration_driver = MockDriver("vibration")
    wind_driver = MockDriver("wind")
    
    manager.register_device("light", "light", light_driver)
    manager.register_device("vibration", "vibration", vibration_driver)
    manager.register_device("wind", "wind", wind_driver)
    
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher,
        topic_pattern="effects/#"
    )
    server.start()
    time.sleep(0.5)
    
    try:
        client = mqtt_client.Client(client_id="topic_publisher")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(0.2)
        
        # Send to different topics
        topics_and_types = [
            ("effects/light", "light"),
            ("effects/vibration", "vibration"),
            ("effects/wind", "wind"),
        ]
        
        for topic, effect_type in topics_and_types:
            payload = json.dumps({
                "effect_type": effect_type,
                "timestamp": 0,
                "duration": 1000,
                "intensity": 80
            })
            client.publish(topic, payload)
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        # Each device should have received its effect
        assert len(light_driver.effects_sent) == 1
        assert len(vibration_driver.effects_sent) == 1
        assert len(wind_driver.effects_sent) == 1
        
        client.loop_stop()
        client.disconnect()
        
    finally:
        server.stop()


@requires_mqtt
def test_mqtt_invalid_json_handling():
    """
    Integration test: Test MQTT server handles invalid JSON gracefully.
    """
    import paho.mqtt.client as mqtt_client
    
    manager = DeviceManager()
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    server.start()
    time.sleep(0.5)
    
    try:
        client = mqtt_client.Client(client_id="invalid_publisher")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(0.2)
        
        # Send invalid JSON
        client.publish("effects/test", "this is not json")
        
        time.sleep(0.3)
        
        # Server should handle gracefully (not crash)
        assert server.is_running()
        
        client.loop_stop()
        client.disconnect()
        
    finally:
        server.stop()


@requires_mqtt
def test_mqtt_qos_levels():
    """
    Integration test: Test MQTT Quality of Service levels.
    """
    import paho.mqtt.client as mqtt_client
    
    manager = DeviceManager()
    driver = MockDriver("qos_device")
    manager.register_device("qos_device", "light", driver)
    dispatcher = EffectDispatcher(manager)
    
    # Server with QoS 1
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher,
        qos=1
    )
    server.start()
    time.sleep(0.5)
    
    try:
        client = mqtt_client.Client(client_id="qos_publisher")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(0.2)
        
        # Publish with QoS 1
        payload = json.dumps({
            "effect_type": "light",
            "timestamp": 0,
            "duration": 1000,
            "intensity": 100
        })
        
        result = client.publish("effects/light", payload, qos=1)
        result.wait_for_publish()
        
        time.sleep(0.5)
        
        # Should be received
        assert len(driver.effects_sent) == 1
        
        client.loop_stop()
        client.disconnect()
        
    finally:
        server.stop()


def test_mqtt_server_without_broker():
    """
    Integration test: Test MQTT server behavior when broker unavailable.
    
    This test ALWAYS runs (no broker needed).
    """
    manager = DeviceManager()
    dispatcher = EffectDispatcher(manager)
    
    # Try to connect to non-existent broker
    server = MQTTServer(
        broker_address="nonexistent.invalid.host",
        broker_port=1883,
        dispatcher=dispatcher
    )
    
    # Should not crash, but won't connect
    server.start()
    time.sleep(0.5)
    
    # May or may not be "running" depending on connection handling
    # Just verify it doesn't crash
    
    server.stop()


@requires_mqtt
def test_mqtt_reconnection_handling():
    """
    Integration test: Test MQTT server handles disconnect/reconnect.
    """
    manager = DeviceManager()
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    
    # Connect
    server.start()
    time.sleep(0.5)
    assert server.is_running()
    
    # Disconnect
    server.stop()
    time.sleep(0.3)
    assert not server.is_running()
    
    # Reconnect
    server.start()
    time.sleep(0.5)
    assert server.is_running()
    
    # Final cleanup
    server.stop()


@requires_mqtt
def test_mqtt_with_retained_messages():
    """
    Integration test: Test MQTT retained messages.
    """
    import paho.mqtt.client as mqtt_client
    
    # First, publish a retained message
    client = mqtt_client.Client(client_id="retained_publisher")
    client.connect("localhost", 1883, 60)
    
    payload = json.dumps({
        "effect_type": "light",
        "timestamp": 0,
        "duration": 1000,
        "intensity": 85
    })
    
    # Publish with retain flag
    client.publish("effects/light", payload, retain=True)
    time.sleep(0.2)
    client.disconnect()
    
    # Now start server - should receive retained message
    manager = DeviceManager()
    driver = MockDriver("retained_device")
    manager.register_device("retained_device", "light", driver)
    dispatcher = EffectDispatcher(manager)
    
    server = MQTTServer(
        broker_address="localhost",
        broker_port=1883,
        dispatcher=dispatcher
    )
    server.start()
    
    time.sleep(1.0)  # Give time to receive retained message
    
    try:
        # Should have received the retained message
        assert len(driver.effects_sent) >= 1
        
    finally:
        server.stop()
        
        # Clean up retained message
        client = mqtt_client.Client(client_id="cleanup")
        client.connect("localhost", 1883, 60)
        client.publish("effects/light", None, retain=True)
        client.disconnect()
