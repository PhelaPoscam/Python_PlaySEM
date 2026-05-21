# effect_dispatcher.py

import heapq
import time
import threading
from dataclasses import dataclass
from itertools import count
from typing import Dict, Any, Optional, List
from playsem.device_manager import DeviceManager
from playsem.config.loader import load_effects_yaml
from playsem.device_capabilities import validate_effect_parameters
from playsem.effect_metadata import EffectMetadata
from playsem.command_envelope import CommandEnvelope


@dataclass
class _QueuedEffect:
    """Internal queue item for managed dispatch mode."""

    priority: int
    sequence: int
    effect_name: str
    parameters: Dict[str, Any]
    expires_at: Optional[float] = None
    attempts: int = 0


@dataclass(frozen=True)
class DispatchResult:
    """Structured outcome for a dispatch attempt."""

    status: str
    accepted: bool
    delivered: bool = False
    effect: Optional[str] = None
    device_id: Optional[str] = None
    command: Optional[str] = None
    priority: Optional[int] = None
    attempts: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    expires_at: Optional[float] = None

    def __bool__(self) -> bool:
        """Keep compatibility with legacy bool-style callers."""
        return self.accepted and (self.delivered or self.status == "queued")

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        data = {
            "status": self.status,
            "accepted": self.accepted,
            "delivered": self.delivered,
            "effect": self.effect,
            "device_id": self.device_id,
            "command": self.command,
            "priority": self.priority,
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "expires_at": self.expires_at,
        }
        return {key: value for key, value in data.items() if value is not None}


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
        max_queue_size: Optional[int] = None,
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
            max_queue_size: Optional cap for managed-mode pending effects.
                When full, new effects are rejected instead of accepted into
                an unbounded queue.
        """
        self.device_manager = device_manager
        self.effects_config = {}
        self.managed_mode = managed_mode
        self.failure_policy = failure_policy
        self.max_dispatch_retries = max(0, max_dispatch_retries)
        self.validate_capabilities = validate_capabilities
        self.max_queue_size = max_queue_size
        self._queue: List[tuple[int, int, _QueuedEffect]] = []
        self._sequence = count()
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        if self.failure_policy not in {"drop", "retry", "dead_letter"}:
            raise ValueError(
                "failure_policy must be one of: drop, retry, dead_letter"
            )
        if self.max_queue_size is not None and self.max_queue_size < 1:
            raise ValueError("max_queue_size must be positive when provided")

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
        ttl_ms: Optional[int] = None,
    ) -> bool:
        """
        Dispatch an effect with given parameters (legacy interface).

        Args:
            effect_name: Name of effect (e.g., 'light', 'wind')
            parameters: Effect parameters
            priority: Effect priority in managed mode (lower is higher)
        """
        if self.managed_mode:
            return bool(
                self.dispatch_effect_result(
                    effect_name, parameters, priority, ttl_ms=ttl_ms
                )
            )

        return self._dispatch_once(effect_name, parameters)

    def dispatch_effect_result(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        ttl_ms: Optional[int] = None,
    ) -> DispatchResult:
        """Dispatch an effect and return a structured outcome."""
        if self.managed_mode:
            enqueued = self.enqueue_effect(
                effect_name,
                parameters,
                priority=priority,
                ttl_ms=ttl_ms,
            )
            if not enqueued:
                return DispatchResult(
                    status="rejected",
                    accepted=False,
                    delivered=False,
                    effect=effect_name,
                    priority=priority,
                    error="dispatch queue full",
                )
            expires_at = self._calculate_expires_at(ttl_ms)
            return DispatchResult(
                status="queued",
                accepted=True,
                delivered=False,
                effect=effect_name,
                priority=priority,
                expires_at=expires_at,
            )

        started = time.perf_counter()
        if self._is_ttl_expired(started, ttl_ms):
            return DispatchResult(
                status="expired",
                accepted=False,
                delivered=False,
                effect=effect_name,
                attempts=0,
                latency_ms=0.0,
                error="dispatch deadline expired",
            )
        try:
            outcome = self._dispatch_once_result(effect_name, parameters)
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return DispatchResult(
                status="failed",
                accepted=False,
                delivered=False,
                effect=effect_name,
                attempts=1,
                latency_ms=latency_ms,
                error=str(exc),
            )
        return outcome

    async def async_dispatch_effect(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        ttl_ms: Optional[int] = None,
    ) -> bool:
        """Asynchronously dispatch an effect with given parameters."""
        result = await self.async_dispatch_effect_result(
            effect_name, parameters, priority, ttl_ms=ttl_ms
        )
        return bool(result)

    async def async_dispatch_effect_result(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        ttl_ms: Optional[int] = None,
    ) -> DispatchResult:
        """Asynchronously dispatch an effect and return a structured outcome."""
        if self.managed_mode:
            # Managed mode still uses the sync queue for now, but we can queue it
            enqueued = self.enqueue_effect(
                effect_name,
                parameters,
                priority=priority,
                ttl_ms=ttl_ms,
            )
            if not enqueued:
                return DispatchResult(
                    status="rejected",
                    accepted=False,
                    delivered=False,
                    effect=effect_name,
                    priority=priority,
                    error="dispatch queue full",
                )
            expires_at = self._calculate_expires_at(ttl_ms)
            return DispatchResult(
                status="queued",
                accepted=True,
                delivered=False,
                effect=effect_name,
                priority=priority,
                expires_at=expires_at,
            )

        started = time.perf_counter()
        if self._is_ttl_expired(started, ttl_ms):
            return DispatchResult(
                status="expired",
                accepted=False,
                delivered=False,
                effect=effect_name,
                attempts=0,
                latency_ms=0.0,
                error="dispatch deadline expired",
            )
        try:
            outcome = await self._async_dispatch_once_result(
                effect_name, parameters
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return DispatchResult(
                status="failed",
                accepted=False,
                delivered=False,
                effect=effect_name,
                attempts=1,
                latency_ms=latency_ms,
                error=str(exc),
            )
        return outcome

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

        ttl_ms = self._extract_ttl_ms(params)
        return self.dispatch_effect(
            effect.effect_type, params, priority, ttl_ms=ttl_ms
        )

    def dispatch_effect_metadata_result(
        self, effect: EffectMetadata, priority: int = 5
    ) -> DispatchResult:
        """Dispatch EffectMetadata and return a structured outcome."""
        if effect.effect_type == "reconfigure":
            self._reconfigure_system(effect.parameters)
            return DispatchResult(
                status="reconfigured",
                accepted=True,
                delivered=True,
                effect=effect.effect_type,
                attempts=1,
            )

        params = effect.parameters.copy()
        if effect.intensity is not None:
            params["intensity"] = effect.intensity
        if effect.location != "everywhere":
            params["location"] = effect.location

        ttl_ms = self._extract_ttl_ms(params)
        return self.dispatch_effect_result(
            effect.effect_type, params, priority, ttl_ms=ttl_ms
        )

    async def async_dispatch_effect_metadata(
        self, effect: EffectMetadata, priority: int = 5
    ) -> bool:
        """Asynchronously dispatch an effect from EffectMetadata object."""
        result = await self.async_dispatch_effect_metadata_result(
            effect, priority
        )
        return bool(result)

    async def async_dispatch_effect_metadata_result(
        self, effect: EffectMetadata, priority: int = 5
    ) -> DispatchResult:
        """Asynchronously dispatch EffectMetadata and return a structured outcome."""
        if effect.effect_type == "reconfigure":
            self._reconfigure_system(effect.parameters)
            return DispatchResult(
                status="reconfigured",
                accepted=True,
                delivered=True,
                effect=effect.effect_type,
                attempts=1,
            )

        params = effect.parameters.copy()
        if effect.intensity is not None:
            params["intensity"] = effect.intensity
        if effect.location != "everywhere":
            params["location"] = effect.location

        ttl_ms = self._extract_ttl_ms(params)
        return await self.async_dispatch_effect_result(
            effect.effect_type, params, priority, ttl_ms=ttl_ms
        )

    def enqueue_effect(
        self,
        effect_name: str,
        parameters: Dict[str, Any],
        priority: int = 5,
        ttl_ms: Optional[int] = None,
    ) -> bool:
        """Add an effect to the managed queue."""
        with self._lock:
            if (
                self.max_queue_size is not None
                and len(self._queue) >= self.max_queue_size
            ):
                return False
            sequence = next(self._sequence)
            item = _QueuedEffect(
                priority=priority,
                sequence=sequence,
                effect_name=effect_name,
                parameters=parameters.copy(),
                expires_at=self._calculate_expires_at(ttl_ms),
            )
            heapq.heappush(self._queue, (item.priority, item.sequence, item))
            return True

    def process_next_effect(self) -> Dict[str, Any]:
        """Process the next queued effect and return outcome details."""
        with self._lock:
            if not self._queue:
                return {"status": "empty"}

            _, _, item = heapq.heappop(self._queue)

        if item.expires_at is not None and time.monotonic() >= item.expires_at:
            return {
                "status": "expired",
                "effect": item.effect_name,
                "priority": item.priority,
                "attempts": item.attempts,
                "error": "dispatch deadline expired",
            }

        result = self._dispatch_once_result(item.effect_name, item.parameters)
        success = result.delivered

        if success:
            return {
                "status": "dispatched",
                "effect": item.effect_name,
                "priority": item.priority,
                "attempts": item.attempts + 1,
                "latency_ms": result.latency_ms,
            }

        item.attempts += 1
        if (
            self.failure_policy == "retry"
            and item.attempts <= self.max_dispatch_retries
        ):
            with self._lock:
                heapq.heappush(
                    self._queue, (item.priority, item.sequence, item)
                )
            return {
                "status": "requeued",
                "effect": item.effect_name,
                "priority": item.priority,
                "attempts": item.attempts,
                "error": result.error,
            }

        if self.failure_policy == "dead_letter":
            dead_item = {
                "effect": item.effect_name,
                "parameters": item.parameters,
                "priority": item.priority,
                "attempts": item.attempts,
                "error": result.error,
            }
            with self._lock:
                self.dead_letter_queue.append(dead_item)
            return {"status": "dead_lettered", **dead_item}

        return {
            "status": "dropped",
            "effect": item.effect_name,
            "priority": item.priority,
            "attempts": item.attempts,
            "error": result.error,
        }

    def process_all_pending(self) -> List[Dict[str, Any]]:
        """Process all queued effects and return per-item outcomes."""
        outcomes: List[Dict[str, Any]] = []
        while self.get_queue_size():
            outcomes.append(self.process_next_effect())
        return outcomes

    def get_queue_size(self) -> int:
        """Return current managed queue size."""
        with self._lock:
            return len(self._queue)

    def get_queue_capacity(self) -> Optional[int]:
        """Return managed queue capacity, or None for unbounded."""
        return self.max_queue_size

    def _calculate_expires_at(self, ttl_ms: Optional[int]) -> Optional[float]:
        """Return monotonic expiration time for a TTL value."""
        if ttl_ms is None:
            return None
        return time.monotonic() + (max(0, ttl_ms) / 1000.0)

    def _is_ttl_expired(self, started: float, ttl_ms: Optional[int]) -> bool:
        """Return True when a dispatch TTL is already exhausted."""
        if ttl_ms is None:
            return False
        return (time.perf_counter() - started) * 1000.0 >= ttl_ms

    def _extract_ttl_ms(self, params: Dict[str, Any]) -> Optional[int]:
        """Extract optional dispatch TTL without mutating effect params."""
        value = params.get("ttl_ms")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _dispatch_once(
        self, effect_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Dispatch a single effect immediately and return success."""
        return self._dispatch_once_result(effect_name, parameters).delivered

    def _dispatch_once_result(
        self, effect_name: str, parameters: Dict[str, Any]
    ) -> DispatchResult:
        """Dispatch a single effect immediately and return details."""
        started = time.perf_counter()
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

        try:
            delivered = bool(
                self.device_manager.send_command(
                    device_id, command, mapped_params
                )
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            return DispatchResult(
                status="dispatched" if delivered else "failed",
                accepted=delivered,
                delivered=delivered,
                effect=effect_name,
                device_id=device_id,
                command=command,
                attempts=1,
                latency_ms=latency_ms,
                error=None if delivered else "device manager returned False",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return DispatchResult(
                status="failed",
                accepted=False,
                delivered=False,
                effect=effect_name,
                device_id=device_id,
                command=command,
                attempts=1,
                latency_ms=latency_ms,
                error=str(exc),
            )

    async def _async_dispatch_once_result(
        self, effect_name: str, parameters: Dict[str, Any]
    ) -> DispatchResult:
        """Asynchronously dispatch a single effect immediately and return details."""
        started = time.perf_counter()
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

        # Optional TTL mapped to deadline_ms
        deadline_ms = None
        if "ttl_ms" in mapped_params:
            try:
                ttl_val = int(mapped_params["ttl_ms"])
                if ttl_val > 0:
                    deadline_ms = ttl_val
            except (ValueError, TypeError):
                pass

        # Optional delivery mode based on failure policy
        delivery_mode = (
            "at_least_once"
            if self.failure_policy in ("retry", "dead_letter")
            else "best_effort"
        )

        envelope = CommandEnvelope(
            effect=EffectMetadata(effect_type=""),
            device_id=device_id,
            command=command,
            params=mapped_params,
            deadline_ms=deadline_ms,
            delivery_mode=delivery_mode,  # type: ignore[arg-type]
        )

        try:
            submit_result = await self.device_manager.async_submit_envelope(
                envelope
            )
            latency_ms = (time.perf_counter() - started) * 1000.0

            return DispatchResult(
                status=submit_result.get("status", "failed"),
                accepted=submit_result.get("accepted", False),
                delivered=submit_result.get("delivered", False),
                effect=effect_name,
                device_id=device_id,
                command=command,
                attempts=1,
                latency_ms=latency_ms,
                error=submit_result.get("error"),
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return DispatchResult(
                status="failed",
                accepted=False,
                delivered=False,
                effect=effect_name,
                device_id=device_id,
                command=command,
                attempts=1,
                latency_ms=latency_ms,
                error=str(exc),
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
