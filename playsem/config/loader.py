# src/config_loader.py
import json
import logging
import os
from typing import Any, Dict

import defusedxml.ElementTree as SafeElementTree
import xmltodict
import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    A flexible configuration loader that handles YAML, JSON, and can
    transform a specific XML format (from the PlaySEM Java project)
    into the application's expected dictionary structure.
    """

    def __init__(
        self,
        devices_path: str,
        effects_path: str,
        protocols_path: str | None = None,
    ):
        """
        Initializes the ConfigLoader and loads all specified configurations.
        """
        self.devices_config = self._load_config_file(devices_path)
        self.effects_config = self._load_config_file(effects_path)
        self.protocols_config = (
            self._load_config_file(protocols_path) if protocols_path is not None else {}
        )

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
                    return yaml.safe_load(f) or {}
                elif extension == ".json":
                    return json.load(f) or {}
                elif extension == ".xml":
                    raw_xml = f.read()
                    safe_elem = SafeElementTree.fromstring(raw_xml)
                    from xml.etree.ElementTree import tostring as et_tostring

                    raw_dict = xmltodict.parse(
                        et_tostring(safe_elem, encoding="unicode")
                    )
                    # Check if this is a PlaySEM XML file and transform it
                    if "configuration" in raw_dict:
                        logger.info("PlaySEM XML format detected. Transforming...")
                        return self._transform_playsem_dict(raw_dict)
                    return raw_dict or {}
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

    def _transform_playsem_dict(self, raw_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms a dictionary parsed from SERenderer.xml into the format
        expected by this application (equivalent to devices.yaml).
        """
        transformed_config: Dict[str, Any] = {
            "devices": [],
            "connectivityInterfaces": [],
        }
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
                "deviceClass": self._map_java_class(xml_device.get("deviceClass")),
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
