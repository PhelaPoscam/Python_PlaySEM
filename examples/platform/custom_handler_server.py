#!/usr/bin/env python3
"""
Custom Handler Server Example

Demonstrates how to extend the modular architecture with custom protocol handlers.
This example shows integration of MQTT handler with the server.

Run:
    python examples/platform/custom_handler_server.py

Features:
    - All basic_server features
    - Custom MQTT handler integration
    - Shows protocol handler extensibility pattern
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI
from tools.test_server.app import create_app
from tools.test_server.config import ServerConfig
from tools.test_server.app.handlers import MQTTHandler


def create_app_with_mqtt(config: ServerConfig) -> FastAPI:
    """
    Create app with MQTT handler integration.
    
    This demonstrates the extensibility pattern:
    1. Create base app with create_app()
    2. Get services from app.state
    3. Register custom handlers
    """
    # Create base app
    app = create_app(config)
    
    # Get protocol service from app state
    protocol_service = app.state.protocol_service
    
    # Create and register MQTT handler
    mqtt_handler = MQTTHandler(
        broker_host="localhost",
        broker_port=1883,
        topic_prefix="playsem",
    )
    
    # Register with protocol service
    protocol_service.register_handler("mqtt", mqtt_handler)
    
    print("[OK] MQTT handler registered")
    print(f"  Broker: {mqtt_handler.broker_host}:{mqtt_handler.broker_port}")
    print(f"  Topic: {mqtt_handler.topic_prefix}/#")
    
    return app


def main():
    """Create and run server with custom MQTT handler."""
    
    print("=" * 60)
    print("PlaySEM Custom Handler Server Example")
    print("=" * 60)
    print()
    print("This demonstrates handler extensibility:")
    print("  [OK] All basic server features")
    print("  [OK] Custom MQTT handler integration")
    print("  [OK] Protocol service extensibility")
    print()
    print("Additional Endpoints:")
    print("  POST /api/protocols/mqtt/publish   - Publish MQTT message")
    print("  POST /api/protocols/mqtt/subscribe - Subscribe to topic")
    print()
    print("MQTT Topics:")
    print("  playsem/devices/+/effects   - Effect commands")
    print("  playsem/devices/+/status    - Device status updates")
    print()
    print("-" * 60)
    print()
    
    # Configure server
    config = ServerConfig(
        host="127.0.0.1",
        port=8090,
        debug=False,
    )
    
    # Create app with MQTT handler
    app = create_app_with_mqtt(config)
    
    # Run server
    print(f"Starting server on http://{config.host}:{config.port}")
    print()
    print("Testing:")
    print("  1. Start an MQTT broker: mosquitto -v")
    print("  2. Connect a device via MQTT")
    print("  3. Send effects via HTTP API or MQTT topic")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
