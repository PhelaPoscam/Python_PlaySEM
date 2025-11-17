"""
Test WebSocket Client for PlaySEM

This script demonstrates sending SEM (Sensory Effect Metadata) to PlaySEM
via the WebSocket protocol server (port 8765).

Note: This connects to the WebSocket SEM Server (port 8765), NOT the control
panel WebSocket (port 8090). The control panel WebSocket is for UI control only.

Usage:
    python test_websocket_client.py
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime


async def send_effect(
    websocket, effect_type, intensity, duration, timestamp=0
):
    """Send a single effect to PlaySEM."""
    effect = {
        "effect_type": effect_type,
        "intensity": intensity,
        "duration": duration,
        "timestamp": timestamp,
    }

    await websocket.send(json.dumps(effect))
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Sent: {effect_type} "
        f"(intensity={intensity}, duration={duration}ms)"
    )

    try:
        # Wait for response (with timeout)
        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        result = json.loads(response)
        if result.get("status") == "success":
            print(f"  ✓ Effect executed successfully")
        else:
            print(
                f"  ✗ Effect failed: {result.get('message', 'Unknown error')}"
            )
    except asyncio.TimeoutError:
        print(f"  ⚠ No response (server may not send confirmations)")
    except Exception as e:
        print(f"  ✗ Error: {e}")


async def test_websocket_protocol():
    """Test the WebSocket protocol server with various effects."""

    # Connect to WebSocket SEM Server (NOT control panel!)
    uri = "ws://localhost:8765"

    print("=" * 60)
    print("PlaySEM WebSocket Protocol Test")
    print("=" * 60)
    print(f"\nConnecting to: {uri}")
    print("(WebSocket SEM Server - port 8765)")
    print("\nMake sure:")
    print("  1. Control panel is running (control_panel_server.py)")
    print("  2. WebSocket SEM Server is started in control panel")
    print("  3. At least one device is connected")
    print("=" * 60)
    print()

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✓ Connected to PlaySEM WebSocket server\n")

            # Test sequence of effects
            print("Sending effect sequence...\n")

            # 1. Vibration effect
            await send_effect(websocket, "vibration", 80, 1000)
            await asyncio.sleep(0.5)

            # 2. Light effect
            await send_effect(websocket, "light", 100, 2000)
            await asyncio.sleep(0.5)

            # 3. Wind effect
            await send_effect(websocket, "wind", 60, 1500)
            await asyncio.sleep(0.5)

            # 4. Synchronized effects with timestamps
            print("\nSending synchronized effect sequence...")
            print(
                "(All effects sent at once, executed at specified timestamps)\n"
            )

            effects = [
                {
                    "effect_type": "light",
                    "intensity": 100,
                    "duration": 500,
                    "timestamp": 0,
                },
                {
                    "effect_type": "vibration",
                    "intensity": 70,
                    "duration": 300,
                    "timestamp": 500,
                },
                {
                    "effect_type": "wind",
                    "intensity": 80,
                    "duration": 1000,
                    "timestamp": 800,
                },
            ]

            for effect in effects:
                await websocket.send(json.dumps(effect))
                print(
                    f"  → {effect['effect_type']} at t={effect['timestamp']}ms"
                )

            await asyncio.sleep(1)

            print("\n" + "=" * 60)
            print("✓ Test completed successfully!")
            print("=" * 60)
            print(
                "\nCheck the control panel Activity Log for effect execution."
            )

    except ConnectionRefusedError:
        print("✗ Connection refused!")
        print("\nTroubleshooting:")
        print("  1. Is control_panel_server.py running?")
        print("  2. Is the WebSocket SEM Server started in the control panel?")
        print(
            "     (Look for 'Protocol Servers' section and click 'Start' on WebSocket)"
        )
        print("  3. Is port 8765 available?")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print(f"\nException type: {type(e).__name__}")
        sys.exit(1)


async def test_streaming_effects():
    """Test continuous streaming of effects (e.g., for game integration)."""
    uri = "ws://localhost:8765"

    print("\n" + "=" * 60)
    print("Testing continuous effect streaming...")
    print("=" * 60)
    print("(Simulating game/VR app sending real-time effects)\n")

    try:
        async with websockets.connect(uri) as websocket:
            # Simulate 5 seconds of gameplay with varying wind intensity
            print("Simulating wind effects during 5-second action sequence:\n")

            for i in range(10):
                # Wind intensity varies with "gameplay intensity"
                intensity = 50 + (i % 5) * 10  # 50-90%
                duration = 500

                await send_effect(websocket, "wind", intensity, duration)
                await asyncio.sleep(0.5)

            print("\n✓ Streaming test completed")

    except Exception as e:
        print(f"✗ Streaming test failed: {e}")


async def main():
    """Run all WebSocket tests."""

    # Test 1: Basic effect sending
    await test_websocket_protocol()

    # Wait a bit between tests
    await asyncio.sleep(2)

    # Test 2: Continuous streaming (optional - uncomment to enable)
    # await test_streaming_effects()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
