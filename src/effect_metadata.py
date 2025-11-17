# src/effect_metadata.py
"""
Effect metadata parsing and representation.

Supports multiple formats:
- Simple JSON/YAML for basic effects
- MPEG-V XML standard (future implementation)
"""

import json
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class EffectMetadata:
    """
    Represents a sensory effect with timing and parameters.

    Attributes:
        effect_type: Type of effect (light, wind, vibration, scent)
        timestamp: When effect should occur (milliseconds from start)
        duration: How long effect should last (milliseconds)
        intensity: Effect intensity (0-100 or specific value)
        location: Spatial location (left, right, center, everywhere, etc.)
        parameters: Additional effect-specific parameters
        event_id: Optional event identifier for event-based triggering
    """
    effect_type: str
    timestamp: int = 0  # milliseconds
    duration: int = 0  # milliseconds
    intensity: Optional[int] = None
    location: str = "everywhere"
    parameters: Dict[str, Any] = field(default_factory=dict)
    event_id: Optional[int] = None

    def __post_init__(self):
        """Validate effect metadata after initialization."""
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if self.intensity is not None:
            if not (0 <= self.intensity <= 100):
                raise ValueError("intensity must be between 0 and 100")


@dataclass
class EffectTimeline:
    """
    Represents a timeline of multiple effects.

    Attributes:
        effects: List of EffectMetadata objects
        total_duration: Total timeline duration in milliseconds
        metadata: Additional timeline metadata (title, author, etc.)
    """
    effects: List[EffectMetadata] = field(default_factory=list)
    total_duration: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_effect(self, effect: EffectMetadata):
        """Add an effect to the timeline."""
        self.effects.append(effect)
        # Update total duration if this effect extends timeline
        effect_end = effect.timestamp + effect.duration
        if effect_end > self.total_duration:
            self.total_duration = effect_end

    def get_effects_at_time(self, time_ms: int) -> List[EffectMetadata]:
        """
        Get all effects that should be active at a given time.

        Args:
            time_ms: Time in milliseconds from timeline start

        Returns:
            List of active effects at the given time
        """
        active = []
        for effect in self.effects:
            if effect.timestamp <= time_ms < (
                effect.timestamp + effect.duration
            ):
                active.append(effect)
        return active

    def sort_effects(self):
        """Sort effects by timestamp (earliest first)."""
        self.effects.sort(key=lambda e: e.timestamp)


