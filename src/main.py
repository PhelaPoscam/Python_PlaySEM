import asyncio
import logging
import argparse
from config_loader import ConfigLoader
from device_manager import DeviceManager
from device_driver.driver_factory import DriverFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Main entry point for the application.
    Initializes and starts the device manager and protocol servers.
    """
    parser = argparse.ArgumentParser(description="PythonPlaySEM Application")
    parser.add_argument(
        '--devices-config',
        type=str,
        default='config/devices.yaml',
        help='Path to the devices configuration file (YAML, JSON, or XML).'
    )
    args = parser.parse_args()

    logging.info("Starting application")

    # Load configurations using the specified devices config file
    try:
        config_loader = ConfigLoader(
            devices_path=args.devices_config,
            effects_path='config/effects.yaml',
            protocols_path='config/protocols.yaml'
        )
        devices_config = config_loader.load_devices_config()
        logging.info(f"Successfully loaded device configuration from '{args.devices_config}'.")
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Failed to load configuration: {e}")
        return

    # Create a list to hold all our driver instances
    drivers = []
    
    # Create drivers for each connectivity interface defined in the config
    for interface_config in devices_config.get('connectivityInterfaces', []):
        try:
            logging.info(f"Creating driver for interface: {interface_config.get('name')}")
            driver = DriverFactory.create_driver(interface_config)
            if driver:
                drivers.append(driver)
        except Exception as e:
            logging.error(f"Failed to create driver for interface {interface_config.get('name')}: {e}")

    if not drivers:
        logging.warning("No drivers were created. Please check your configuration file.")
        return

    # Initialize the DeviceManager with all the created drivers
    device_manager = DeviceManager(drivers, config_loader)

    logging.info("DeviceManager initialized.")
    logging.info("Application running. Press Ctrl+C to exit.")

    # Keep the application running
    try:
        while True:
            await asyncio.sleep(3600)  # Keep running, sleep for an hour
    except asyncio.CancelledError:
        logging.info("Application shutting down.")
    finally:
        # Perform any cleanup if necessary
        device_manager.disconnect_all()
        logging.info("All drivers disconnected.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")
