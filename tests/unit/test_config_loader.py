# tests/test_config_loader.py

import json
import pytest

from playsem.config.loader import ConfigLoader


class TestConfigLoader:
    @pytest.fixture
    def cfg_dir(self, tmp_path):
        devices = tmp_path / "devices.yaml"
        devices.write_text(
            "devices:\n  - id: d1\n    deviceClass: MockLight\n    connectivityInterface: mock\n"
        )
        effects = tmp_path / "effects.yaml"
        effects.write_text("vibration:\n  device: v1\n  command: set_intensity\n")
        protocols = tmp_path / "protocols.yaml"
        protocols.write_text("mqtt:\n  enabled: true\n")
        return str(devices), str(effects), str(protocols)

    def test_loads_yaml_configs(self, cfg_dir):
        loader = ConfigLoader(*cfg_dir)
        assert loader.devices_config["devices"][0]["id"] == "d1"
        assert loader.effects_config["vibration"]["command"] == "set_intensity"
        assert loader.protocols_config["mqtt"]["enabled"] is True

    def test_loads_json(self, tmp_path):
        d = tmp_path / "d.json"
        d.write_text(json.dumps({"key": "val"}))
        e = tmp_path / "e.yaml"
        e.write_text("effects: {}")
        p = tmp_path / "p.yaml"
        p.write_text("protocols: {}")
        loader = ConfigLoader(str(d), str(e), str(p))
        assert loader.devices_config == {"key": "val"}

    def test_playsem_xml_transform(self, tmp_path):
        xml = """<configuration>
  <devices>
    <device><id>d1</id><deviceClass>com.thing.LightDevice</deviceClass><connectivityInterface>MQTT</connectivityInterface></device>
    <device><id>d2</id><deviceClass>com.thing.WindDevice</deviceClass><connectivityInterface>SERIAL</connectivityInterface></device>
  </devices>
  <connectivityInterfaces>
    <connectivityInterface><id>MQTT</id><properties><broker>localhost</broker></properties></connectivityInterface>
    <connectivityInterface><id>SERIAL</id><properties><serialPort>COM5</serialPort><baudRate>115200</baudRate></properties></connectivityInterface>
  </connectivityInterfaces>
</configuration>"""
        d = tmp_path / "d.xml"
        d.write_text(xml)
        e = tmp_path / "e.yaml"
        e.write_text("effects: {}")
        p = tmp_path / "p.yaml"
        p.write_text("protocols: {}")
        loader = ConfigLoader(str(d), str(e), str(p))
        devs = loader.devices_config["devices"]
        assert len(devs) == 2
        assert devs[0]["deviceClass"] == "Light"
        assert devs[1]["deviceClass"] == "Fan"
        ifaces = loader.devices_config["connectivityInterfaces"]
        assert ifaces[1]["port"] == "COM5"
        assert ifaces[1]["baudrate"] == 115200

    def test_xml_transform_single_device(self, tmp_path):
        xml = """<configuration>
  <devices>
    <device><id>d1</id><deviceClass>com.MockDevice</deviceClass><connectivityInterface>MQTT</connectivityInterface></device>
  </devices>
  <connectivityInterfaces>
    <connectivityInterface><id>MQTT</id></connectivityInterface>
  </connectivityInterfaces>
</configuration>"""
        d = tmp_path / "d.xml"
        d.write_text(xml)
        e = tmp_path / "e.yaml"
        e.write_text("{}")
        p = tmp_path / "p.yaml"
        p.write_text("{}")
        loader = ConfigLoader(str(d), str(e), str(p))
        assert len(loader.devices_config["devices"]) == 1

    def test_map_java_class_wind(self, tmp_path):
        xml = """<configuration>
  <devices>
    <device><id>w1</id><deviceClass>com.foo.wind.v2.WindDevice</deviceClass><connectivityInterface>MQTT</connectivityInterface></device>
  </devices>
  <connectivityInterfaces>
    <connectivityInterface><id>MQTT</id></connectivityInterface>
  </connectivityInterfaces>
</configuration>"""
        d = tmp_path / "d.xml"
        d.write_text(xml)
        e = tmp_path / "e.yaml"
        e.write_text("{}")
        p = tmp_path / "p.yaml"
        p.write_text("{}")
        loader = ConfigLoader(str(d), str(e), str(p))
        assert loader.devices_config["devices"][0]["deviceClass"] == "Fan"

    def test_map_java_class_scent(self, tmp_path):
        xml = """<configuration>
  <devices>
    <device><id>s1</id><deviceClass>com.scent.ScentDevice</deviceClass><connectivityInterface>MQTT</connectivityInterface></device>
  </devices>
  <connectivityInterfaces>
    <connectivityInterface><id>MQTT</id></connectivityInterface>
  </connectivityInterfaces>
</configuration>"""
        d = tmp_path / "d.xml"
        d.write_text(xml)
        e = tmp_path / "e.yaml"
        e.write_text("{}")
        p = tmp_path / "p.yaml"
        p.write_text("{}")
        loader = ConfigLoader(str(d), str(e), str(p))
        assert loader.devices_config["devices"][0]["deviceClass"] == "Scent"

    def test_map_java_class_fallback(self, tmp_path):
        xml = """<configuration>
  <devices>
    <device><id>u1</id><deviceClass>com.unknown.Xyz</deviceClass><connectivityInterface>MQTT</connectivityInterface></device>
  </devices>
  <connectivityInterfaces>
    <connectivityInterface><id>MQTT</id></connectivityInterface>
  </connectivityInterfaces>
</configuration>"""
        d = tmp_path / "d.xml"
        d.write_text(xml)
        e = tmp_path / "e.yaml"
        e.write_text("{}")
        p = tmp_path / "p.yaml"
        p.write_text("{}")
        loader = ConfigLoader(str(d), str(e), str(p))
        assert loader.devices_config["devices"][0]["deviceClass"] == "GenericDevice"

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ConfigLoader(
                str(tmp_path / "nope.yaml"),
                str(tmp_path / "e.yaml"),
                str(tmp_path / "p.yaml"),
            )

    def test_unsupported_format(self, tmp_path):
        d = tmp_path / "d.txt"
        d.write_text("hello")
        e = tmp_path / "e.yaml"
        e.write_text("{}")
        p = tmp_path / "p.yaml"
        p.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported"):
            ConfigLoader(str(d), str(e), str(p))
