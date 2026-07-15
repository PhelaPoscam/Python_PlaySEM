from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Literal
import time
from playsem.effect_metadata import EffectMetadata


@dataclass(frozen=True, slots=True)
class CommandEnvelope:
    """
    Standardized payload for dispatching an effect to a device.
    """

    effect: EffectMetadata
    device_id: str
    command: str
    params: Dict[str, Any]
    deadline_ms: Optional[int] = None
    priority: int = 5
    delivery_mode: Literal["best_effort", "at_least_once"] = "best_effort"
    created_at: float = field(default_factory=time.monotonic)
