#!/usr/bin/env python3
"""
Simple example demonstrating mock sensory effect devices.
Run this to test the PythonPlaySEM framework without hardware.
"""

import logging
import time
import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.device_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

# Configure logging to see device output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def demo_light_effects():
    """Demonstrate light device effects."""
    print("\n=== Light Effects Demo ===")
    light = MockLightDevice("living_room_light")

    # Brightness control
    light.set_brightness(128)
    time.sleep(0.5)

    # Color changes
    light.set_color(255, 0, 0)  # Red
    time.sleep(0.5)
    light.set_color(0, 255, 0)  # Green
    time.sleep(0.5)
    light.set_color(0, 0, 255)  # Blue
    time.sleep(0.5)

    # Reset
    light.reset()


def demo_wind_effects():
    """Demonstrate wind device effects."""
    print("\n=== Wind Effects Demo ===")
    fan = MockWindDevice("desk_fan")

    # Speed control
    fan.set_speed(25)  # Gentle breeze
    time.sleep(0.5)
    fan.set_speed(75)  # Strong wind
    time.sleep(0.5)

    # Direction
    fan.set_direction("reverse")
    time.sleep(0.5)

    # Reset
    fan.reset()


def demo_vibration_effects():
    """Demonstrate vibration device effects."""
    print("\n=== Vibration Effects Demo ===")
    vibrator = MockVibrationDevice("chair_haptic")

    # Intensity control
    vibrator.set_intensity(50)
    vibrator.set_duration(1000)
    time.sleep(0.5)

    # Stronger vibration
    vibrator.set_intensity(100)
    vibrator.set_duration(500)
    time.sleep(0.5)

    # Reset
    vibrator.reset()


def demo_scent_effects():
    """Demonstrate scent device effects."""
    print("\n=== Scent Effects Demo ===")
    diffuser = MockScentDevice("scent_diffuser")

    # Activate different scents
    diffuser.set_scent("rose", 75)
    time.sleep(0.5)
    diffuser.set_scent("ocean", 50)
    time.sleep(0.5)

    # Stop scent
    diffuser.stop_scent()
    time.sleep(0.5)

    # Reset
    diffuser.reset()


def demo_generic_commands():
    """Demonstrate generic command interface."""
    print("\n=== Generic Command Interface Demo ===")

    light = MockLightDevice("rgb_strip")
    light.send_command("set_brightness", {"brightness": 200})
    light.send_command("set_color", {"r": 255, "g": 128, "b": 0})

    fan = MockWindDevice("ceiling_fan")
    fan.send_command("set_speed", {"speed": 60})

    print(f"\nLight state: {light.get_state()}")
    print(f"Fan state: {fan.get_state()}")


if __name__ == "__main__":
    print("PythonPlaySEM Mock Device Demo")
    print("=" * 50)

    demo_light_effects()
    demo_wind_effects()
    demo_vibration_effects()
    demo_scent_effects()
    demo_generic_commands()

    print("\n" + "=" * 50)
    print("Demo completed successfully!")
    print("\nNext steps:")
    print("  - Check config/devices.yaml for device registry")
    print("  - Check config/effects.yaml for effect mappings")
    print("  - Run 'pytest' to execute unit tests")