class EffectMetadataParser:
    """Parser for effect metadata in various formats."""

    @staticmethod
    def parse_json(json_str: str) -> EffectMetadata:
        """
        Parse effect metadata from JSON string.

        Args:
            json_str: JSON string containing effect data

        Returns:
            EffectMetadata object

        Example JSON:
            {
                "effect_type": "light",
                "timestamp": 1000,
                "duration": 2000,
                "intensity": 75,
                "location": "center",
                "parameters": {"color": "#FF0000"}
            }
        """
        data = json.loads(json_str)
        return EffectMetadata(
            effect_type=data['effect_type'],
            timestamp=data.get('timestamp', 0),
            duration=data.get('duration', 0),
            intensity=data.get('intensity'),
            location=data.get('location', 'everywhere'),
            parameters=data.get('parameters', {}),
            event_id=data.get('event_id')
        )

    @staticmethod
    def parse_yaml(yaml_str: str) -> EffectMetadata:
        """
        Parse effect metadata from YAML string.

        Args:
            yaml_str: YAML string containing effect data

        Returns:
            EffectMetadata object
        """
        data = yaml.safe_load(yaml_str)
        return EffectMetadata(
            effect_type=data['effect_type'],
            timestamp=data.get('timestamp', 0),
            duration=data.get('duration', 0),
            intensity=data.get('intensity'),
            location=data.get('location', 'everywhere'),
            parameters=data.get('parameters', {}),
            event_id=data.get('event_id')
        )

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> EffectMetadata:
        """
        Parse effect metadata from dictionary.

        Args:
            data: Dictionary containing effect data

        Returns:
            EffectMetadata object
        """
        return EffectMetadata(
            effect_type=data['effect_type'],
            timestamp=data.get('timestamp', 0),
            duration=data.get('duration', 0),
            intensity=data.get('intensity'),
            location=data.get('location', 'everywhere'),
            parameters=data.get('parameters', {}),
            event_id=data.get('event_id')
        )

    @staticmethod
    def parse_timeline_json(json_str: str) -> EffectTimeline:
        """
        Parse timeline with multiple effects from JSON.

        Args:
            json_str: JSON string containing timeline data

        Returns:
            EffectTimeline object

        Example JSON:
            {
                "metadata": {"title": "Action Scene", "fps": 30},
                "effects": [
                    {"effect_type": "light", "timestamp": 0, ...},
                    {"effect_type": "wind", "timestamp": 1000, ...}
                ]
            }
        """
        data = json.loads(json_str)
        timeline = EffectTimeline(
            metadata=data.get('metadata', {})
        )

        for effect_data in data.get('effects', []):
            effect = EffectMetadataParser.parse_dict(effect_data)
            timeline.add_effect(effect)

        timeline.sort_effects()
        return timeline

    @staticmethod
    def parse_timeline_yaml(yaml_str: str) -> EffectTimeline:
        """
        Parse timeline with multiple effects from YAML.

        Args:
            yaml_str: YAML string containing timeline data

        Returns:
            EffectTimeline object
        """
        data = yaml.safe_load(yaml_str)
        timeline = EffectTimeline(
            metadata=data.get('metadata', {})
        )

        for effect_data in data.get('effects', []):
            effect = EffectMetadataParser.parse_dict(effect_data)
            timeline.add_effect(effect)

        timeline.sort_effects()
        return timeline

    @staticmethod
    def to_dict(effect: EffectMetadata) -> Dict[str, Any]:
        """
        Convert EffectMetadata to dictionary.

        Args:
            effect: EffectMetadata object

        Returns:
            Dictionary representation
        """
        return {
            'effect_type': effect.effect_type,
            'timestamp': effect.timestamp,
            'duration': effect.duration,
            'intensity': effect.intensity,
            'location': effect.location,
            'parameters': effect.parameters,
            'event_id': effect.event_id
        }

    @staticmethod
    def to_json(effect: EffectMetadata, indent: int = 2) -> str:
        """
        Convert EffectMetadata to JSON string.

        Args:
            effect: EffectMetadata object
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(
            EffectMetadataParser.to_dict(effect),
            indent=indent
        )


# Convenience functions for common use cases
def create_effect(
    effect_type: str,
    timestamp: int = 0,
    duration: int = 0,
    **kwargs
) -> EffectMetadata:
    """
    Create an EffectMetadata object with convenience syntax.

    Args:
        effect_type: Type of effect
        timestamp: When effect occurs (ms)
        duration: How long effect lasts (ms)
        **kwargs: Additional parameters (intensity, location, parameters)

    Returns:
        EffectMetadata object

    Example:
        effect = create_effect(
            'light',
            timestamp=1000,
            duration=2000,
            intensity=75,
            parameters={'color': '#FF0000'}
        )
    """
    return EffectMetadata(
        effect_type=effect_type,
        timestamp=timestamp,
        duration=duration,
        intensity=kwargs.get('intensity'),
        location=kwargs.get('location', 'everywhere'),
        parameters=kwargs.get('parameters', {}),
        event_id=kwargs.get('event_id')
    )


def create_timeline(*effects: EffectMetadata, **metadata) -> EffectTimeline:
    """
    Create an EffectTimeline with convenience syntax.

    Args:
        *effects: Variable number of EffectMetadata objects
        **metadata: Timeline metadata (title, author, etc.)

    Returns:
        EffectTimeline object

    Example:
        timeline = create_timeline(
            create_effect('light', 0, 1000),
            create_effect('wind', 500, 1500),
            title='Action Scene'
        )
    """
    timeline = EffectTimeline(metadata=metadata)
    for effect in effects:
        timeline.add_effect(effect)
    timeline.sort_effects()
    return timeline
