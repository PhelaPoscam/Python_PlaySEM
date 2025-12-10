# src/effect_metadata.py
"""
Effect metadata parsing and representation.

Supports multiple formats:
- Simple JSON/YAML for basic effects
- MPEG-V XML standard
"""

import json
import yaml
import xml.etree.ElementTree as ET
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
            if (
                effect.timestamp
                <= time_ms
                < (effect.timestamp + effect.duration)
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
            effect_type=data["effect_type"],
            timestamp=data.get("timestamp", 0),
            duration=data.get("duration", 0),
            intensity=data.get("intensity"),
            location=data.get("location", "everywhere"),
            parameters=data.get("parameters", {}),
            event_id=data.get("event_id"),
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
            effect_type=data["effect_type"],
            timestamp=data.get("timestamp", 0),
            duration=data.get("duration", 0),
            intensity=data.get("intensity"),
            location=data.get("location", "everywhere"),
            parameters=data.get("parameters", {}),
            event_id=data.get("event_id"),
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
            effect_type=data["effect_type"],
            timestamp=data.get("timestamp", 0),
            duration=data.get("duration", 0),
            intensity=data.get("intensity"),
            location=data.get("location", "everywhere"),
            parameters=data.get("parameters", {}),
            event_id=data.get("event_id"),
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
        timeline = EffectTimeline(metadata=data.get("metadata", {}))

        for effect_data in data.get("effects", []):
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
        timeline = EffectTimeline(metadata=data.get("metadata", {}))

        for effect_data in data.get("effects", []):
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
            "effect_type": effect.effect_type,
            "timestamp": effect.timestamp,
            "duration": effect.duration,
            "intensity": effect.intensity,
            "location": effect.location,
            "parameters": effect.parameters,
            "event_id": effect.event_id,
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
        return json.dumps(EffectMetadataParser.to_dict(effect), indent=indent)

    @staticmethod
    def parse_mpegv_xml(xml_content: str) -> EffectTimeline:
        """
        Parse MPEG-V XML format into EffectTimeline.

        MPEG-V format example:
        <SEM>
            <SensoryEffect>
                <Effect type="vibration" timestamp="1000" duration="500"
                        intensity="75" location="center"/>
            </SensoryEffect>
        </SEM>

        Args:
            xml_content: XML string in MPEG-V format

        Returns:
            EffectTimeline object with parsed effects
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {e}")

        timeline = EffectTimeline()

        # Try different common root element names
        sensory_effects = (
            root.findall(".//SensoryEffect")
            + root.findall(".//SensoryEffects")
            + root.findall(".//Effect")
            + root.findall(".//effect")
        )

        for se_elem in sensory_effects:
            # Parse effect from element or its children
            effect = EffectMetadataParser._parse_effect_element(se_elem)
            if effect:
                timeline.add_effect(effect)

        # Try to parse metadata from root
        if root.get("title"):
            timeline.metadata["title"] = root.get("title")
        if root.get("duration"):
            try:
                timeline.total_duration = int(root.get("duration"))
            except (ValueError, TypeError):
                pass

        # Parse metadata from separate elements
        metadata_elem = root.find(".//metadata") or root.find(".//Metadata")
        if metadata_elem is not None:
            for child in metadata_elem:
                timeline.metadata[child.tag] = child.text

        timeline.sort_effects()
        return timeline

    @staticmethod
    def _parse_effect_element(elem: ET.Element) -> Optional[EffectMetadata]:
        """
        Parse a single effect element from XML.

        Supports both attribute-based and child-element-based formats.

        Args:
            elem: XML Element representing an effect

        Returns:
            EffectMetadata object or None if parsing fails
        """
        # Try to find effect type
        effect_type = (
            elem.get("type")
            or elem.get("effectType")
            or elem.get("Type")
            or EffectMetadataParser._get_child_text(
                elem, ["type", "Type", "effectType"]
            )
        )

        if not effect_type:
            # Check if element itself contains Effect child
            effect_child = elem.find(".//Effect") or elem.find(".//effect")
            if effect_child is not None:
                return EffectMetadataParser._parse_effect_element(effect_child)
            return None

        # Map common MPEG-V effect types to our types
        effect_type = EffectMetadataParser._normalize_effect_type(effect_type)

        # Parse timestamp (milliseconds)
        timestamp = EffectMetadataParser._parse_int_attr(
            elem, ["timestamp", "Timestamp", "time", "Time"], default=0
        )

        # Parse duration (milliseconds)
        duration = EffectMetadataParser._parse_int_attr(
            elem, ["duration", "Duration"], default=1000
        )

        # Parse intensity (0-100)
        intensity = EffectMetadataParser._parse_int_attr(
            elem,
            ["intensity", "Intensity", "magnitude", "Magnitude"],
            default=None,
        )

        # Parse location
        location = (
            elem.get("location")
            or elem.get("Location")
            or EffectMetadataParser._get_child_text(
                elem, ["location", "Location"]
            )
            or "everywhere"
        )

        # Parse additional parameters
        parameters = {}

        # Color for light effects
        color = (
            elem.get("color")
            or elem.get("Color")
            or EffectMetadataParser._get_child_text(elem, ["color", "Color"])
        )
        if color:
            parameters["color"] = color

        # RGB values for light effects
        r = EffectMetadataParser._parse_int_attr(
            elem, ["r", "R", "red"], default=None
        )
        g = EffectMetadataParser._parse_int_attr(
            elem, ["g", "G", "green"], default=None
        )
        b = EffectMetadataParser._parse_int_attr(
            elem, ["b", "B", "blue"], default=None
        )
        if r is not None and g is not None and b is not None:
            parameters["rgb"] = [r, g, b]

        # Scent information
        scent = (
            elem.get("scent")
            or elem.get("Scent")
            or EffectMetadataParser._get_child_text(elem, ["scent", "Scent"])
        )
        if scent:
            parameters["scent"] = scent

        # Wind direction
        direction = (
            elem.get("direction")
            or elem.get("Direction")
            or EffectMetadataParser._get_child_text(
                elem, ["direction", "Direction"]
            )
        )
        if direction:
            parameters["direction"] = direction

        # Temperature value
        temp = EffectMetadataParser._parse_int_attr(
            elem, ["temperature", "Temperature", "temp"], default=None
        )
        if temp is not None:
            parameters["temperature"] = temp

        return EffectMetadata(
            effect_type=effect_type,
            timestamp=timestamp,
            duration=duration,
            intensity=intensity,
            location=location,
            parameters=parameters,
        )

    @staticmethod
    def _normalize_effect_type(effect_type: str) -> str:
        """Normalize effect type names to match PlaySEM conventions."""
        effect_type_lower = effect_type.lower()

        # Map MPEG-V types to PlaySEM types
        type_map = {
            "lighteffect": "light",
            "windeffect": "wind",
            "vibrationeffect": "vibration",
            "tactileeffect": "vibration",
            "scenteffect": "scent",
            "olfactoryeffect": "scent",
            "temperatureeffect": "temperature",
            "thermaleffect": "temperature",
        }

        return type_map.get(effect_type_lower, effect_type_lower)

    @staticmethod
    def _parse_int_attr(
        elem: ET.Element, attr_names: list, default: Optional[int] = None
    ) -> Optional[int]:
        """Try to parse an integer from element attributes or child elements."""
        for name in attr_names:
            # Try as attribute
            val = elem.get(name)
            if val:
                try:
                    return int(float(val))  # Handle "1000.0" format
                except (ValueError, TypeError):
                    pass

            # Try as child element
            child = (
                elem.find(name)
                or elem.find(name.lower())
                or elem.find(name.upper())
            )
            if child is not None and child.text:
                try:
                    return int(float(child.text))
                except (ValueError, TypeError):
                    pass

        return default

    @staticmethod
    def _get_child_text(elem: ET.Element, tag_names: list) -> Optional[str]:
        """Get text content from child element with various possible tag names."""
        for tag in tag_names:
            child = (
                elem.find(tag)
                or elem.find(tag.lower())
                or elem.find(tag.upper())
            )
            if child is not None and child.text:
                return child.text.strip()
        return None

    @staticmethod
    def parse_xml_file(filepath: str) -> EffectTimeline:
        """
        Parse XML timeline from file.

        Args:
            filepath: Path to XML file

        Returns:
            EffectTimeline object
        """
        with open(filepath, "r", encoding="utf-8") as f:
            xml_content = f.read()

        return EffectMetadataParser.parse_mpegv_xml(xml_content)


# Convenience functions for common use cases
def create_effect(
    effect_type: str, timestamp: int = 0, duration: int = 0, **kwargs
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
        intensity=kwargs.get("intensity"),
        location=kwargs.get("location", "everywhere"),
        parameters=kwargs.get("parameters", {}),
        event_id=kwargs.get("event_id"),
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
