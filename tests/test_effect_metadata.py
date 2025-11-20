# tests/test_effect_metadata.py

import pytest
import json
from src.effect_metadata import (
    EffectMetadata,
    EffectTimeline,
    EffectMetadataParser,
    create_effect,
    create_timeline,
)


def test_effect_metadata_creation():
    """Test creating EffectMetadata object."""
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
    """Test EffectMetadata validation."""
    with pytest.raises(ValueError):
        EffectMetadata("light", timestamp=-100)

    with pytest.raises(ValueError):
        EffectMetadata("light", duration=-100)

    with pytest.raises(ValueError):
        EffectMetadata("light", intensity=150)


def test_create_effect_convenience():
    """Test convenience function for creating effects."""
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
    """Test adding effects to timeline."""
    timeline = EffectTimeline()

    effect1 = create_effect("light", timestamp=0, duration=1000)
    effect2 = create_effect("wind", timestamp=500, duration=1500)

    timeline.add_effect(effect1)
    timeline.add_effect(effect2)

    assert len(timeline.effects) == 2
    assert timeline.total_duration == 2000  # 500 + 1500


def test_timeline_get_effects_at_time():
    """Test getting effects active at specific time."""
    timeline = EffectTimeline()

    timeline.add_effect(create_effect("light", timestamp=0, duration=1000))
    timeline.add_effect(create_effect("wind", timestamp=500, duration=1000))

    # At 750ms, both effects should be active
    active = timeline.get_effects_at_time(750)
    assert len(active) == 2

    # At 1500ms, only wind should be active
    active = timeline.get_effects_at_time(1500)
    assert len(active) == 0


def test_parse_json():
    """Test parsing effect from JSON."""
    json_str = """
    {
        "effect_type": "vibration",
        "timestamp": 2000,
        "duration": 500,
        "intensity": 80,
        "location": "left"
    }
    """

    effect = EffectMetadataParser.parse_json(json_str)
    assert effect.effect_type == "vibration"
    assert effect.timestamp == 2000
    assert effect.intensity == 80


def test_parse_timeline_json():
    """Test parsing timeline from JSON."""
    json_str = """
    {
        "metadata": {"title": "Test Scene"},
        "effects": [
            {
                "effect_type": "light",
                "timestamp": 0,
                "duration": 1000
            },
            {
                "effect_type": "wind",
                "timestamp": 500,
                "duration": 1000
            }
        ]
    }
    """

    timeline = EffectMetadataParser.parse_timeline_json(json_str)
    assert len(timeline.effects) == 2
    assert timeline.metadata["title"] == "Test Scene"


def test_to_json():
    """Test converting effect to JSON."""
    effect = create_effect(
        "scent",
        timestamp=1000,
        duration=3000,
        intensity=60,
        parameters={"scent": "rose"},
    )

    json_str = EffectMetadataParser.to_json(effect)
    parsed = json.loads(json_str)

    assert parsed["effect_type"] == "scent"
    assert parsed["parameters"]["scent"] == "rose"


def test_create_timeline_convenience():
    """Test convenience function for creating timelines."""
    timeline = create_timeline(
        create_effect("light", 0, 1000),
        create_effect("wind", 500, 1500),
        title="Action Scene",
        author="Test",
    )

    assert len(timeline.effects) == 2
    assert timeline.metadata["title"] == "Action Scene"
    assert timeline.metadata["author"] == "Test"
