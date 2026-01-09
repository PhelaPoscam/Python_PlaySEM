# effect_dispatcher.py

from typing import Dict, Any, Optional
from playsem.device_manager import DeviceManager
from playsem.config.loader import load_effects_yaml
from playsem.effect_metadata import EffectMetadata


class EffectDispatcher:
    """
    Dispatches sensory effects to appropriate devices.

    Loads effect-to-device mappings from effects.yaml and handles
    parameter mapping (e.g., 'high' -> 255), location-based routing,
    and multi-device coordination.
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        effects_config_path: Optional[str] = None,
    ):
        """
        Initialize effect dispatcher.

        Args:
            device_manager: DeviceManager instance for sending commands
            effects_config_path: Path to effects.yaml config file
                (defaults to config/effects.yaml)
        """
        self.device_manager = device_manager
        self.effects_config = {}

        # Load effects configuration if path provided
        if effects_config_path:
            try:
                self.effects_config = load_effects_yaml(effects_config_path)
            except FileNotFoundError:
                # Fallback to hardcoded mappings
                self._use_default_mappings()
        else:
            self._use_default_mappings()

    def _use_default_mappings(self):
        """Set up default hardcoded effect mappings as fallback."""
        self.effects_config = {
            "effects": {
                "light": {
                    "device": "light_device",
                    "command": "set_brightness",
                },
                "wind": {
                    "device": "wind_device",
                    "command": "set_speed",
                },
                "vibration": {
                    "device": "vibration_device",
                    "command": "set_intensity",
                },
                "scent": {
                    "device": "scent_device",
                    "command": "set_scent",
                },
            }
        }

    def dispatch_effect(self, effect_name: str, parameters: Dict[str, Any]):
        """
        Dispatch an effect with given parameters (legacy interface).

        Args:
            effect_name: Name of effect (e.g., 'light', 'wind')
            parameters: Effect parameters
        """
        effect_config = self.effects_config.get("effects", {}).get(effect_name)

        if not effect_config:
            raise ValueError(f"Unknown effect: {effect_name}")

        device_id = effect_config.get("device")
        command = effect_config.get("command")

        if not device_id or not command:
            raise ValueError(
                f"Effect '{effect_name}' missing device or command config"
            )

        # Map parameters based on config
        mapped_params = self._map_parameters(effect_config, parameters)

        self.device_manager.send_command(device_id, command, mapped_params)

    def dispatch_effect_metadata(self, effect: EffectMetadata):
        """
        Dispatch an effect from EffectMetadata object.

        Args:
            effect: EffectMetadata containing effect details
        """
        if effect.effect_type == "reconfigure":
            self._reconfigure_system(effect.parameters)
            return

        # Merge intensity into parameters if present
        params = effect.parameters.copy()
        if effect.intensity is not None:
            params["intensity"] = effect.intensity

        # Add location if not 'everywhere'
        if effect.location != "everywhere":
            params["location"] = effect.location

        self.dispatch_effect(effect.effect_type, params)

    def _reconfigure_system(self, config_data: Dict[str, Any]):
        """
        Reconfigures the system based on new settings.
        This method updates DeviceManager settings and potentially
        signals for ProtocolServer settings updates.
        """
        print(f"Received reconfigure command with data: {config_data}")

        # Reconfigure DeviceManager if relevant data is present
        if "device_manager" in config_data:
            if self.device_manager.reconfigure(config_data["device_manager"]):
                print("DeviceManager reconfigured successfully.")
            else:
                print("DeviceManager reconfiguration failed or not supported.")

        # TODO: Implement signaling for ProtocolServer reconfiguration
        # This would likely involve a callback to the ControlPanelServer
        # or a similar managing entity.

    def _map_parameters(
        self, effect_config: Dict[str, Any], parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map parameter values based on effect configuration.

        Handles value mapping like 'high' -> 255, 'low' -> 64.

        Args:
            effect_config: Effect configuration from effects.yaml
            parameters: Raw parameters

        Returns:
            Mapped parameters
        """
        mapped = parameters.copy()
        param_configs = effect_config.get("parameters", [])

        for param_config in param_configs:
            param_name = param_config.get("name")
            if param_name not in parameters:
                # Use default if specified
                if "default" in param_config:
                    mapped[param_name] = param_config["default"]
                continue

            param_value = parameters[param_name]
            mapping = param_config.get("mapping", {})

            # If mapping exists and value is in mapping, use mapped value
            if mapping and param_value in mapping:
                mapped[param_name] = mapping[param_value]

        return mapped

    def get_supported_effects(self) -> list:
        """
        Get list of supported effect names.

        Returns:
            List of effect names
        """
        return list(self.effects_config.get("effects", {}).keys())
