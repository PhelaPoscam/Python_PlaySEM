#!/usr/bin/env python3
"""
HTTP REST API Client Test Script.

Tests the HTTP REST server by sending effect requests and checking status.
Consolidated to use aiohttp for dependency reduction.

Run:
  # Start server first:
  python examples/demos/http_server_demo.py

  # Then run this client:
  python tools/http/client.py
"""

import asyncio
import aiohttp

BASE_URL = "http://localhost:8080"


async def test_server_status(session: aiohttp.ClientSession):
    """Test GET /api/status endpoint."""
    print("\n" + "=" * 60)
    print("Test 1: Server Status")
    print("=" * 60)

    try:
        async with session.get(f"{BASE_URL}/api/status") as response:
            response.raise_for_status()
            data = await response.json()
            print(f"[OK] Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Uptime: {data['uptime_seconds']:.1f}s")
            print(f"   Effects Processed: {data['effects_processed']}")
            return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


async def test_submit_effect(
    session: aiohttp.ClientSession, effect_data: dict
):
    """Test POST /api/effects endpoint."""
    print("\n" + "=" * 60)
    print(f"Test: Submit Effect ({effect_data['effect_type']})")
    print("=" * 60)

    try:
        headers = {"Content-Type": "application/json"}
        async with session.post(
            f"{BASE_URL}/api/effects", json=effect_data, headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            print(f"✅ Success: {data['message']}")
            print(f"   Effect ID: {data.get('effect_id', 'N/A')}")
            print(f"   Effect: {effect_data}")
            return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


async def test_list_devices(session: aiohttp.ClientSession):
    """Test GET /api/devices endpoint."""
    print("\n" + "=" * 60)
    print("Test 3: List Devices")
    print("=" * 60)

    try:
        async with session.get(f"{BASE_URL}/api/devices") as response:
            response.raise_for_status()
            data = await response.json()
            print(f"✅ Found {data['count']} device(s):")
            for device in data["devices"]:
                print(
                    f"   - {device['device_id']} "
                    f"({device['device_type']}) "
                    f"- {device['status']}"
                )
            return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("HTTP REST API Client Test")
    print("=" * 60)
    print(f"Server: {BASE_URL}")
    print("Make sure the server is running!")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # Test 1: Check server status
        if not await test_server_status(session):
            print("\n❌ Server not responding. Is it running?")
            return

        await asyncio.sleep(0.5)

        # Test 2: Submit various effects
        effects = [
            {
                "effect_type": "light",
                "intensity": 255,
                "duration": 2000,
                "parameters": {"color": "blue"},
            },
            {
                "effect_type": "wind",
                "intensity": 180,
                "duration": 3000,
                "parameters": {"speed": "medium"},
            },
            {
                "effect_type": "vibration",
                "intensity": 200,
                "duration": 1500,
                "location": "left",
            },
            {
                "effect_type": "scent",
                "intensity": 100,
                "duration": 5000,
                "parameters": {"fragrance": "ocean"},
            },
        ]

        for effect in effects:
            await test_submit_effect(session, effect)
            await asyncio.sleep(0.5)

        # Test 3: List devices
        await test_list_devices(session)

        # Final status check
        await asyncio.sleep(0.5)
        await test_server_status(session)

        print("\n" + "=" * 60)
        print("✅ All tests complete!")
        print("=" * 60)
        print("\nTry the interactive documentation at:")
        print(f"  {BASE_URL}/docs")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
