"""
Simple CLI Example using PlaySEM library

Demonstrates basic usage of the playsem framework.

Usage:
    python examples/simple_cli.py
"""

import asyncio
import logging
from pathlib import Path
import cmd

# Import from the playsem library
from playsem import DeviceManager
from playsem.drivers import MockLightDevice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleCLI(cmd.Cmd):
    """Simple command-line interface for PlaySEM."""

    prompt = "(playsem) "
    intro = "🎮 Welcome to the PlaySEM Simple CLI! Type help or ? to list commands.\n"

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def do_list_devices(self, arg):
        """List all available devices."""
        logger.info("Available Devices:")
        devices = self.manager.get_all_devices()
        if not devices:
            logger.info("   No devices found.")
        for device in devices:
            logger.info(f"   • {device.name} ({device.id}) - Type: {device.type}")

    def do_a_thing(self, arg):
        """Prints 'Doing a thing!'"""
        print("Doing a thing!")

    def do_quit(self, arg):
        """Exit the CLI."""
        print("👋 Goodbye!")
        return True

    def do_exit(self, arg):
        """Exit the CLI."""
        return self.do_quit(arg)


async def initialize_manager():
    """Initialize the device manager."""
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
        mock_device = MockLightDevice("mock_light_1", "Demo Light")
        await manager.add_device(mock_device)
    return manager


def main():
    """Run simple CLI demonstration."""
    logger.info("🎮 PlaySEM Simple CLI Example")
    logger.info("=" * 50)

    # Initialize device manager
    logger.info("\n1️⃣  Initializing Device Manager...")
    manager = asyncio.run(initialize_manager())

    # Start the CLI
    cli = SimpleCLI(manager)
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
