# tests/test_config_loader.py

from src.config_loader import load_config, DeviceDefinition


def test_load_config_minimal(tmp_path):
    xml_content = """
    <SERendererConfig>
      <communicationServiceBroker>upnpService</communicationServiceBroker>
      <metadataParser>mpegvParser</metadataParser>
      <lightDevice>mockLight</lightDevice>
      <windDevice>mockWind</windDevice>
      <vibrationDevice>mockVibration</vibrationDevice>
      <scentDevice>mockScent</scentDevice>

      <devices>
        <device>
          <id>mockLight</id>
          <deviceClass>my.package.MockLightDevice</deviceClass>
          <connectivityInterface>mockInterface</connectivityInterface>
          <properties>
            <delay>800</delay>
          </properties>
        </device>
      </devices>
    </SERendererConfig>
    """
    xml_file = tmp_path / "test_config.xml"
    xml_file.write_text(xml_content)

    config = load_config(str(xml_file))

    assert config.communication_service_broker == "upnpService"
    assert config.metadata_parser == "mpegvParser"
    assert config.light_device == "mockLight"
    assert config.wind_device == "mockWind"
    assert config.vibration_device == "mockVibration"
    assert config.scent_device == "mockScent"

    assert len(config.devices) == 1
    device = config.devices[0]
    assert isinstance(device, DeviceDefinition)
    assert device.id == "mockLight"
    assert device.device_class == "my.package.MockLightDevice"
    assert device.connectivity_interface == "mockInterface"
    assert device.properties.get("delay") == "800"
