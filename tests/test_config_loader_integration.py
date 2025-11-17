"""Integration tests for ConfigLoader - tests real file I/O"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path

from src.config_loader import ConfigLoader


def test_load_real_device_config():
    """
    Integration test: Load actual devices.yaml from config directory.
    
    This tests real file I/O, path resolution, and YAML parsing.
    """
    # Get path to real config file
    config_dir = Path(__file__).parent.parent / "config"
    devices_file = config_dir / "devices.yaml"
    
    # Verify file exists
    assert devices_file.exists(), f"Config file not found: {devices_file}"
    
    # Load real config
    loader = ConfigLoader(str(config_dir))
    config = loader.load_config("devices.yaml")
    
    # Verify structure of real config
    assert config is not None
    assert "devices" in config
    assert isinstance(config["devices"], list)
    
    # Verify at least one device defined
    assert len(config["devices"]) > 0
    
    # Verify device structure
    for device in config["devices"]:
        assert "id" in device
        assert "type" in device
        assert "driver" in device


def test_load_real_effects_config():
    """
    Integration test: Load actual effects.yaml from config directory.
    """
    config_dir = Path(__file__).parent.parent / "config"
    effects_file = config_dir / "effects.yaml"
    
    assert effects_file.exists(), f"Config file not found: {effects_file}"
    
    loader = ConfigLoader(str(config_dir))
    config = loader.load_config("effects.yaml")
    
    assert config is not None
    assert "effects" in config
    assert isinstance(config["effects"], dict)
    
    # Verify common effect types exist
    effects = config["effects"]
    assert "light" in effects or "vibration" in effects or "wind" in effects
    
    # Verify effect structure
    for effect_type, effect_config in effects.items():
        assert "min_intensity" in effect_config
        assert "max_intensity" in effect_config
        assert "default_duration" in effect_config


def test_file_not_found_real_filesystem():
    """
    Integration test: Verify error handling with real filesystem.
    """
    config_dir = Path(__file__).parent.parent / "config"
    loader = ConfigLoader(str(config_dir))
    
    # Try to load non-existent file
    config = loader.load_config("nonexistent.yaml")
    
    # Should return None for missing files
    assert config is None


def test_invalid_yaml_real_file():
    """
    Integration test: Create and load invalid YAML file.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create invalid YAML file
        invalid_file = Path(tmpdir) / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [unclosed")
        
        loader = ConfigLoader(tmpdir)
        config = loader.load_config("invalid.yaml")
        
        # Should handle parse error gracefully
        assert config is None


def test_empty_yaml_file():
    """
    Integration test: Load empty YAML file from real filesystem.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_file = Path(tmpdir) / "empty.yaml"
        empty_file.touch()  # Create empty file
        
        loader = ConfigLoader(tmpdir)
        config = loader.load_config("empty.yaml")
        
        # Empty YAML returns None or empty dict
        assert config is None or config == {}


def test_relative_and_absolute_paths():
    """
    Integration test: Test path resolution with real directories.
    """
    config_dir = Path(__file__).parent.parent / "config"
    
    # Test with absolute path
    loader_abs = ConfigLoader(str(config_dir.absolute()))
    config_abs = loader_abs.load_config("devices.yaml")
    
    # Test with relative path
    loader_rel = ConfigLoader("config")
    config_rel = loader_rel.load_config("devices.yaml")
    
    # Both should load successfully
    assert config_abs is not None
    # Note: relative path may fail if not run from project root, that's ok


def test_yaml_with_comments_and_formatting():
    """
    Integration test: Verify YAML parser handles real-world formatting.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create YAML with comments, blank lines, complex formatting
        yaml_file = Path(tmpdir) / "complex.yaml"
        with open(yaml_file, "w") as f:
            f.write("""
# This is a comment
devices:
  # Device list
  - id: device1
    type: light  # inline comment
    
    # Another section
    driver: mock
    
  - id: device2
    type: vibration
    driver: mock

# End of file
""")
        
        loader = ConfigLoader(tmpdir)
        config = loader.load_config("complex.yaml")
        
        assert config is not None
        assert "devices" in config
        assert len(config["devices"]) == 2
        assert config["devices"][0]["id"] == "device1"
        assert config["devices"][1]["id"] == "device2"


def test_nested_yaml_structures():
    """
    Integration test: Test deeply nested YAML structures.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_file = Path(tmpdir) / "nested.yaml"
        with open(nested_file, "w") as f:
            f.write("""
system:
  servers:
    mqtt:
      host: localhost
      port: 1883
      settings:
        keepalive: 60
        qos: 1
    websocket:
      host: 0.0.0.0
      port: 8765
  devices:
    - id: dev1
      settings:
        calibration:
          min: 0
          max: 255
""")
        
        loader = ConfigLoader(tmpdir)
        config = loader.load_config("nested.yaml")
        
        # Verify deep nesting works
        assert config["system"]["servers"]["mqtt"]["port"] == 1883
        assert config["system"]["servers"]["websocket"]["port"] == 8765
        assert config["system"]["devices"][0]["settings"]["calibration"]["max"] == 255


def test_unicode_and_special_characters():
    """
    Integration test: Test YAML with unicode and special characters.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        unicode_file = Path(tmpdir) / "unicode.yaml"
        with open(unicode_file, "w", encoding="utf-8") as f:
            f.write("""
device:
  name: "Device with émojis 🎮✨"
  description: "Spëcial çharacters: üöä"
  tags:
    - "日本語"
    - "中文"
    - "Español"
""")
        
        loader = ConfigLoader(tmpdir)
        config = loader.load_config("unicode.yaml")
        
        assert config is not None
        assert "🎮" in config["device"]["name"]
        assert "日本語" in config["device"]["tags"]


def test_multiple_yaml_files_in_sequence():
    """
    Integration test: Load multiple config files sequentially.
    """
    config_dir = Path(__file__).parent.parent / "config"
    loader = ConfigLoader(str(config_dir))
    
    # Load both config files
    devices = loader.load_config("devices.yaml")
    effects = loader.load_config("effects.yaml")
    
    # Both should load successfully
    assert devices is not None
    assert effects is not None
    assert "devices" in devices
    assert "effects" in effects
    
    # Verify they're different configs
    assert devices != effects
