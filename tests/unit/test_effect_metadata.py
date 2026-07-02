# tests/test_effect_metadata.py

import json
import pytest

from playsem.effect_metadata import (
    EffectMetadata,
    EffectTimeline,
    EffectMetadataParser,
    create_effect,
    create_timeline,
)


def test_effect_metadata_creation():
    effect = EffectMetadata(
        effect_type="light",
        timestamp=1000,
        duration=2000,
        intensity=75,
        location="center",
    )
    assert effect.effect_type == "light"
    assert effect.timestamp == 1000
    assert effect.duration == 2000
    assert effect.intensity == 75
    assert effect.location == "center"


def test_effect_metadata_validation():
    with pytest.raises(ValueError):
        EffectMetadata("light", timestamp=-100)
    with pytest.raises(ValueError):
        EffectMetadata("light", duration=-100)
    with pytest.raises(ValueError):
        EffectMetadata("light", intensity=150)


def test_create_effect_convenience():
    effect = create_effect(
        "wind",
        timestamp=500,
        duration=1500,
        intensity=50,
        parameters={"direction": "forward"},
    )
    assert effect.effect_type == "wind"
    assert effect.timestamp == 500
    assert effect.parameters["direction"] == "forward"


def test_timeline_add_effect():
    timeline = EffectTimeline()
    timeline.add_effect(create_effect("light", timestamp=0, duration=1000))
    timeline.add_effect(create_effect("wind", timestamp=500, duration=1500))
    assert len(timeline.effects) == 2
    assert timeline.total_duration == 2000


def test_timeline_get_effects_at_time():
    timeline = EffectTimeline()
    timeline.add_effect(create_effect("light", timestamp=0, duration=1000))
    timeline.add_effect(create_effect("wind", timestamp=500, duration=1000))
    active = timeline.get_effects_at_time(750)
    assert len(active) == 2
    active = timeline.get_effects_at_time(1500)
    assert len(active) == 0


def test_parse_json():
    effect = EffectMetadataParser.parse_json(
        """
    {
        "effect_type": "vibration",
        "timestamp": 2000,
        "duration": 500,
        "intensity": 80,
        "location": "left"
    }
    """
    )
    assert effect.effect_type == "vibration"
    assert effect.timestamp == 2000
    assert effect.intensity == 80


def test_parse_timeline_json():
    timeline = EffectMetadataParser.parse_timeline_json(
        """
    {
        "metadata": {"title": "Test Scene"},
        "effects": [
            {"effect_type": "light", "timestamp": 0, "duration": 1000},
            {"effect_type": "wind", "timestamp": 500, "duration": 1000}
        ]
    }
    """
    )
    assert len(timeline.effects) == 2
    assert timeline.metadata["title"] == "Test Scene"


def test_to_json():
    effect = create_effect(
        "scent",
        timestamp=1000,
        duration=3000,
        intensity=60,
        parameters={"scent": "rose"},
    )
    parsed = json.loads(EffectMetadataParser.to_json(effect))
    assert parsed["effect_type"] == "scent"
    assert parsed["parameters"]["scent"] == "rose"


def test_create_timeline_convenience():
    timeline = create_timeline(
        create_effect("light", 0, 1000),
        create_effect("wind", 500, 1500),
        title="Action Scene",
        author="Test",
    )
    assert len(timeline.effects) == 2
    assert timeline.metadata["title"] == "Action Scene"
    assert timeline.metadata["author"] == "Test"


