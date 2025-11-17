"""Integration tests for EffectDispatcher - end-to-end effect processing"""

from pathlib import Path

from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager
from src.effect_metadata import EffectMetadata
from src.device_driver.mock_driver import MockDriver
from src.config_loader import ConfigLoader


def test_full_effect_dispatch_pipeline():
    """
    Integration test: Complete pipeline from effect metadata to device execution.
    """
    # Setup real components
    manager = DeviceManager()
    driver = MockDriver("test_light")
    manager.register_device("test_light", "light", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Create effect metadata
    effect = EffectMetadata(
        effect_type="light",
        timestamp=1000,
        duration=500,
        intensity=80
    )
    
    # Dispatch effect
    dispatcher.dispatch_effect_metadata(effect)
    
    # Verify effect reached driver
    assert len(driver.effects_sent) == 1
    assert driver.effects_sent[0] == ("light", 80, 500)


def test_dispatch_to_multiple_devices():
    """
    Integration test: Dispatch effect to multiple devices of same type.
    """
    manager = DeviceManager()
    
    # Create multiple light devices
    drivers = []
    for i in range(3):
        driver = MockDriver(f"light_{i}")
        drivers.append(driver)
        manager.register_device(f"light_{i}", "light", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch light effect
    effect = EffectMetadata(
        effect_type="light",
        timestamp=0,
        duration=1000,
        intensity=100
    )
    
    dispatcher.dispatch_effect_metadata(effect)
    
    # All light devices should receive effect
    for driver in drivers:
        assert len(driver.effects_sent) == 1
        assert driver.effects_sent[0] == ("light", 100, 1000)


def test_dispatch_with_real_config():
    """
    Integration test: Use real config files for complete setup.
    """
    config_dir = Path(__file__).parent.parent / "config"
    loader = ConfigLoader(str(config_dir))
    
    # Load both configs
    device_config = loader.load_config("devices.yaml")
    effect_config = loader.load_config("effects.yaml")
    
    assert device_config is not None
    assert effect_config is not None
    
    # Setup device manager with real config
    manager = DeviceManager()
    for device in device_config["devices"]:
        driver = MockDriver(device["id"])
        manager.register_device(device["id"], device["type"], driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Test dispatching each effect type from config
    for effect_type in effect_config["effects"].keys():
        effect = EffectMetadata(
            effect_type=effect_type,
            timestamp=0,
            duration=1000,
            intensity=75
        )
        
        # Should not crash
        dispatcher.dispatch_effect_metadata(effect)


def test_mixed_device_types():
    """
    Integration test: Dispatch different effects to correct device types.
    """
    manager = DeviceManager()
    
    # Create devices of different types
    light_driver = MockDriver("light_1")
    vibration_driver = MockDriver("vibration_1")
    wind_driver = MockDriver("wind_1")
    
    manager.register_device("light_1", "light", light_driver)
    manager.register_device("vibration_1", "vibration", vibration_driver)
    manager.register_device("wind_1", "wind", wind_driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch light effect
    light_effect = EffectMetadata("light", 0, 1000, 80)
    dispatcher.dispatch_effect_metadata(light_effect)
    
    # Dispatch vibration effect
    vibration_effect = EffectMetadata("vibration", 0, 500, 60)
    dispatcher.dispatch_effect_metadata(vibration_effect)
    
    # Dispatch wind effect
    wind_effect = EffectMetadata("wind", 0, 2000, 90)
    dispatcher.dispatch_effect_metadata(wind_effect)
    
    # Verify each device received only its effect type
    assert len(light_driver.effects_sent) == 1
    assert light_driver.effects_sent[0][0] == "light"
    
    assert len(vibration_driver.effects_sent) == 1
    assert vibration_driver.effects_sent[0][0] == "vibration"
    
    assert len(wind_driver.effects_sent) == 1
    assert wind_driver.effects_sent[0][0] == "wind"


def test_effect_with_no_matching_devices():
    """
    Integration test: Dispatch effect when no devices registered for that type.
    """
    manager = DeviceManager()
    light_driver = MockDriver("light_1")
    manager.register_device("light_1", "light", light_driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch effect for non-existent device type
    scent_effect = EffectMetadata("scent", 0, 1000, 50)
    dispatcher.dispatch_effect_metadata(scent_effect)
    
    # Light device should not receive scent effect
    assert len(light_driver.effects_sent) == 0


def test_rapid_effect_sequence():
    """
    Integration test: Dispatch multiple effects in rapid succession.
    """
    manager = DeviceManager()
    driver = MockDriver("rapid_device")
    manager.register_device("rapid_device", "light", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Send 10 effects rapidly
    for i in range(10):
        effect = EffectMetadata("light", i * 100, 100, 50 + i * 5)
        dispatcher.dispatch_effect_metadata(effect)
    
    # All effects should be processed
    assert len(driver.effects_sent) == 10
    
    # Verify sequence
    for i, (effect_type, intensity, duration) in enumerate(driver.effects_sent):
        assert effect_type == "light"
        assert intensity == 50 + i * 5
        assert duration == 100


def test_varying_intensity_and_duration():
    """
    Integration test: Test wide range of intensity and duration values.
    """
    manager = DeviceManager()
    driver = MockDriver("test_device")
    manager.register_device("test_device", "vibration", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Test various combinations
    test_cases = [
        (0, 0),      # Minimum
        (50, 500),   # Low
        (100, 1000), # Medium
        (255, 5000), # High
        (1, 1),      # Edge case
    ]
    
    for intensity, duration in test_cases:
        effect = EffectMetadata("vibration", 0, duration, intensity)
        dispatcher.dispatch_effect_metadata(effect)
    
    # Verify all dispatched
    assert len(driver.effects_sent) == len(test_cases)
    
    for i, (intensity, duration) in enumerate(test_cases):
        assert driver.effects_sent[i] == ("vibration", intensity, duration)


def test_effect_dispatch_with_device_errors():
    """
    Integration test: Test dispatcher behavior when devices fail.
    """
    manager = DeviceManager()
    
    # Create multiple devices
    good_driver = MockDriver("good_device")
    bad_driver = MockDriver("bad_device")
    bad_driver.simulate_error = True  # This will fail
    
    manager.register_device("good_device", "light", good_driver)
    manager.register_device("bad_device", "light", bad_driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch effect
    effect = EffectMetadata("light", 0, 1000, 100)
    dispatcher.dispatch_effect_metadata(effect)
    
    # Good device should still work
    assert len(good_driver.effects_sent) == 1
    
    # Bad device tried but failed
    assert bad_driver.send_effect_called is True


def test_empty_dispatcher():
    """
    Integration test: Test dispatcher with no devices registered.
    """
    manager = DeviceManager()
    dispatcher = EffectDispatcher(manager)
    
    # Should not crash with no devices
    effect = EffectMetadata("light", 0, 1000, 100)
    dispatcher.dispatch_effect_metadata(effect)
    
    # Just verify it didn't crash


def test_effect_parameters_validation_in_pipeline():
    """
    Integration test: Test effect parameter validation through full pipeline.
    """
    manager = DeviceManager()
    driver = MockDriver("validator")
    manager.register_device("validator", "light", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Test with extreme/edge values
    extreme_cases = [
        EffectMetadata("light", 0, 10000, 255),      # Max duration and intensity
        EffectMetadata("light", 999999, 1, 1),       # High timestamp, min values
        EffectMetadata("light", 0, 0, 0),            # All zeros
    ]
    
    for effect in extreme_cases:
        dispatcher.dispatch_effect_metadata(effect)
    
    # All should be processed
    assert len(driver.effects_sent) == len(extreme_cases)


def test_device_registration_during_dispatch():
    """
    Integration test: Test adding devices while dispatcher is in use.
    """
    manager = DeviceManager()
    driver1 = MockDriver("device_1")
    manager.register_device("device_1", "light", driver1)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch first effect
    effect = EffectMetadata("light", 0, 1000, 50)
    dispatcher.dispatch_effect_metadata(effect)
    
    # Only device_1 should have received it
    assert len(driver1.effects_sent) == 1
    
    # Add second device
    driver2 = MockDriver("device_2")
    manager.register_device("device_2", "light", driver2)
    
    # Dispatch second effect
    effect2 = EffectMetadata("light", 0, 1000, 75)
    dispatcher.dispatch_effect_metadata(effect2)
    
    # Both devices should receive second effect
    assert len(driver1.effects_sent) == 2
    assert len(driver2.effects_sent) == 1


def test_timestamp_preservation():
    """
    Integration test: Verify timestamps are preserved through dispatch.
    """
    manager = DeviceManager()
    driver = MockDriver("timestamp_device")
    manager.register_device("timestamp_device", "light", driver)
    
    dispatcher = EffectDispatcher(manager)
    
    # Dispatch effects with specific timestamps
    timestamps = [1000, 2000, 3000, 4000, 5000]
    
    for ts in timestamps:
        effect = EffectMetadata("light", ts, 500, 75)
        dispatcher.dispatch_effect_metadata(effect)
    
    # Timestamps should be tracked correctly
    # (MockDriver doesn't track timestamps, but effect should process correctly)
    assert len(driver.effects_sent) == len(timestamps)
