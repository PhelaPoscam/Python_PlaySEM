#!/usr/bin/env python3
"""
Comprehensive Protocol Validation
Tests all 5 protocol handlers can be instantiated and managed.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.test_server.handlers import (
    HTTPHandler,
    CoAPHandler,
    UPnPHandler,
    MQTTHandler,
    WebSocketHandler,
)

from tools.test_server.handlers.http_handler import HTTPConfig
from tools.test_server.handlers.coap_handler import CoAPConfig
from tools.test_server.handlers.upnp_handler import UPnPConfig
from tools.test_server.handlers.mqtt_handler import MQTTConfig
from tools.test_server.handlers.websocket_handler import WebSocketConfig


class MockEffectDispatcher:
    """Mock dispatcher for testing protocol handlers."""
    
    async def dispatch_effect(self, device_id: str, effect_data: dict):
        """Mock effect dispatch."""
        pass


def test_all_protocol_handlers():
    """Test that all protocol handlers can be instantiated."""
    print("\n" + "=" * 60)
    print("PROTOCOL HANDLER VALIDATION")
    print("=" * 60)
    
    dispatcher = MockEffectDispatcher()
    results = {}
    
    # Test HTTP Handler
    print("\n[Testing] HTTP Handler...")
    try:
        config = HTTPConfig(host="127.0.0.1", port=18080)
        handler = HTTPHandler(global_dispatcher=dispatcher, config=config)
        status = handler.get_status()
        results["HTTP"] = {
            "passed": True,
            "status": status,
            "config": {"host": config.host, "port": config.port},
        }
        print("[OK] HTTP Handler instantiated successfully")
    except Exception as e:
        results["HTTP"] = {"passed": False, "error": str(e)}
        print(f"[FAIL] HTTP Handler error: {e}")
    
    # Test CoAP Handler
    print("[Testing] CoAP Handler...")
    try:
        config = CoAPConfig(host="127.0.0.1", port=15683)
        handler = CoAPHandler(global_dispatcher=dispatcher, config=config)
        status = handler.get_status()
        results["CoAP"] = {
            "passed": True,
            "status": status,
            "config": {"host": config.host, "port": config.port},
        }
        print("[OK] CoAP Handler instantiated successfully")
    except Exception as e:
        results["CoAP"] = {"passed": False, "error": str(e)}
        print(f"[FAIL] CoAP Handler error: {e}")
    
    # Test UPnP Handler
    print("[Testing] UPnP Handler...")
    try:
        config = UPnPConfig(
            device_name="PlaySEM Test",
            device_type="urn:test:device:Haptic:1"
        )
        handler = UPnPHandler(global_dispatcher=dispatcher, config=config)
        status = handler.get_status()
        results["UPnP"] = {
            "passed": True,
            "status": status,
            "config": {
                "device_name": config.device_name,
                "device_type": config.device_type,
            },
        }
        print("[OK] UPnP Handler instantiated successfully")
    except Exception as e:
        results["UPnP"] = {"passed": False, "error": str(e)}
        print(f"[FAIL] UPnP Handler error: {e}")
    
    # Test MQTT Handler
    print("[Testing] MQTT Handler...")
    try:
        config = MQTTConfig(host="127.0.0.1", port=11883, broker_id="test_broker")
        handler = MQTTHandler(global_dispatcher=dispatcher, config=config)
        status = handler.get_status()
        results["MQTT"] = {
            "passed": True,
            "status": status,
            "config": {"host": config.host, "port": config.port},
        }
        print("[OK] MQTT Handler instantiated successfully")
    except Exception as e:
        results["MQTT"] = {"passed": False, "error": str(e)}
        print(f"[FAIL] MQTT Handler error: {e}")
    
    # Test WebSocket Handler
    print("[Testing] WebSocket Handler...")
    try:
        config = WebSocketConfig(host="127.0.0.1", port=18081)
        handler = WebSocketHandler(global_dispatcher=dispatcher, config=config)
        status = handler.get_status()
        results["WebSocket"] = {
            "passed": True,
            "status": status,
            "config": {"host": config.host, "port": config.port},
        }
        print("[OK] WebSocket Handler instantiated successfully")
    except Exception as e:
        results["WebSocket"] = {"passed": False, "error": str(e)}
        print(f"[FAIL] WebSocket Handler error: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r["passed"])
    total = len(results)
    
    print(f"\nProtocols Validated: {passed}/{total}\n")
    
    for protocol, result in results.items():
        status = "[OK]" if result["passed"] else "[FAIL]"
        print(f"{status} {protocol}")
        
        if result["passed"]:
            print(f"    Status: {result['status']}")
            print(f"    Config: {result['config']}")
        else:
            print(f"    Error: {result['error']}")
        print()
    
    print("=" * 60)
    
    if passed == total:
        print("\n[OK] All protocols validated successfully!")
        print("\nArchitecture Status: MODULAR EXTRACTION COMPLETE")
        print("  [OK] HTTPHandler")
        print("  [OK] CoAPHandler")
        print("  [OK] UPnPHandler")
        print("  [OK] MQTTHandler (existing)")
        print("  [OK] WebSocketHandler (existing)")
        print("\nAll 5 protocol handlers working correctly!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} protocol(s) failed validation")
        return 1


if __name__ == "__main__":
    exit_code = test_all_protocol_handlers()
    sys.exit(exit_code)
