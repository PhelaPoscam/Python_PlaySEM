#!/usr/bin/env python3
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import xml.etree.ElementTree as ET

from playsem.utils.serializer import (
    serialize_to_json,
    serialize_to_xml,
    serialize_device_command,
    _sanitize_xml_tag
)

def test_json_custom_encoder_fallback():
    data = {
        "timestamp": datetime(2026, 5, 20, 10, 0, 0),
        "price": Decimal("19.99"),
        "id": UUID("12345678-1234-5678-1234-567812345678"),
        "raw_bytes": b"\x01\x02\x03",
        "unique_vals": {1, 2, 3}
    }
    
    json_str = serialize_to_json(data)
    assert '"timestamp": "2026-05-20T10:00:00"' in json_str
    assert '"price": 19.99' in json_str
    assert '"id": "12345678-1234-5678-1234-567812345678"' in json_str
    assert '"raw_bytes": "010203"' in json_str
    
    # Parse back to list for order-independent set check
    import json
    parsed = json.loads(json_str)
    assert sorted(parsed["unique_vals"]) == [1, 2, 3]

def test_xml_escaping_and_sanitization():
    # Test sanitizing invalid tag names
    assert _sanitize_xml_tag("valid-tag_name.1") == "valid-tag_name.1"
    assert _sanitize_xml_tag("invalid tag name & core") == "invalid_tag_name___core"
    assert _sanitize_xml_tag("123starts-with-number") == "_123starts-with-number"

    # Test proper escaping of special XML characters in values
    data = {
        "msg": "Hello <world> & friends",
        "nested": {
            "invalid name": "value"
        }
    }
    xml_str = serialize_to_xml("root", data)
    assert "<msg>Hello &lt;world&gt; &amp; friends</msg>" in xml_str
    assert "<invalid_name>value</invalid_name>" in xml_str

def test_serialize_device_command():
    params = {
        "intensity": 75,
        "mode": "pulse",
        "special_char": "val < 10 & val > 5"
    }
    
    # JSON command serialization
    json_cmd = serialize_device_command("device_123", "SET_LIGHT", params, "json")
    assert '"device_id": "device_123"' in json_cmd
    assert '"command": "SET_LIGHT"' in json_cmd
    assert '"special_char": "val < 10 & val > 5"' in json_cmd

    # XML command serialization
    xml_cmd = serialize_device_command("device_123", "SET_LIGHT", params, "xml")
    
    # Parse back the XML to verify structure and content
    root = ET.fromstring(xml_cmd)
    assert root.tag == "command"
    assert root.find("deviceId").text == "device_123"
    assert root.find("name").text == "SET_LIGHT"
    
    params_node = root.find("params")
    assert params_node is not None
    assert params_node.find("intensity").text == "75"
    assert params_node.find("mode").text == "pulse"
    assert params_node.find("special_char").text == "val < 10 & val > 5"
