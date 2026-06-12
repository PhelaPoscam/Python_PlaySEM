#!/usr/bin/env python3
"""
Standardized serialization utilities for JSON and XML payloads.
"""

import json
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring as _tostring
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Any, Dict, Optional


def json_default(obj: Any) -> Any:
    """Fallback JSON serializer for datetime, decimal, uuid, bytes, and sets."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def serialize_to_json(data: Any, **kwargs) -> str:
    """Serialize data to a JSON string using custom default encoder."""
    kwargs.setdefault("default", json_default)
    return json.dumps(data, **kwargs)


def _sanitize_xml_tag(name: str) -> str:
    """Sanitize key to be a valid XML element name."""
    if not name:
        return "element"
    first = (
        name[0]
        if (name[0].isalpha() or name[0] == "_")
        else ("_" + name[0] if name[0].isalnum() else "_")
    )
    rest = "".join(
        c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name[1:]
    )
    return first + rest


def _build_xml_tree(parent: ET.Element, data: Any):
    """Recursive helper to build XML elements from dict/list/scalar data."""
    if isinstance(data, dict):
        for k, v in data.items():
            _build_xml_tree(ET.SubElement(parent, _sanitize_xml_tag(k)), v)
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            _build_xml_tree(ET.SubElement(parent, "item"), item)
    else:
        if data is None:
            parent.text = ""
        elif isinstance(data, bool):
            parent.text = str(data).lower()
        elif isinstance(data, bytes):
            parent.text = data.hex()
        elif isinstance(data, (datetime, date)):
            parent.text = data.isoformat()
        else:
            parent.text = str(data)


def serialize_to_xml(tag_name: str, data: Dict[str, Any]) -> str:
    """Serialize a dictionary of key-values to an XML string."""
    root = ET.Element(tag_name)
    _build_xml_tree(root, data)
    return _tostring(root, encoding="utf-8").decode("utf-8")


def serialize_device_command(
    device_id: str,
    command: str,
    params: Optional[Dict[str, Any]] = None,
    data_format: str = "json",
) -> str:
    """Serialize a device command using standard JSON or properly escaped XML."""
    if params is None:
        params = {}

    if data_format.lower() == "xml":
        root = ET.Element("command")
        ET.SubElement(root, "deviceId").text = device_id
        ET.SubElement(root, "name").text = command
        _build_xml_tree(ET.SubElement(root, "params"), params)
        return _tostring(root, encoding="utf-8").decode("utf-8")

    return serialize_to_json(
        {
            "command": command,
            "params": params,
            "device_id": device_id,
        }
    )
