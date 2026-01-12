"""Quick test script for GUI modules."""

import sys
from pathlib import Path
import asyncio

import pytest

# Add project root to Python path for gui/tools imports
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


try:
    from gui.protocols import ProtocolFactory
    from gui.app_controller import AppController, ConnectionConfig

    HAS_GUI_PROTOCOLS = True
except ImportError:
    HAS_GUI_PROTOCOLS = False


@pytest.mark.skipif(
    not HAS_GUI_PROTOCOLS, reason="gui.protocols module not available"
)
async def test_websocket_protocol():
    """Test WebSocket protocol creation."""
    print("\n=== Testing WebSocket Protocol ===")
    protocol = ProtocolFactory.create("websocket", "localhost", 8090)
    if not protocol:
        print("[X] Failed to create WebSocket protocol")
        return False

    print(f"[OK] WebSocket protocol created: {protocol.get_connection_info()}")
    print(f'[OK] Protocol has send method: {hasattr(protocol, "send")}')
    print(f'[OK] Protocol has connect method: {hasattr(protocol, "connect")}')
    print(
        f'[OK] Protocol has disconnect method: {hasattr(protocol, "disconnect")}'
    )
    print(f'[OK] Protocol has listen method: {hasattr(protocol, "listen")}')
    return True


@pytest.mark.skipif(
    not HAS_GUI_PROTOCOLS, reason="gui.protocols module not available"
)
async def test_http_protocol():
    """Test HTTP protocol creation."""
    print("\n=== Testing HTTP Protocol ===")
    protocol = ProtocolFactory.create("http", "localhost", 8090)
    if not protocol:
        print("[X] Failed to create HTTP protocol")
        return False

    print(f"[OK] HTTP protocol created: {protocol.get_connection_info()}")
    print(f'[OK] Protocol has send method: {hasattr(protocol, "send")}')
    return True


@pytest.mark.skipif(
    not HAS_GUI_PROTOCOLS, reason="gui.protocols module not available"
)
async def test_app_controller():
    """Test AppController."""
    print("\n=== Testing AppController ===")
    controller = AppController()
    print(f"[OK] AppController created")
    print(f"[OK] Initial state: connected={controller.is_running}")
    print(f"[OK] Protocol: {controller.protocol}")
    return True


@pytest.mark.skipif(
    not HAS_GUI_PROTOCOLS, reason="gui.protocols module not available"
)
async def test_protocol_factory():
    """Test ProtocolFactory."""
    print("\n=== Testing ProtocolFactory ===")
    protocols = ProtocolFactory.available_protocols()
    print(f"[OK] Available protocols: {protocols}")
    if "websocket" not in protocols:
        print("[X] WebSocket protocol not registered")
        return False
    if "http" not in protocols:
        print("[X] HTTP protocol not registered")
        return False
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("PythonPlaySEM GUI - Module Tests")
    print("=" * 50)

    tests = [
        ("Protocol Factory", test_protocol_factory),
        ("WebSocket Protocol", test_websocket_protocol),
        ("HTTP Protocol", test_http_protocol),
        ("AppController", test_app_controller),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[X] {name} raised exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed! Ready for integration testing.")
        return 0
    else:
        print(f"\n[X] {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
