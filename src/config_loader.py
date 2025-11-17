# src/config_loader.py

import xml.etree.ElementTree as ET
from typing import List, Dict
import yaml


class DeviceDefinition:
    def __init__(
        self,
        id: str,
        device_class: str,
        connectivity_interface: str,
        properties: Dict[str, str]
    ):
        self.id = id
        self.device_class = device_class
        self.connectivity_interface = connectivity_interface
        self.properties = properties

    def __repr__(self):
        return (
            f"DeviceDefinition(id={self.id!r}, "
            f"device_class={self.device_class!r}, "
            f"connectivity_interface={self.connectivity_interface!r}, "
            f"properties={self.properties!r})"
        )


class Config:
    def __init__(self,
                 communication_service_broker: str,
                 metadata_parser: str,
                 light_device: str,
                 wind_device: str,
                 vibration_device: str,
                 scent_device: str,
                 devices: List[DeviceDefinition]):
        self.communication_service_broker = communication_service_broker
        self.metadata_parser = metadata_parser
        self.light_device = light_device
        self.wind_device = wind_device
        self.vibration_device = vibration_device
        self.scent_device = scent_device
        self.devices = devices

    def __repr__(self):
        return (
            f"Config(communication_service_broker="
            f"{self.communication_service_broker!r}, "
            f"metadata_parser={self.metadata_parser!r}, "
            f"light_device={self.light_device!r}, "
            f"wind_device={self.wind_device!r}, "
            f"vibration_device={self.vibration_device!r}, "
            f"scent_device={self.scent_device!r}, "
            f"devices={self.devices!r})"
        )


def load_config(xml_path: str) -> Config:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Top level simple tags
    comm = root.findtext('communicationServiceBroker')
    meta = root.findtext('metadataParser')
    light = root.findtext('lightDevice')
    wind = root.findtext('windDevice')
    vib = root.findtext('vibrationDevice')
    scent = root.findtext('scentDevice')

    # Devices list
    devices: List[DeviceDefinition] = []
    devices_root = root.find('devices')
    if devices_root is not None:
        for dev_el in devices_root.findall('device'):
            dev_id = dev_el.findtext('id', default='')
            dev_class = dev_el.findtext('deviceClass', default='')
            conn_if = dev_el.findtext('connectivityInterface', default='')
            # Properties
            props: Dict[str, str] = {}
            props_el = dev_el.find('properties')
            if props_el is not None:
                for p in props_el:
                    props[p.tag] = p.text.strip() if p.text else ""
            devices.append(DeviceDefinition(dev_id, dev_class, conn_if, props))

    config = Config(
        communication_service_broker=comm or '',
        metadata_parser=meta or '',
        light_device=light or '',
        wind_device=wind or '',
        vibration_device=vib or '',
        scent_device=scent or '',
        devices=devices
    )
    return config


def load_yaml_config(yaml_path: str) -> Dict:
    """
    Load YAML configuration file.

    Args:
        yaml_path: path to YAML configuration file

    Returns:
        Dictionary containing configuration data
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_devices_yaml(yaml_path: str) -> List[DeviceDefinition]:
    """
    Load device definitions from YAML file.

    Args:
        yaml_path: path to devices.yaml file

    Returns:
        List of DeviceDefinition objects
    """
    config_data = load_yaml_config(yaml_path)
    devices = []

    for device_data in config_data.get('devices', []):
        device = DeviceDefinition(
            id=device_data.get('id', ''),
            device_class=device_data.get('deviceClass', ''),
            connectivity_interface=device_data.get(
                'connectivityInterface', ''
            ),
            properties=device_data.get('properties', {})
        )
        devices.append(device)

    return devices


def load_effects_yaml(yaml_path: str) -> Dict:
    """
    Load effect definitions from YAML file.

    Args:
        yaml_path: path to effects.yaml file

    Returns:
        Dictionary containing effect mappings
    """
    return load_yaml_config(yaml_path)
