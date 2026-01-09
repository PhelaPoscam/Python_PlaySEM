# playsem/timeline.py
"""
Timeline scheduler for synchronized sensory effect rendering.

Provides precise timing control for multimedia applications like
video players, ensuring effects are triggered at exact timestamps.
"""

import time
import threading
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from .effect_metadata import EffectMetadata, EffectTimeline
from .effect_dispatcher import EffectDispatcher


@dataclass
class ScheduledEffect:
    """Represents an effect scheduled for execution."""

    effect: EffectMetadata
    scheduled_time: float  # absolute time (time.time())
    executed: bool = False


class Timeline:
    """
    Timeline scheduler for synchronized effect rendering.

    Manages a timeline of effects and triggers them at precise timestamps.
    Supports play, pause, stop, seek, and event-based triggering.
    """

    def __init__(
        self,
        effect_dispatcher: EffectDispatcher,
        tick_interval: float = 0.01,  # 10ms precision
    ):
        """
        Initialize timeline scheduler.

        Args:
            effect_dispatcher: EffectDispatcher for executing effects
            tick_interval: Timer tick interval in seconds (default 10ms)
        """
        self.dispatcher = effect_dispatcher
        self.tick_interval = tick_interval

        self.timeline: Optional[EffectTimeline] = None
        self.scheduled_effects: List[ScheduledEffect] = []

        self.is_running = False
        self.is_paused = False
        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.current_position = 0  # milliseconds

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Callbacks for timeline events
        self.on_start_callback: Optional[Callable] = None
        self.on_stop_callback: Optional[Callable] = None
        self.on_effect_callback: Optional[Callable] = None
        self.on_complete_callback: Optional[Callable] = None

    def load_timeline(self, timeline: EffectTimeline):
        """
        Load an effect timeline.

        Args:
            timeline: EffectTimeline object with effects to schedule
        """
        with self._lock:
            self.timeline = timeline
            self.scheduled_effects = []
            self.current_position = 0

    def start(self):
        """Start playing the timeline from current position."""
        with self._lock:
            if self.is_running:
                return

            if not self.timeline or not self.timeline.effects:
                raise ValueError("No timeline loaded or timeline is empty")

            self.is_running = True
            self.is_paused = False
            self.start_time = time.time() - (self.current_position / 1000.0)

            # Schedule all effects that haven't been executed
            self._schedule_effects()

            # Start scheduler thread
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_scheduler,
                daemon=False,  # Non-daemon to allow proper cleanup
            )
            self._thread.start()

            if self.on_start_callback:
                self.on_start_callback()

    def pause(self):
        """Pause timeline playback."""
        with self._lock:
            if not self.is_running or self.is_paused:
                return

            self.is_paused = True
            self.pause_time = time.time()

    def resume(self):
        """Resume timeline playback from pause."""
        with self._lock:
            if (
                not self.is_paused
                or self.pause_time is None
                or self.start_time is None
            ):
                return

            self.is_paused = False
            # Adjust start time to account for pause duration
            pause_duration = time.time() - self.pause_time
            self.start_time += pause_duration

    def stop(self):
        """Stop timeline playback and reset to beginning."""
        with self._lock:
            if not self.is_running:
                return

            self.is_running = False
            self.is_paused = False
            self._stop_event.set()

        # Wait for thread to finish (outside lock to avoid deadlock)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        with self._lock:
            self._thread = None
            self.current_position = 0
            self.start_time = None
            self.scheduled_effects = []

            if self.on_stop_callback:
                self.on_stop_callback()

    def seek(self, position_ms: int):
        """
        Seek to a specific position in the timeline.

        Args:
            position_ms: Position in milliseconds
        """
        with self._lock:
            if not self.timeline:
                return

            was_running = self.is_running
            if was_running:
                self.stop()

            self.current_position = max(
                0, min(position_ms, self.timeline.total_duration)
            )

            if was_running:
                self.start()

    def get_position(self) -> int:
        """
        Get current playback position in milliseconds.

        Returns:
            Current position in milliseconds
        """
        with self._lock:
            if not self.is_running or not self.start_time:
                return self.current_position

            if self.is_paused and self.pause_time:
                elapsed = self.pause_time - self.start_time
            else:
                elapsed = time.time() - self.start_time

            return int(elapsed * 1000)

    def add_event_effect(self, effect: EffectMetadata):
        """
        Add an event-based effect (triggered immediately).

        Args:
            effect: EffectMetadata with event_id set
        """
        if not effect.event_id:
            raise ValueError("Effect must have event_id for event triggering")

        # Execute immediately
        self._execute_effect(effect)

    def _schedule_effects(self):
        """Schedule all timeline effects based on current position."""
        if not self.timeline:
            return

        current_time = time.time()
        scheduled_effects = []

        for effect in self.timeline.effects:
            # Skip effects that are before current position
            if effect.timestamp < self.current_position:
                continue

            # Calculate absolute execution time
            time_offset = (effect.timestamp - self.current_position) / 1000.0
            scheduled_time = current_time + time_offset

            scheduled_effects.append(
                ScheduledEffect(
                    effect=effect,
                    scheduled_time=scheduled_time,
                    executed=False,
                )
            )

        self.scheduled_effects = scheduled_effects

    def _run_scheduler(self):
        """Main scheduler loop (runs in background thread)."""
        while not self._stop_event.is_set():
            if self.is_paused:
                time.sleep(self.tick_interval)
                continue

            current_time = time.time()

            with self._lock:
                # Update current position
                if self.start_time:
                    elapsed = current_time - self.start_time
                    self.current_position = int(elapsed * 1000)

                # Check for effects to execute
                for scheduled in self.scheduled_effects:
                    if (
                        not scheduled.executed
                        and current_time >= scheduled.scheduled_time
                    ):
                        self._execute_effect(scheduled.effect)
                        scheduled.executed = True

                # Check if timeline is complete
                if (
                    self.timeline
                    and self.current_position >= self.timeline.total_duration
                ):
                    self.is_running = False
                    if self.on_complete_callback:
                        self.on_complete_callback()
                    break

            time.sleep(self.tick_interval)

    def _execute_effect(self, effect: EffectMetadata):
        """
        Execute a single effect.

        Args:
            effect: EffectMetadata to execute
        """
        try:
            self.dispatcher.dispatch_effect_metadata(effect)

            if self.on_effect_callback:
                self.on_effect_callback(effect)

        except Exception as e:
            print(f"Error executing effect {effect.effect_type}: {e}")

    def set_callbacks(
        self,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_effect: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ):
        """
        Set callback functions for timeline events.

        Args:
            on_start: Called when timeline starts
            on_stop: Called when timeline stops
            on_effect: Called when each effect executes
            on_complete: Called when timeline completes
        """
        self.on_start_callback = on_start
        self.on_stop_callback = on_stop
        self.on_effect_callback = on_effect
        self.on_complete_callback = on_complete

    def get_status(self) -> Dict[str, Any]:
        """
        Get current timeline status.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "current_position": self.get_position(),
                "total_duration": (
                    self.timeline.total_duration if self.timeline else 0
                ),
                "pending_effects": sum(
                    1 for s in self.scheduled_effects if not s.executed
                ),
            }
