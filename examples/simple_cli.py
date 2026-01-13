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
    intro = (
        "Welcome to the PlaySEM Simple CLI! Type help or ? to list commands.\n"
    )

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def do_list_devices(self, arg):
        """List all available devices."""
        logger.info("Available Devices:")
        devices_config = self.manager.config_loader.load_devices_config()
        devices = devices_config.get("devices", [])
        if not devices:
            logger.info("   No devices found.")
        for device in devices:
            logger.info(
                f"   • {device.get('name', 'N/A')} ({device.get('deviceId', 'N/A')}) - Type: {device.get('deviceClass', 'N/A')}"
            )

    def do_list_capabilities(self, arg):
        """List the capabilities of a device.

        Usage: list_capabilities <device_id>
        """
        args = arg.split()
        if len(args) != 1:
            logger.error("Usage: list_capabilities <device_id>")
            return

        device_id = args[0]
        device_info = self.manager.get_device_info(device_id)
        if not device_info:
            logger.error(f"Device with ID '{device_id}' not found.")
            return

        logger.info(
            f"Capabilities for device '{device_info.get('name', 'N/A')}' ({device_info.get('deviceId', 'N/A')}):"
        )
        capabilities = device_info.get("capabilities", [])
        if not capabilities:
            logger.info("   No capabilities found.")
        for capability in capabilities:
            logger.info(f"   • {capability}")

    def do_send_command(self, arg):
        """Send a command to a device.

        Usage: send_command <device_id> <command_name> <value>
        """
        args = arg.split()
        if len(args) != 3:
            logger.error(
                "Usage: send_command <device_id> <command_name> <value>"
            )
            return

        device_id, command_name, value = args
        try:
            # Convert value to a more specific type if needed, e.g., int, float
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                # Keep as string if conversion fails
                pass

            logger.info(
                f"Sending command '{command_name}' with value '{value}' to device '{device_id}'"
            )
            asyncio.run(
                self.manager.send_command(device_id, command_name, value)
            )
            logger.info("✅ Command sent successfully.")
        except Exception as e:
            logger.error(f"❌ Error sending command: {e}")

    def do_quit(self, arg):
        """Exit the CLI."""
        print("👋 Goodbye!")
        return True


async def initialize_manager():
    """Initialize the device manager."""
    from playsem.config import ConfigLoader

    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "devices.yaml"
    logger.info(f"📄 Loading config: {config_path}")

    try:
        # Create config loader
        config_loader = ConfigLoader(
            devices_path=str(config_path),
            effects_path=str(config_path.parent / "effects.yaml"),
            protocols_path=str(config_path.parent / "protocols.yaml"),
        )

        # Initialize manager
        manager = DeviceManager(config_loader=config_loader)
        manager.connect_all()
        devices_config = config_loader.load_devices_config()
        num_devices = len(devices_config.get("devices", []))
        logger.info(f"✅ Loaded {num_devices} devices\n")
    except FileNotFoundError:
        logger.warning(
            f"⚠️  Config not found: {config_path}\n"
            "   Using mock devices for demonstration..."
        )
        # Fallback to mock devices
        manager = DeviceManager()
        mock_device = MockLightDevice("mock_light_1", "Demo Light")
        await manager.add_device(mock_device)
    return manager


def main():
    """Run simple CLI demonstration."""
    logger.info("PlaySEM Simple CLI Example")
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
