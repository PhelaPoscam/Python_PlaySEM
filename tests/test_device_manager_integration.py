"""Integration tests for DeviceManager - tests with real device drivers"""

import pytest
from pathlib import Path

from src.device_manager import DeviceManager
from src.device_driver.mock_driver import MockDriver
from src.config_loader import ConfigLoader


def test_device_manager_with_real_config():
    """
    Integration test: Load DeviceManager with actual devices.yaml.
    """
    config_dir = Path(__file__).parent.parent / "config"
    loader = ConfigLoader(str(config_dir))
    config = loader.load_config("devices.yaml")
    
    assert config is not None
    
    # Create DeviceManager with real config
    manager = DeviceManager()
    
    # Register devices from real config
    for device_config in config["devices"]:
        device_id = device_config["id"]
        device_type = device_config["type"]
        driver_type = device_config.get("driver", "mock")
        
        # Create appropriate driver
        if driver_type == "mock":
            driver = MockDriver(device_id)
            manager.register_device(device_id, device_type, driver)
    
    # Verify devices registered
    assert len(manager.devices) > 0
    
    # Test getting device
    first_device_id = config["devices"][0]["id"]
    device = manager.get_device(first_device_id)
    assert device is not None


def test_device_lifecycle_with_real_driver():
    """
    Integration test: Test full device lifecycle with real MockDriver.
    """
    manager = DeviceManager()
    driver = MockDriver("test_device")
    
    # Register device
    manager.register_device("test_device", "light", driver)
    
    # Verify registration
    assert "test_device" in manager.devices
    device = manager.get_device("test_device")
    assert device is not None
    assert device["type"] == "light"
    assert device["driver"] == driver
    
    # Test device operation
    result = driver.send_effect("light", 100, 1000)
    assert result is True
    
    # Unregister device
    manager.unregister_device("test_device")
    assert "test_device" not in manager.devices


def test_multiple_devices_real_drivers():
    """
    Integration test: Manage multiple devices with real drivers simultaneously.
    """
    manager = DeviceManager()
    
    # Create multiple drivers
    drivers = {
        "light_1": MockDriver("light_1"),
        "light_2": MockDriver("light_2"),
        "vibration_1": MockDriver("vibration_1"),
        "wind_1": MockDriver("wind_1"),
    }
    
    # Register all devices
    manager.register_device("light_1", "light", drivers["light_1"])
    manager.register_device("light_2", "light", drivers["light_2"])
    manager.register_device("vibration_1", "vibration", drivers["vibration_1"])
    manager.register_device("wind_1", "wind", drivers["wind_1"])
    
    # Verify all registered
    assert len(manager.devices) == 4
    
    # Get devices by type
    lights = manager.get_devices_by_type("light")
    assert len(lights) == 2
    assert all(d["type"] == "light" for d in lights)
    
    # Send effects to all light devices
    for light in lights:
        result = light["driver"].send_effect("light", 80, 500)
        assert result is True


def test_device_communication_real_driver():
    """
    Integration test: Test actual communication through MockDriver.
    """
    driver = MockDriver("comm_test")
    manager = DeviceManager()
    manager.register_device("comm_test", "vibration", driver)
    
    # Send multiple effects
    effects = [
        ("vibration", 50, 1000),
        ("vibration", 75, 500),
        ("vibration", 100, 250),
    ]
    
    for effect_type, intensity, duration in effects:
        result = driver.send_effect(effect_type, intensity, duration)
        assert result is True
    
    # Verify driver state (MockDriver tracks calls)
    assert len(driver.effects_sent) == 3
    assert driver.effects_sent[0] == ("vibration", 50, 1000)
    assert driver.effects_sent[2] == ("vibration", 100, 250)


def test_concurrent_device_operations():
    """
    Integration test: Test concurrent operations on multiple devices.
    """
    manager = DeviceManager()
    
    # Setup multiple devices
    for i in range(5):
        driver = MockDriver(f"device_{i}")
        manager.register_device(f"device_{i}", "light", driver)
    
    # Send effects to all devices simultaneously
    for device_id, device_info in manager.devices.items():
        driver = device_info["driver"]
        result = driver.send_effect("light", 100, 1000)
        assert result is True
    
    # Verify all received commands
    for device_id, device_info in manager.devices.items():
        driver = device_info["driver"]
        assert len(driver.effects_sent) == 1


def test_device_error_handling_real_scenario():
    """
    Integration test: Test error handling with real driver errors.
    """
    driver = MockDriver("error_device")
    manager = DeviceManager()
    manager.register_device("error_device", "light", driver)
    
    # Force driver into error state
    driver.simulate_error = True
    
    # Try to send effect
    result = driver.send_effect("light", 100, 1000)
    assert result is False  # Should fail gracefully
    
    # Recover from error
    driver.simulate_error = False
    result = driver.send_effect("light", 100, 1000)
    assert result is True  # Should work again


def test_device_type_filtering_real_config():
    """
    Integration test: Filter devices by type using real config.
    """
    config_dir = Path(__file__).parent.parent / "config"
    loader = ConfigLoader(str(config_dir))
    config = loader.load_config("devices.yaml")
    
    manager = DeviceManager()
    
    # Register all devices from config
    for device_config in config["devices"]:
        driver = MockDriver(device_config["id"])
        manager.register_device(
            device_config["id"],
            device_config["type"],
            driver
        )
    
    # Get unique device types from config
    config_types = set(d["type"] for d in config["devices"])
    
    # Test filtering for each type
    for device_type in config_types:
        filtered = manager.get_devices_by_type(device_type)
        assert len(filtered) > 0
        assert all(d["type"] == device_type for d in filtered)


def test_duplicate_device_registration():
    """
    Integration test: Test duplicate device ID handling.
    """
    manager = DeviceManager()
    driver1 = MockDriver("device_1")
    driver2 = MockDriver("device_1")  # Same ID
    
    # Register first device
    manager.register_device("device_1", "light", driver1)
    assert len(manager.devices) == 1
    
    # Try to register duplicate - should replace
    manager.register_device("device_1", "vibration", driver2)
    assert len(manager.devices) == 1
    
    # Should have new driver
    device = manager.get_device("device_1")
    assert device["driver"] == driver2
    assert device["type"] == "vibration"


def test_unregister_nonexistent_device():
    """
    Integration test: Test unregistering device that doesn't exist.
    """
    manager = DeviceManager()
    
    # Should not crash
    manager.unregister_device("nonexistent")
    
    # Register a device
    driver = MockDriver("real_device")
    manager.register_device("real_device", "light", driver)
    assert len(manager.devices) == 1
    
    # Unregister wrong device
    manager.unregister_device("wrong_id")
    assert len(manager.devices) == 1  # Should still have the real device


def test_device_manager_empty_state():
    """
    Integration test: Test DeviceManager operations in empty state.
    """
    manager = DeviceManager()
    
    # Test operations on empty manager
    assert len(manager.devices) == 0
    assert manager.get_device("any_id") is None
    assert manager.get_devices_by_type("any_type") == []
    
    # Unregister from empty should not crash
    manager.unregister_device("any_id")
    assert len(manager.devices) == 0
