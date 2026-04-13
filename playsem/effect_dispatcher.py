# effect_dispatcher.py

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Dict, Any, Optional, List
from playsem.device_manager import DeviceManager
from playsem.config.loader import load_effects_yaml
from playsem.device_capabilities import validate_effect_parameters
from playsem.effect_metadata import EffectMetadata


@dataclass
class _QueuedEffect:
    """Internal queue item for managed dispatch mode."""

    priority: int
    sequence: int
    effect_name: str
    parameters: Dict[str, Any]
    attempts: int = 0


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
        managed_mode: bool = False,
        failure_policy: str = "drop",
        max_dispatch_retries: int = 1,
        validate_capabilities: bool = False,
    ):
        """
        Initialize effect dispatcher.

        Args:
            device_manager: DeviceManager instance for sending commands
            effects_config_path: Path to effects.yaml config file
                (defaults to config/effects.yaml)
            managed_mode: If True, enqueue effects and dispatch via queue
            failure_policy: Behavior for failed dispatches:
                'drop', 'retry', or 'dead_letter'
            max_dispatch_retries: Max retries in retry policy
            validate_capabilities: Validate effect parameters against
                device capability contract before dispatch
        """
        self.device_manager = device_manager
        self.effects_config = {}
        self.managed_mode = managed_mode
        self.failure_policy = failure_policy
        self.max_dispatch_retries = max(0, max_dispatch_retries)
        self.validate_capabilities = validate_capabilities
        self._queue: List[tuple[int, int, _QueuedEffect]] = []
        self._sequence = count()
        self.dead_letter_queue: List[Dict[str, Any]] = []

        if self.failure_policy not in {"drop", "retry", "dead_letter"}:
            raise ValueError(
                "failure_policy must be one of: drop, retry, dead_letter"
            )

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

    def dispatch_effect(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
    ) -> bool:
        """
        Dispatch an effect with given parameters (legacy interface).

        Args:
            effect_name: Name of effect (e.g., 'light', 'wind')
            parameters: Effect parameters
            priority: Effect priority in managed mode (lower is higher)
        """
        if self.managed_mode:
            self.enqueue_effect(effect_name, parameters, priority=priority)
            return True

        return self._dispatch_once(effect_name, parameters)

    def dispatch_effect_metadata(
        self, effect: EffectMetadata, priority: int = 5
    ) -> bool:
        """
        Dispatch an effect from EffectMetadata object.

        Args:
            effect: EffectMetadata containing effect details
        """
        if effect.effect_type == "reconfigure":
            self._reconfigure_system(effect.parameters)
            return True

        # Merge intensity into parameters if present
        params = effect.parameters.copy()
        if effect.intensity is not None:
            params["intensity"] = effect.intensity

        # Add location if not 'everywhere'
        if effect.location != "everywhere":
            params["location"] = effect.location

        return self.dispatch_effect(effect.effect_type, params, priority)

    def enqueue_effect(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
    ):
        """Add an effect to the managed queue."""
        sequence = next(self._sequence)
        item = _QueuedEffect(
            priority=priority,
            sequence=sequence,
            effect_name=effect_name,
            parameters=parameters.copy(),
        )
        heapq.heappush(self._queue, (item.priority, item.sequence, item))

    def process_next_effect(self) -> Dict[str, Any]:
        """Process the next queued effect and return outcome details."""
        if not self._queue:
            return {"status": "empty"}

        _, _, item = heapq.heappop(self._queue)
        success = self._dispatch_once(item.effect_name, item.parameters)

        if success:
            return {
                "status": "dispatched",
                "effect": item.effect_name,
                "priority": item.priority,
                "attempts": item.attempts + 1,
            }

        item.attempts += 1
        if (
            self.failure_policy == "retry"
            and item.attempts <= self.max_dispatch_retries
        ):
            heapq.heappush(self._queue, (item.priority, item.sequence, item))
            return {
                "status": "requeued",
                "effect": item.effect_name,
                "priority": item.priority,
                "attempts": item.attempts,
            }

        if self.failure_policy == "dead_letter":
            dead_item = {
                "effect": item.effect_name,
                "parameters": item.parameters,
                "priority": item.priority,
                "attempts": item.attempts,
            }
            self.dead_letter_queue.append(dead_item)
            return {"status": "dead_lettered", **dead_item}

        return {
            "status": "dropped",
            "effect": item.effect_name,
            "priority": item.priority,
            "attempts": item.attempts,
        }

    def process_all_pending(self) -> List[Dict[str, Any]]:
        """Process all queued effects and return per-item outcomes."""
        outcomes: List[Dict[str, Any]] = []
        while self._queue:
            outcomes.append(self.process_next_effect())
        return outcomes

    def get_queue_size(self) -> int:
        """Return current managed queue size."""
        return len(self._queue)

    def _dispatch_once(
        self, effect_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Dispatch a single effect immediately and return success."""
        effect_config = self.effects_config.get("effects", {}).get(effect_name)

        if not effect_config:
            raise ValueError(f"Unknown effect: {effect_name}")

        device_id = effect_config.get("device")
        command = effect_config.get("command")

        if not device_id or not command:
            raise ValueError(
                f"Effect '{effect_name}' missing device or command config"
            )

        mapped_params = self._map_parameters(effect_config, parameters)

        if self.validate_capabilities:
            self._validate_capability_for_effect(
                device_id=device_id,
                effect_name=effect_name,
                effect_config=effect_config,
                params=mapped_params,
            )

        return bool(
            self.device_manager.send_command(device_id, command, mapped_params)
        )

    def _validate_capability_for_effect(
        self,
        device_id: str,
        effect_name: str,
        effect_config: Dict[str, Any],
        params: Dict[str, Any],
    ):
        """Validate command params against device capability contract."""
        get_caps = getattr(
            self.device_manager,
            "get_device_capabilities",
            None,
        )
        if not callable(get_caps):
            return

        capabilities = get_caps(device_id)
        if not capabilities:
            return

        capability_effect = effect_config.get("capability_effect")
        inferred = capability_effect or effect_name.split("_")[0]
        is_valid, errors = validate_effect_parameters(
            capabilities=capabilities,
            effect_type=inferred,
            params=params,
        )
        if not is_valid:
            raise ValueError(
                "Capability validation failed: " + "; ".join(errors)
            )

    def _reconfigure_system(self, config_data: Dict[str, Any]):
        """
        Reconfigures the system based on new settings.
        This method updates DeviceManager settings and potentially
        signals for ProtocolServer settings updates.
        """
        print(f"Received reconfigure command with data: {config_data}")

        # Reconfigure DeviceManager if relevant data is present
        if "device_manager" in config_data:
            reconfigure_fn = getattr(self.device_manager, "reconfigure", None)
            if callable(reconfigure_fn):
                if reconfigure_fn(config_data["device_manager"]):
                    print("DeviceManager reconfigured successfully.")
                else:
                    print(
                        "DeviceManager reconfiguration failed or not "
                        "supported."
                    )

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
