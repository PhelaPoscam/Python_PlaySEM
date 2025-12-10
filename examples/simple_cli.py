"""
Simple CLI Example using PlaySEM library

Demonstrates basic usage of the playsem framework.

Usage:
    python examples/simple_cli.py
"""

import asyncio
import logging
from pathlib import Path

# Import from the playsem library
from playsem import DeviceManager, EffectMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run simple CLI demonstration."""
    logger.info("🎮 PlaySEM Simple CLI Example")
    logger.info("=" * 50)

    # Initialize device manager
    logger.info("\n1️⃣  Initializing Device Manager...")
    manager = DeviceManager()

    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "devices.yaml"
    logger.info(f"📄 Loading config: {config_path}")

    try:
        await manager.initialize(config_path)
        logger.info(f"✅ Loaded {len(manager.get_all_devices())} devices\n")
    except FileNotFoundError:
        logger.warning(
            f"⚠️  Config not found: {config_path}\n"
            "   Using mock devices for demonstration..."
        )
        # Fallback to mock devices
        from playsem.drivers import MockLightDevice

        mock_device = MockLightDevice("mock_light_1", "Demo Light")
        await manager.add_device(mock_device)

    # List available devices
    logger.info("2️⃣  Available Devices:")
    devices = manager.get_all_devices()
    for device in devices:
        logger.info(f"   • {device.name} ({device.id}) - Type: {device.type}")

    if not devices:
        logger.error("❌ No devices available")
        return

    # Send test effect
    logger.info("\n3️⃣  Sending Test Effects...")
    target_device = devices[0]

    effects_to_test = [
        EffectMetadata(
            effect_type="light", intensity=80, duration=1000, timestamp=0
        ),
        EffectMetadata(
            effect_type="vibration", intensity=60, duration=500, timestamp=0
        ),
    ]

    for effect in effects_to_test:
        logger.info(
            f"   📤 {effect.effect_type} (intensity={effect.intensity}) "
            f"→ {target_device.name}"
        )
        success = await manager.send_effect(target_device.id, effect)
        if success:
            logger.info(f"      ✅ Effect delivered")
        else:
            logger.error(f"      ❌ Effect failed")

        await asyncio.sleep(0.5)

    logger.info("\n✨ Demo complete!")
    logger.info(
        "\n💡 Next steps:\n"
        "   - Add your own devices to config/devices.yaml\n"
        "   - Check examples/platform/ for full server\n"
        "   - See docs/ for API documentation"
    )


if __name__ == "__main__":
    asyncio.run(main())
