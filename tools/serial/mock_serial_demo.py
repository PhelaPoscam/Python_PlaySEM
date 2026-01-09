"""
Demonstration of the MockConnectivityDriver for testing serial-like interactions.
"""
import sys
from pathlib import Path
import logging
from typing import Dict, Any

# Make 'playsem' importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from playsem.drivers.mock_driver import MockConnectivityDriver, MockDeviceBase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


class MockSerialDevice(MockDeviceBase):
    """
    A mock device that simulates command handling like a serial device
    by updating its internal state with a response dictionary.
    """

    def send_command(self, command: str, params: Dict[str, Any]):
        """Simulates handling a command and updates its internal state."""
        log.info(f"'{self.device_id}' received command '{command}' with params {params}")

        # Let the base class update the state with the params
        super().send_command(command, params)

        # Simulate a response by updating a 'last_response' field in the state
        if command == "PING":
            self.state['last_response'] = {"status": "PONG"}
        elif command == "SET_EFFECT":
            self.state['last_response'] = {"status": "OK", "effect": params.get("name")}
        else:
            self.state['last_response'] = {"status": "ERROR", "message": "Unknown command"}

        log.info(f"'{self.device_id}' updated state with response: {self.state['last_response']}")


def main():
    """Main function to demonstrate using MockConnectivityDriver for testing."""
    print("\n" + "="*60)
    print("🔌 Mock Serial Driver Demo")
    print("="*60 + "\n")

    # 1. Initialize the Mock Driver
    print("1. Initializing MockConnectivityDriver...")
    mock_driver = MockConnectivityDriver(interface_name="mock_serial_bus", data_format="json")
    mock_driver.connect()
    log.info("Mock driver connected.")

    # 2. Create and register a mock device
    print("\n2. Creating and registering a MockSerialDevice with ID 'virtual-serial-01'...")
    mock_device = MockSerialDevice(device_id="virtual-serial-01")
    mock_driver.register_device(device_id="virtual-serial-01", device_obj=mock_device)
    log.info(f"Device '{mock_device.device_id}' registered with the driver.")

    # 3. Send a 'PING' command to the device
    print("\n3. Sending 'PING' command to 'virtual-serial-01'...")
    mock_driver.send_command(device_id="virtual-serial-01", command="PING", params={})

    # 4. Read the "response" from the device's state
    print("\n4. Reading response from the device state...")
    state = mock_device.get_state()
    response = state.get("last_response")

    if response and response.get("status") == "PONG":
        log.info(f"Received response from state: {response}")
        print("   ✅ Success! Received 'PONG' as expected.")
    else:
        log.error(f"Failure! Unexpected response in state: {response}")
        print("   ❌ Failure! Did not receive 'PONG'.")

    # 5. Send a command with parameters
    print("\n5. Sending 'SET_EFFECT' command with parameters...")
    command = "SET_EFFECT"
    params = {"name": "RAINBOW", "speed": 90}
    mock_driver.send_command(device_id="virtual-serial-01", command=command, params=params)

    # 6. Reading response for 'SET_EFFECT'
    print("\n6. Reading response for 'SET_EFFECT'...")
    state = mock_device.get_state()
    response = state.get("last_response")

    if response and response.get("status") == "OK":
        log.info(f"Received response from state: {response}")
        print("   ✅ Success! Received 'OK' status for SET_EFFECT.")
    else:
        log.error(f"Failure! Unexpected response in state: {response}")
        print("   ❌ Failure! Did not receive 'OK' for SET_EFFECT.")

    # 7. Disconnect the driver
    print("\n7. Disconnecting mock driver...")
    mock_driver.disconnect()
    log.info("Mock driver disconnected.")

    print("\n" + "="*60)
    print("✅ Mock serial demo complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
