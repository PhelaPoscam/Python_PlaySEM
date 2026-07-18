#!/usr/bin/env python3
"""
Standardized serialization utilities for JSON and XML payloads.
"""

import json
import xmltodict
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


def _sanitize_xml_keys(data: Any) -> Any:
    """Recursively sanitize dict keys to valid XML element names."""
    if isinstance(data, dict):
        return {_sanitize_xml_tag(k): _sanitize_xml_keys(v) for k, v in data.items()}
    if isinstance(data, (list, tuple, set)):
        return [_sanitize_xml_keys(item) for item in data]
    return data


def serialize_to_xml(tag_name: str, data: Dict[str, Any]) -> str:
    """Serialize a dictionary of key-values to an XML string."""
    sanitized = _sanitize_xml_keys(data)
    return str(
        xmltodict.unparse({tag_name: sanitized}, full_document=False, pretty=False)
    )


def serialize_device_command(
    device_id: str,
    command: str,
    params: Optional[Dict[str, Any]] = None,
    data_format: str = "json",
) -> str:
    """Serialize a device command using JSON or XML."""
    if params is None:
        params = {}

    if data_format.lower() == "xml":
        sanitized_params = _sanitize_xml_keys(params)
        payload = {
            "command": {
                "deviceId": device_id,
                "name": command,
                "params": sanitized_params,
            }
        }
        return str(xmltodict.unparse(payload, full_document=False, pretty=False))

    return serialize_to_json(
        {
            "command": command,
            "params": params,
            "device_id": device_id,
        }
    )
