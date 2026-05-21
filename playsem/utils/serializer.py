#!/usr/bin/env python3
"""
Standardized serialization utilities for JSON and XML payloads.

Handles custom JSON encoding for datetimes, Decimals, UUIDs, bytes, and sets,
as well as proper escaping and tag sanitization for XML payloads.
"""

import json
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring as _tostring
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Any, Dict, Optional


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetimes, decimals, UUIDs, bytes, and sets.
    """

    def default(self, obj: Any) -> Any:
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
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def serialize_to_json(data: Any, **kwargs) -> str:
    """
    Serialize data to a JSON string using CustomJSONEncoder.
    """
    kwargs.setdefault("cls", CustomJSONEncoder)
    return json.dumps(data, **kwargs)


def serialize_to_xml(tag_name: str, data: Dict[str, Any]) -> str:
    """
    Serialize a dictionary of key-values to an XML string.
    Ensures proper escaping using xml.etree.ElementTree.
    """
    root = ET.Element(tag_name)
    _build_xml_tree(root, data)
    result: bytes = _tostring(root, encoding="utf-8")
    return result.decode("utf-8")


def serialize_device_command(
    device_id: str,
    command: str,
    params: Optional[Dict[str, Any]] = None,
    data_format: str = "json",
) -> str:
    """
    Serialize a device command using standard JSON or properly escaped XML.
    """
    if params is None:
        params = {}

    if data_format.lower() == "xml":
        root = ET.Element("command")

        dev_id_elem = ET.SubElement(root, "deviceId")
        dev_id_elem.text = device_id

        name_elem = ET.SubElement(root, "name")
        name_elem.text = command

        params_elem = ET.SubElement(root, "params")
        _build_xml_tree(params_elem, params)

        result: bytes = _tostring(root, encoding="utf-8")
        return result.decode("utf-8")
    else:
        payload = {
            "command": command,
            "params": params,
            "device_id": device_id,
        }
        return serialize_to_json(payload)


def _build_xml_tree(parent: ET.Element, data: Any):
    """Recursive helper to build XML elements from dict/list/scalar data."""
    if isinstance(data, dict):
        for k, v in data.items():
            tag = _sanitize_xml_tag(k)
            child = ET.SubElement(parent, tag)
            _build_xml_tree(child, v)
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            child = ET.SubElement(parent, "item")
            _build_xml_tree(child, item)
    else:
        if data is None:
            parent.text = ""
        elif isinstance(data, bool):
            parent.text = str(data).lower()
        elif isinstance(data, bytes):
            parent.text = data.hex()
        elif isinstance(data, (datetime, date)):
            parent.text = data.isoformat()
        elif isinstance(data, Decimal):
            parent.text = str(data)
        else:
            parent.text = str(data)


def _sanitize_xml_tag(name: str) -> str:
    """Sanitize key to be a valid XML element name."""
    if not name:
        return "element"
    chars = []
    for i, c in enumerate(name):
        if i == 0:
            if c.isalpha() or c == "_":
                chars.append(c)
            else:
                chars.append("_" + c if c.isalnum() else "_")
        else:
            if c.isalnum() or c in ("-", "_", "."):
                chars.append(c)
            else:
                chars.append("_")
    return "".join(chars)
