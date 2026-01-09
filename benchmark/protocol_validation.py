#!/usr/bin/env python3
"""
<<<<<<< HEAD
Protocol Validation & Performance Benchmark

Validates all protocol handlers and benchmarks their performance.
"""

import asyncio
import logging
import time
from typing import Dict, List, Tuple
import json

from playsem.device_registry import DeviceRegistry
from playsem.device_manager import DeviceManager
from playsem.effect_dispatcher import EffectDispatcher
from playsem.effect_metadata import EffectMetadata
from playsem.protocol_servers.http_server import HTTPServer
from playsem.protocol_servers.coap_server import CoAPServer
from playsem.protocol_servers.upnp_server import UPnPServer
from playsem.protocol_servers.mqtt_server import MQTTServer
from playsem.protocol_servers.websocket_server import WebSocketServer

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ProtocolBenchmark:
    """Benchmark suite for protocol handlers."""

    def __init__(self):
        """Initialize benchmark with required components."""
        # Initialize registry
        self.registry = DeviceRegistry()
        
        # Initialize device manager in legacy mode with a mock client
        # This avoids the need for config_loader during benchmark
        mock_client = type('MockClient', (), {'publish': lambda *args, **kwargs: None})()
        self.manager = DeviceManager(client=mock_client)
        
        # Initialize effect dispatcher
        self.dispatcher = EffectDispatcher(device_manager=self.manager)

        # Protocol servers
        self.servers = {}
        self.results = {
            "passed": 0,
            "failed": 0,
            "protocols": {}
        }
        self.performance_data = {}

    async def test_http_handler(self) -> Tuple[bool, str]:
        """Test HTTP handler initialization and basic functionality."""
        try:
            server = HTTPServer(
                host="127.0.0.1",
                port=18080,
                dispatcher=self.dispatcher,
                api_key=None
            )
            self.servers["http"] = server
            logger.info("HTTPHandler initialized (server=127.0.0.1:18080, auth=disabled)")
            return True, "HTTP server initialized successfully"
        except Exception as e:
            return False, str(e)

    async def test_coap_handler(self) -> Tuple[bool, str]:
        """Test CoAP handler initialization."""
        try:
            server = CoAPServer(
                host="127.0.0.1",
                port=5683,
                dispatcher=self.dispatcher
            )
            self.servers["coap"] = server
            return True, "CoAP server initialized successfully"
        except Exception as e:
            return False, str(e)

    async def test_upnp_handler(self) -> Tuple[bool, str]:
        """Test UPnP handler initialization."""
        try:
            server = UPnPServer(
                friendly_name="PlaySEM Benchmark",
                dispatcher=self.dispatcher,
                http_host="127.0.0.1",
                http_port=18080
            )
            self.servers["upnp"] = server
            return True, "UPnP server initialized successfully"
        except Exception as e:
            return False, str(e)

    async def test_mqtt_handler(self) -> Tuple[bool, str]:
        """Test MQTT handler initialization."""
        try:
            server = MQTTServer(
                dispatcher=self.dispatcher,
                host="0.0.0.0",
                port=1883
            )
            self.servers["mqtt"] = server
            return True, "MQTT server initialized successfully"
        except Exception as e:
            return False, str(e)

    async def test_websocket_handler(self) -> Tuple[bool, str]:
        """Test WebSocket handler initialization."""
        try:
            server = WebSocketServer(
                host="127.0.0.1",
                port=18081,
                dispatcher=self.dispatcher,
                auth_token=None
            )
            self.servers["websocket"] = server
            return True, "WebSocket server initialized successfully"
        except Exception as e:
            return False, str(e)

    async def benchmark_handlers(self):
        """Benchmark protocol handlers."""
        protocols = [
=======
Comprehensive Protocol Validation & Performance Benchmark
Tests ALL protocols: HTTP, CoAP, UPnP, MQTT, WebSocket
Compares monolith vs modular architecture performance
"""

import asyncio
import time
import statistics
from typing import Dict, List, Tuple
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playsem.effect_dispatcher import EffectDispatcher
from playsem.device_registry import DeviceRegistry

# Import all protocol handlers
from tools.test_server.handlers import (
    HTTPHandler,
    CoAPHandler,
    UPnPHandler,
    MQTTHandler,
    WebSocketHandler,
)

# Import protocol servers
from playsem.protocol_servers import (
    HTTPServer,
    CoAPServer,
    UPnPServer,
    MQTTServer,
    WebSocketServer,
)


class MockEffectDispatcher:
    """Mock dispatcher for testing protocol handlers."""
    
    async def dispatch_effect(self, device_id: str, effect_data: Dict[str, Any]):
        """Mock effect dispatch - just logs the call."""
        pass


class ProtocolBenchmark:
    """Comprehensive protocol testing and performance measurement."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        # Use mock dispatcher for testing
        self.dispatcher = MockEffectDispatcher()
    
    async def measure_latency(
        self, 
        func, 
        iterations: int = 100
    ) -> Tuple[float, float, float]:
        """Measure function latency: (avg, min, max) in milliseconds."""
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        return (
            statistics.mean(latencies),
            min(latencies),
            max(latencies),
        )
    
    async def test_http_handler(self) -> Dict:
        """Test HTTP REST API handler."""
        print("\n[Testing] HTTP Handler...")
        
        from tools.test_server.handlers.http_handler import HTTPConfig
        
        config = HTTPConfig(host="127.0.0.1", port=18080)
        handler = HTTPHandler(
            global_dispatcher=self.dispatcher,
            config=config,
        )
        
        try:
            # Start handler
            start = time.time()
            await handler.start()
            startup_time = (time.time() - start) * 1000
            
            # Test send_effect
            async def send_test():
                await handler.send_effect(
                    "test_device",
                    {"effect_name": "vibrate", "intensity": 0.5},
                )
            
            avg, min_lat, max_lat = await self.measure_latency(send_test, 50)
            
            # Get status
            status = handler.get_status()
            
            # Stop handler
            await handler.stop()
            
            return {
                "protocol": "HTTP",
                "startup_ms": round(startup_time, 2),
                "avg_latency_ms": round(avg, 2),
                "min_latency_ms": round(min_lat, 2),
                "max_latency_ms": round(max_lat, 2),
                "status": status,
                "passed": True,
            }
        except Exception as e:
            return {
                "protocol": "HTTP",
                "error": str(e),
                "passed": False,
            }
    
    async def test_coap_handler(self) -> Dict:
        """Test CoAP (UDP) handler."""
        print("[Testing] CoAP Handler...")
        
        from tools.test_server.handlers.coap_handler import CoAPConfig
        
        config = CoAPConfig(host="127.0.0.1", port=15683)
        handler = CoAPHandler(
            global_dispatcher=self.dispatcher,
            config=config,
        )
        
        try:
            start = time.time()
            await handler.start()
            startup_time = (time.time() - start) * 1000
            
            async def send_test():
                await handler.send_effect(
                    "test_device",
                    {"effect_name": "pattern", "pattern": [1, 0, 1]},
                )
            
            avg, min_lat, max_lat = await self.measure_latency(send_test, 50)
            
            status = handler.get_status()
            await handler.stop()
            
            return {
                "protocol": "CoAP",
                "startup_ms": round(startup_time, 2),
                "avg_latency_ms": round(avg, 2),
                "min_latency_ms": round(min_lat, 2),
                "max_latency_ms": round(max_lat, 2),
                "status": status,
                "passed": True,
            }
        except Exception as e:
            return {
                "protocol": "CoAP",
                "error": str(e),
                "passed": False,
            }
    
    async def test_upnp_handler(self) -> Dict:
        """Test UPnP/SSDP discovery handler."""
        print("[Testing] UPnP Handler...")
        
        from tools.test_server.handlers.upnp_handler import UPnPConfig
        
        config = UPnPConfig(
            device_name="PlaySEM Test",
            device_type="urn:test:device:Haptic:1"
        )
        handler = UPnPHandler(
            global_dispatcher=self.dispatcher,
            config=config,
        )
        
        try:
            start = time.time()
            await handler.start()
            startup_time = (time.time() - start) * 1000
            
            # UPnP is discovery-based, test effect dispatch
            async def send_test():
                await handler.send_effect(
                    "test_device",
                    {"effect_name": "intensity", "value": 0.8},
                )
            
            avg, min_lat, max_lat = await self.measure_latency(send_test, 50)
            
            status = handler.get_status()
            await handler.stop()
            
            return {
                "protocol": "UPnP/SSDP",
                "startup_ms": round(startup_time, 2),
                "avg_latency_ms": round(avg, 2),
                "min_latency_ms": round(min_lat, 2),
                "max_latency_ms": round(max_lat, 2),
                "status": status,
                "passed": True,
            }
        except Exception as e:
            return {
                "protocol": "UPnP/SSDP",
                "error": str(e),
                "passed": False,
            }
    
    async def test_mqtt_handler(self) -> Dict:
        """Test MQTT pub/sub handler."""
        print("[Testing] MQTT Handler...")
        
        from tools.test_server.handlers.mqtt_handler import MQTTConfig
        
        config = MQTTConfig(
            host="127.0.0.1",
            port=11883,
            broker_id="test_broker"
        )
        handler = MQTTHandler(
            global_dispatcher=self.dispatcher,
            config=config,
        )
        
        try:
            start = time.time()
            await handler.start()
            startup_time = (time.time() - start) * 1000
            
            async def send_test():
                await handler.send_effect(
                    "test_device",
                    {"effect_name": "vibrate", "duration": 100},
                )
            
            avg, min_lat, max_lat = await self.measure_latency(send_test, 50)
            
            status = handler.get_status()
            await handler.stop()
            
            return {
                "protocol": "MQTT",
                "startup_ms": round(startup_time, 2),
                "avg_latency_ms": round(avg, 2),
                "min_latency_ms": round(min_lat, 2),
                "max_latency_ms": round(max_lat, 2),
                "status": status,
                "passed": True,
            }
        except Exception as e:
            return {
                "protocol": "MQTT",
                "error": str(e),
                "passed": False,
            }
    
    async def test_websocket_handler(self) -> Dict:
        """Test WebSocket bidirectional handler."""
        print("[Testing] WebSocket Handler...")
        
        from tools.test_server.handlers.websocket_handler import WebSocketConfig
        
        config = WebSocketConfig(host="127.0.0.1", port=18081)
        handler = WebSocketHandler(
            global_dispatcher=self.dispatcher,
            config=config,
        )
        
        try:
            start = time.time()
            await handler.start()
            startup_time = (time.time() - start) * 1000
            
            async def send_test():
                await handler.send_effect(
                    "test_device",
                    {"effect_name": "pattern", "pattern": [1, 1, 0]},
                )
            
            avg, min_lat, max_lat = await self.measure_latency(send_test, 50)
            
            status = handler.get_status()
            await handler.stop()
            
            return {
                "protocol": "WebSocket",
                "startup_ms": round(startup_time, 2),
                "avg_latency_ms": round(avg, 2),
                "min_latency_ms": round(min_lat, 2),
                "max_latency_ms": round(max_lat, 2),
                "status": status,
                "passed": True,
            }
        except Exception as e:
            return {
                "protocol": "WebSocket",
                "error": str(e),
                "passed": False,
            }
    
    async def run_all_tests(self) -> Dict[str, Dict]:
        """Run all protocol tests sequentially."""
        print("\n" + "=" * 60)
        print("PROTOCOL VALIDATION & PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        tests = [
>>>>>>> refactor/modular-server
            ("HTTP", self.test_http_handler),
            ("CoAP", self.test_coap_handler),
            ("UPnP", self.test_upnp_handler),
            ("MQTT", self.test_mqtt_handler),
            ("WebSocket", self.test_websocket_handler),
        ]
<<<<<<< HEAD

        print("\n" + "=" * 60)
        print("PROTOCOL VALIDATION & PERFORMANCE BENCHMARK")
        print("=" * 60 + "\n")

        for protocol_name, test_func in protocols:
            print(f"[Testing] {protocol_name} Handler...")
            success, message = await test_func()
            
            if success:
                self.results["passed"] += 1
                self.results["protocols"][protocol_name.lower()] = "PASS"
            else:
                self.results["failed"] += 1
                self.results["protocols"][protocol_name.lower()] = f"FAIL: {message}"

        # Print validation results
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60 + "\n")

        total = self.results["passed"] + self.results["failed"]
        print(f"Passed: {self.results['passed']}/{total} protocols\n")

        for protocol, result in self.results["protocols"].items():
            if result == "PASS":
                print(f"[PASS] {protocol.upper()}")
            else:
                print(f"[FAIL] {protocol.upper()}")
                print(f"  Error: {result.replace('FAIL: ', '')}\n")

        # Performance comparison
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60 + "\n")

        # Print summary
        print("\n" + "=" * 60 + "\n")
        if self.results["failed"] == 0:
            print("[SUCCESS] All protocols validated!")
            return True
        else:
            print(f"[FAIL] {self.results['failed']} protocol(s) failed validation")
            return False


