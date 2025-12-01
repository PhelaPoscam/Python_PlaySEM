# src/config_loader.py
import json
import logging
import os
from typing import Any, Dict, List

import xmltodict
from dataclasses import dataclass, field
import yaml

logger = logging.getLogger(__name__)


# --- Backwards-compatibility data models and functions ---
@dataclass
class DeviceDefinition:
    id: str
    device_class: str
    connectivity_interface: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    communication_service_broker: str = ""
    metadata_parser: str = ""
    light_device: str = ""
    wind_device: str = ""
    vibration_device: str = ""
    scent_device: str = ""
    devices: List[DeviceDefinition] = field(default_factory=list)


def load_config(path: str) -> Config:
    """
    Legacy loader for SERendererConfig-style XML files used in tests.

    Returns a Config instance populated from the XML.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = xmltodict.parse(f.read())
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {path}")
        raise

    root = data.get("SERendererConfig", {})

    cfg = Config(
        communication_service_broker=root.get(
            "communicationServiceBroker", ""
        ),
        metadata_parser=root.get("metadataParser", ""),
        light_device=root.get("lightDevice", ""),
        wind_device=root.get("windDevice", ""),
        vibration_device=root.get("vibrationDevice", ""),
        scent_device=root.get("scentDevice", ""),
    )

    devices_node = root.get("devices", {}) or {}
    device_list = devices_node.get("device", [])
    if not isinstance(device_list, list):
        device_list = [device_list]

    for dev in device_list:
        if not dev:
            continue
        props_node = dev.get("properties", {}) or {}
        # Flatten properties (keep direct children of <properties>)
        props: Dict[str, Any] = {}
        if isinstance(props_node, dict):
            for k, v in props_node.items():
                # xmltodict may wrap values; ensure plain strings where possible
                props[k] = v

        cfg.devices.append(
            DeviceDefinition(
                id=dev.get("id", ""),
                device_class=dev.get("deviceClass", ""),
                connectivity_interface=dev.get("connectivityInterface", ""),
                properties=props,
            )
        )

    return cfg


def load_effects_yaml(path: str) -> Dict[str, Any]:
    """
    Legacy helper used by EffectDispatcher to load effects.yaml.
    Returns the parsed YAML as a dict (or empty dict if file is empty).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


class ConfigLoader:
    """
    A flexible configuration loader that handles YAML, JSON, and can
    transform a specific XML format (from the PlaySEM Java project)
    into the application's expected dictionary structure.
    """

    def __init__(
        self, devices_path: str, effects_path: str, protocols_path: str
    ):
        """
        Initializes the ConfigLoader and loads all specified configurations.
        """
        self.devices_config = self._load_config_file(devices_path)
        self.effects_config = self._load_config_file(effects_path)
        self.protocols_config = self._load_config_file(protocols_path)

    def load_devices_config(self) -> Dict[str, Any]:
        return self.devices_config

    def load_effects_config(self) -> Dict[str, Any]:
        return self.effects_config

    def load_protocols_config(self) -> Dict[str, Any]:
        return self.protocols_config

    def _load_config_file(self, path: str) -> Dict[str, Any]:
        """
        Loads a configuration file, dispatching to the correct parser
        based on the file extension.
        """
        _, extension = os.path.splitext(path)
        extension = extension.lower()

        logger.info(f"Loading configuration file: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                if extension in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif extension == ".json":
                    return json.load(f)
                elif extension == ".xml":
                    raw_dict = xmltodict.parse(f.read())
                    # Check if this is a PlaySEM XML file and transform it
                    if "configuration" in raw_dict:
                        logger.info(
                            "PlaySEM XML format detected. Transforming..."
                        )
                        return self._transform_playsem_dict(raw_dict)
                    return raw_dict
                else:
                    raise ValueError(
                        f"Unsupported configuration file format: {extension}"
                    )
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {path}")
            raise
        except Exception as e:
            logger.error(f"Error parsing configuration file {path}: {e}")
            raise

    def _transform_playsem_dict(
        self, raw_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transforms a dictionary parsed from SERenderer.xml into the format
        expected by this application (equivalent to devices.yaml).
        """
        transformed_config = {"devices": [], "connectivityInterfaces": []}
        config_node = raw_dict.get("configuration", {})

        # --- Transform Devices ---
        device_list = config_node.get("devices", {}).get("device", [])
        if not isinstance(device_list, list):
            device_list = [device_list]  # Handle case of single device

        for xml_device in device_list:
            interface_ref = xml_device.get("connectivityInterface")
            py_device = {
                "deviceId": xml_device.get("id"),
                "label": xml_device.get("id"),  # Use id as a default label
                "deviceClass": self._map_java_class(
                    xml_device.get("deviceClass")
                ),
                # The protocol is determined by the interface, so we map it later
                "protocol": interface_ref.lower() if interface_ref else None,
                "connectivityInterface": (
                    f"{interface_ref}_interface" if interface_ref else None
                ),
                "capabilities": [],  # XML doesn't define this, so default to empty
            }
            transformed_config["devices"].append(py_device)

        # --- Transform Connectivity Interfaces ---
        interface_list = config_node.get("connectivityInterfaces", {}).get(
            "connectivityInterface", []
        )
        if not isinstance(interface_list, list):
            interface_list = [interface_list]

        for xml_interface in interface_list:
            interface_id = xml_interface.get("id")
            py_interface = {
                "name": f"{interface_id}_interface",
                "protocol": interface_id.lower(),
                # Extract properties if they exist
                **xml_interface.get("properties", {}),
            }
            # The XML format has inconsistent property names, so we normalize them
            if "serialPort" in py_interface:
                py_interface["port"] = py_interface.pop("serialPort")
            if "baudRate" in py_interface:
                py_interface["baudrate"] = int(py_interface.pop("baudRate"))

            transformed_config["connectivityInterfaces"].append(py_interface)

        logger.info(
            f"Successfully transformed {len(transformed_config['devices'])} devices "
            f"and {len(transformed_config['connectivityInterfaces'])} interfaces."
        )
        return transformed_config

    def _map_java_class(self, java_class: str) -> str:
        """
        A best-effort mapping from known PlaySEM Java class names to simple
        Python-friendly device types.
        """
        if not java_class:
            return "GenericDevice"

        class_name = java_class.lower()

        if "wind" in class_name:
            return "Fan"
        if "light" in class_name:
            return "Light"
        if "vibration" in class_name:
            return "Vibration"
        if "scent" in class_name:
            return "Scent"
        if "mock" in class_name:
            return "MockDevice"

        # Default fallback
        return "GenericDevice"