class TestMPEGVXml:
    def test_parse_single_effect(self):
        xml = """<SEM>
  <SensoryEffect>
    <Effect type="vibration" timestamp="1000" duration="500"
            intensity="75" location="center"/>
  </SensoryEffect>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert len(tl.effects) == 1
        eff = tl.effects[0]
        assert eff.effect_type == "vibration"
        assert eff.timestamp == 1000
        assert eff.duration == 500
        assert eff.intensity == 75
        assert eff.location == "center"

    def test_parse_multiple_effects(self):
        xml = """<SEM>
  <Effect type="light" timestamp="0" duration="1000" intensity="50"/>
  <Effect type="wind" timestamp="500" duration="2000" intensity="80" direction="forward"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert len(tl.effects) == 2
        assert tl.effects[0].effect_type == "light"
        assert tl.effects[1].effect_type == "wind"
        assert tl.effects[1].parameters["direction"] == "forward"

    def test_parse_with_color(self):
        xml = """<SEM>
  <SensoryEffect type="light" timestamp="100" duration="200" color="#FF0000"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        eff = tl.effects[0]
        assert eff.parameters["color"] == "#FF0000"

    def test_parse_with_rgb(self):
        xml = """<SEM>
  <SensoryEffect type="light" timestamp="0" duration="500" r="255" g="128" b="64"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        eff = tl.effects[0]
        assert eff.parameters["rgb"] == [255, 128, 64]

    def test_parse_with_scent(self):
        xml = """<SEM>
  <SensoryEffect type="scent" timestamp="0" duration="3000" scent="rose" intensity="40"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        eff = tl.effects[0]
        assert eff.parameters["scent"] == "rose"

    def test_parse_with_metadata(self):
        xml = """<SEM title="MyScene">
  <metadata>
    <author>Alice</author>
    <description>Test scene</description>
  </metadata>
  <Effect type="light" timestamp="0" duration="1000"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert tl.metadata["title"] == "MyScene"
        assert tl.metadata["author"] == "Alice"
        assert tl.metadata["description"] == "Test scene"

    def test_parse_root_duration(self):
        xml = """<SEM duration="5000">
  <Effect type="light" timestamp="0" duration="1000"/>
  <Effect type="wind" timestamp="500" duration="1500"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert tl.total_duration == 5000

    def test_parse_lowercase_effect(self):
        xml = """<SEM>
  <effect type="light" timestamp="0" duration="800"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert len(tl.effects) == 1

    def test_parse_nested_effect(self):
        xml = """<SEM>
  <SensoryEffect>
    <Effect type="vibration" timestamp="2000" duration="300"/>
  </SensoryEffect>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert len(tl.effects) == 1
        assert tl.effects[0].effect_type == "vibration"

    def test_parse_temperature(self):
        xml = """<SEM>
  <SensoryEffect type="temperature" timestamp="0" duration="3000"
                 temperature="28" intensity="60"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        eff = tl.effects[0]
        assert eff.parameters["temperature"] == 28

    def test_parse_child_elements(self):
        xml = """<SEM>
  <SensoryEffect>
    <type>wind</type>
    <timestamp>500</timestamp>
    <duration>1200</duration>
    <intensity>70</intensity>
    <location>left</location>
    <direction>right</direction>
  </SensoryEffect>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        eff = tl.effects[0]
        assert eff.effect_type == "wind"
        assert eff.timestamp == 500
        assert eff.duration == 1200
        assert eff.intensity == 70
        assert eff.location == "left"
        assert eff.parameters["direction"] == "right"

    def test_invalid_xml(self):
        with pytest.raises(ValueError, match="Invalid XML"):
            EffectMetadataParser.parse_mpegv_xml("<not><valid>")

    def test_normalize_light_effect(self):
        xml = """<SEM>
  <Effect type="LightEffect" timestamp="0" duration="1000"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert tl.effects[0].effect_type == "light"

    def test_normalize_tactile(self):
        xml = """<SEM>
  <Effect type="TactileEffect" timestamp="0" duration="500"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert tl.effects[0].effect_type == "vibration"

    def test_normalize_olfactory(self):
        xml = """<SEM>
  <Effect type="OlfactoryEffect" timestamp="0" duration="800"/>
</SEM>"""
        tl = EffectMetadataParser.parse_mpegv_xml(xml)
        assert tl.effects[0].effect_type == "scent"

    def test_parse_xml_file(self, tmp_path):
        xml = """<SEM>
  <Effect type="light" timestamp="100" duration="200"/>
</SEM>"""
        p = tmp_path / "scene.xml"
        p.write_text(xml)
        tl = EffectMetadataParser.parse_xml_file(str(p))
        assert len(tl.effects) == 1

    def test_parse_xml_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            EffectMetadataParser.parse_xml_file(str(tmp_path / "nope.xml"))


class TestYaml:
    def test_parse_yaml(self):
        yml = """
effect_type: light
timestamp: 300
duration: 900
intensity: 55
location: right
"""
        eff = EffectMetadataParser.parse_yaml(yml)
        assert eff.effect_type == "light"
        assert eff.timestamp == 300
        assert eff.intensity == 55
        assert eff.location == "right"

    def test_parse_yaml_with_params(self):
        yml = """
effect_type: wind
timestamp: 0
duration: 2000
intensity: 80
parameters:
  direction: forward
  speed: max
"""
        eff = EffectMetadataParser.parse_yaml(yml)
        assert eff.parameters["direction"] == "forward"
        assert eff.parameters["speed"] == "max"

    def test_parse_timeline_yaml(self):
        yml = """
metadata:
  title: Storm Scene
  author: Tester
effects:
  - effect_type: wind
    timestamp: 0
    duration: 5000
    intensity: 90
  - effect_type: light
    timestamp: 1000
    duration: 2000
    intensity: 30
"""
        tl = EffectMetadataParser.parse_timeline_yaml(yml)
        assert len(tl.effects) == 2
        assert tl.metadata["title"] == "Storm Scene"
        assert tl.effects[0].effect_type == "wind"
        assert tl.effects[1].effect_type == "light"

    def test_parse_yaml_output(self):
        eff = create_effect("light", timestamp=100, duration=500, intensity=80)
        d = EffectMetadataParser.to_dict(eff)
        assert d["effect_type"] == "light"
        assert d["timestamp"] == 100


class TestTimelineSerialization:
    def test_parser_to_dict(self):
        eff = create_effect("light", 100, 200, intensity=50)
        d = EffectMetadataParser.to_dict(eff)
        assert d["effect_type"] == "light"
        assert d["timestamp"] == 100

    def test_parser_to_json(self):
        eff = create_effect("vibration", 0, 500)
        js = EffectMetadataParser.to_json(eff)
        assert '"effect_type": "vibration"' in js

    def test_equality(self):
        a = create_effect("light", 100, 200, intensity=50)
        b = create_effect("light", 100, 200, intensity=50)
        assert a == b
        c = create_effect("light", 100, 200, intensity=51)
        assert a != c

    def test_effect_serialization_roundtrip(self):
        original = create_effect(
            "scent",
            timestamp=500,
            duration=2000,
            intensity=50,
            parameters={"scent": "ocean"},
        )
        d = EffectMetadataParser.to_dict(original)
        restored = EffectMetadataParser.parse_dict(d)
        assert restored.effect_type == original.effect_type
        assert restored.timestamp == original.timestamp
        assert restored.parameters["scent"] == "ocean"