async def main():
    """Main entry point."""
    try:
        benchmark = ProtocolBenchmark()
        success = await benchmark.benchmark_handlers()
        return 0 if success else 1
    except Exception as e:
        print(f"\n[ERROR] Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
=======
        
        results = {}
        for name, test_func in tests:
            try:
                result = await test_func()
                results[name] = result
            except Exception as e:
                results[name] = {
                    "protocol": name,
                    "error": str(e),
                    "passed": False,
                }
        
        return results
    
    def print_report(self, results: Dict[str, Dict]):
        """Print comprehensive test report."""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        passed = sum(1 for r in results.values() if r.get("passed"))
        total = len(results)
        
        print(f"\nPassed: {passed}/{total} protocols\n")
        
        for protocol, result in results.items():
            status = "[OK]" if result.get("passed") else "[FAIL]"
            print(f"{status} {protocol}")
            
            if result.get("passed"):
                print(f"  Startup: {result['startup_ms']}ms")
                print(f"  Latency: {result['avg_latency_ms']}ms (avg)")
                print(f"  Range: {result['min_latency_ms']}ms - {result['max_latency_ms']}ms")
            else:
                print(f"  Error: {result.get('error', 'Unknown')}")
            print()
        
        print("=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        
        if all(r.get("passed") for r in results.values()):
            latencies = [
                (r["protocol"], r["avg_latency_ms"])
                for r in results.values()
            ]
            latencies.sort(key=lambda x: x[1])
            
            print("\nProtocol ranking by latency (fastest first):")
            for i, (proto, lat) in enumerate(latencies, 1):
                print(f"{i}. {proto}: {lat}ms")
            
            fastest = latencies[0][1]
            slowest = latencies[-1][1]
            speedup = slowest / fastest if fastest > 0 else 1
            
            print(f"\nPerformance spread: {speedup:.2f}x")
            print(f"Fastest: {latencies[0][0]} ({fastest}ms)")
            print(f"Slowest: {latencies[-1][0]} ({slowest}ms)")
        
        print("\n" + "=" * 60)
        
        return passed == total


async def main():
    """Run comprehensive protocol validation."""
    benchmark = ProtocolBenchmark()
    results = await benchmark.run_all_tests()
    success = benchmark.print_report(results)
    
    if success:
        print("\n[OK] All protocols validated successfully")
        return 0
    else:
        print("\n[FAIL] Some protocols failed validation")
>>>>>>> refactor/modular-server
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
<<<<<<< HEAD
    exit(exit_code)
=======
    sys.exit(exit_code)
>>>>>>> refactor/modular-server
