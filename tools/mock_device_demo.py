"""
Demonstration of the MockConnectivityDriver for testing without hardware.
"""
<<<<<<< HEAD
import sys
from pathlib import Path
import logging

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
=======

import logging
import time
>>>>>>> refactor/modular-server

from playsem.drivers.mock_driver import MockConnectivityDriver, MockLightDevice

# Configure logging to see the output from the mock driver
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    """
    Demonstrates how to use the MockConnectivityDriver and a MockLightDevice.
    """
    print("\n" + "=" * 60)
    print("🔌 Mock Driver Demo")
    print("=" * 60)

    # 1. Initialize the MockConnectivityDriver
    # This driver doesn't connect to any real hardware. It just logs commands.
    print("\n1. Creating MockConnectivityDriver...")
    mock_driver = MockConnectivityDriver()
    mock_driver.connect()

    # 2. Create a mock device
    # This simulates a specific piece of hardware, like a smart light.
    # We give it a unique ID.
    light_device_id = "mock-light-01"
    print(f"\n2. Creating a MockLightDevice with ID: '{light_device_id}'...")
    mock_light = MockLightDevice(device_id=light_device_id)

    # 3. Register the mock device with the driver
    # This tells the driver to forward commands for this ID to our mock light object.
    print(f"\n3. Registering '{light_device_id}' with the driver...")
    mock_driver.register_device(device_id=light_device_id, device_obj=mock_light)

    # 4. Check the initial state of the mock light
    print("\n4. Checking initial state of the light...")
    initial_state = mock_light.get_state()
    print(f"   - Initial state: {initial_state}")

    # 5. Send a command to the mock light via the driver
    # We'll tell the light to turn red.
    print("\n5. Sending 'set_color' command to the light...")
    command_params = {"r": 255, "g": 0, "b": 0}
    mock_driver.send_command(
        device_id=light_device_id,
        command="set_color",
        params=command_params
    )

    # 6. Check the final state of the mock light
    # The state should now be updated with the color we sent.
    print("\n6. Checking final state of the light...")
    final_state = mock_light.get_state()
    print(f"   - Final state: {final_state}")

    if final_state["r"] == 255 and final_state["g"] == 0 and final_state["b"] == 0:
        print("\n✅ Success! The mock light state was updated correctly.")
    else:
        print("\n❌ Failure! The mock light state was not updated correctly.")

    print("\n" + "=" * 60)
    print("✅ Mock driver demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()