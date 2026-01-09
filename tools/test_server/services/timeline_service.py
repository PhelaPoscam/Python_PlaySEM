"""
Timeline Service - Timeline management and playback.

Handles:
- Timeline upload and storage
- Playback control (pause, resume, stop)
- Timeline status tracking
- Timeline event broadcasting
"""

import asyncio
import json
from typing import Dict, Optional

from fastapi import WebSocket


class TimelineService:
    """Service for managing effect timelines."""

    def __init__(self):
        """Initialize timeline service."""
        self.timelines = {}  # timeline_id -> timeline data
        self.timeline_tasks = {}  # timeline_id -> asyncio task
        self.timeline_status = {}  # timeline_id -> status info
        self.stats = {
            "timelines_uploaded": 0,
            "timelines_played": 0,
            "timelines_paused": 0,
            "errors": 0,
        }

    async def handle_timeline_upload(
        self,
        websocket: WebSocket,
        timeline_id: str,
        timeline_data: dict,
        effect_dispatcher,
        device_id: str = None,
    ) -> None:
        """Handle timeline upload and storage.

        Args:
            websocket: WebSocket connection for status
            timeline_id: Unique timeline identifier
            timeline_data: Timeline JSON data (events array)
            effect_dispatcher: Dispatcher for effect sending
            device_id: Optional target device ID
        """
        try:
            if not timeline_data.get("events"):
                raise ValueError("Timeline must contain 'events' array")

            events = timeline_data["events"]
            if not isinstance(events, list):
                raise ValueError("Events must be an array")

            # Validate each event
            for i, event in enumerate(events):
                if not isinstance(event, dict):
                    raise ValueError(f"Event {i} is not an object")
                if "time" not in event:
                    raise ValueError(f"Event {i} missing 'time' field")
                if "effect" not in event:
                    raise ValueError(f"Event {i} missing 'effect' field")

            # Store timeline
            self.timelines[timeline_id] = {
                "id": timeline_id,
                "events": events,
                "device_id": device_id,
                "uploaded_at": asyncio.get_event_loop().time(),
                "duration": max(
                    (e.get("time", 0) + e.get("effect", {}).get("duration", 0))
                    for e in events
                ),
            }

            self.timeline_status[timeline_id] = {
                "state": "ready",
                "current_time": 0,
                "progress": 0,
            }

            self.stats["timelines_uploaded"] += 1

            print(
                f"[OK] Timeline '{timeline_id}' uploaded with "
                f"{len(events)} events, total duration "
                f"{self.timelines[timeline_id]['duration']}ms"
            )

            await websocket.send_json(
                {
                    "type": "timeline_result",
                    "success": True,
                    "timeline_id": timeline_id,
                    "event_count": len(events),
                    "duration": self.timelines[timeline_id]["duration"],
                }
            )

        except Exception as e:
            print(f"[x] Timeline upload error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "timeline_result",
                    "success": False,
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    async def play_timeline(
        self,
        websocket: WebSocket,
        timeline_id: str,
        device_id: str = None,
        effect_dispatcher=None,
        broadcast_callback=None,
    ) -> None:
        """Play a timeline.

        Args:
            websocket: WebSocket connection for status
            timeline_id: Timeline to play
            device_id: Optional target device
            effect_dispatcher: Dispatcher for effects
            broadcast_callback: Callback for broadcasting
        """
        try:
            if timeline_id not in self.timelines:
                raise ValueError(f"Timeline '{timeline_id}' not found")

            timeline = self.timelines[timeline_id]
            if timeline_id in self.timeline_tasks:
                await self.pause_timeline(
                    websocket, timeline_id, device_id, broadcast_callback
                )
                await asyncio.sleep(0.1)

            self.timeline_status[timeline_id]["state"] = "playing"
            self.stats["timelines_played"] += 1

            print(f"[OK] Playing timeline '{timeline_id}'")

            task = asyncio.create_task(
                self._play_timeline_task(
                    timeline, timeline_id, device_id, broadcast_callback
                )
            )
            self.timeline_tasks[timeline_id] = task

            await websocket.send_json(
                {
                    "type": "timeline_playing",
                    "timeline_id": timeline_id,
                    "device_id": device_id,
                }
            )

        except Exception as e:
            print(f"[x] Timeline play error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "timeline_error",
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    async def _play_timeline_task(
        self,
        timeline: dict,
        timeline_id: str,
        device_id: str,
        broadcast_callback,
    ) -> None:
        """Internal task for playing timeline events.

        Args:
            timeline: Timeline data
            timeline_id: Timeline ID
            device_id: Target device
            broadcast_callback: Broadcast callback
        """
        try:
            start_time = asyncio.get_event_loop().time()
            events = timeline["events"]

            for event in events:
                event_time = (
                    event.get("time", 0) / 1000.0
                )  # Convert to seconds
                current_time = asyncio.get_event_loop().time() - start_time

                # Wait until event time
                if event_time > current_time:
                    wait_time = event_time - current_time
                    await asyncio.sleep(wait_time)

                # Check if paused
                while self.timeline_status[timeline_id]["state"] == "paused":
                    await asyncio.sleep(0.05)

                # Check if stopped
                if self.timeline_status[timeline_id]["state"] == "stopped":
                    break

                # Execute event
                effect = event.get("effect", {})
                if callable(broadcast_callback):
                    await broadcast_callback(
                        timeline_id=timeline_id,
                        effect=effect,
                        event_time=event_time,
                    )

                # Update progress
                progress = (
                    (event_time / timeline["duration"]) * 100
                    if timeline["duration"] > 0
                    else 0
                )
                self.timeline_status[timeline_id]["progress"] = min(
                    progress, 100
                )

            # Timeline complete
            if self.timeline_status[timeline_id]["state"] != "stopped":
                self.timeline_status[timeline_id]["state"] = "completed"
                self.timeline_status[timeline_id]["progress"] = 100

                if callable(broadcast_callback):
                    await broadcast_callback(
                        timeline_id=timeline_id,
                        event_type="timeline_complete",
                    )

            print(f"[OK] Timeline '{timeline_id}' completed")

        except asyncio.CancelledError:
            print(f"[INFO] Timeline '{timeline_id}' cancelled")
        except Exception as e:
            print(f"[x] Timeline playback error: {e}")
            if timeline_id in self.timeline_status:
                self.timeline_status[timeline_id]["state"] = "error"
        finally:
            self.timeline_tasks.pop(timeline_id, None)

    async def pause_timeline(
        self,
        websocket: WebSocket,
        timeline_id: str,
        device_id: str = None,
        broadcast_callback=None,
    ) -> None:
        """Pause a playing timeline.

        Args:
            websocket: WebSocket connection
            timeline_id: Timeline to pause
            device_id: Optional device ID
            broadcast_callback: Broadcast callback
        """
        try:
            if timeline_id not in self.timeline_status:
                raise ValueError(f"Timeline '{timeline_id}' not found")

            status = self.timeline_status[timeline_id]
            if status["state"] != "playing":
                raise ValueError(
                    f"Cannot pause timeline in state '{status['state']}'"
                )

            status["state"] = "paused"
            self.stats["timelines_paused"] += 1

            print(
                f"[OK] Timeline '{timeline_id}' paused at {status['progress']}%"
            )

            if callable(broadcast_callback):
                await broadcast_callback(
                    timeline_id=timeline_id,
                    event_type="timeline_paused",
                    progress=status["progress"],
                )

            await websocket.send_json(
                {
                    "type": "timeline_paused",
                    "timeline_id": timeline_id,
                    "progress": status["progress"],
                }
            )

        except Exception as e:
            print(f"[x] Pause error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "timeline_error",
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    async def resume_timeline(
        self,
        websocket: WebSocket,
        timeline_id: str,
        device_id: str = None,
        broadcast_callback=None,
    ) -> None:
        """Resume a paused timeline.

        Args:
            websocket: WebSocket connection
            timeline_id: Timeline to resume
            device_id: Optional device ID
            broadcast_callback: Broadcast callback
        """
        try:
            if timeline_id not in self.timeline_status:
                raise ValueError(f"Timeline '{timeline_id}' not found")

            status = self.timeline_status[timeline_id]
            if status["state"] != "paused":
                raise ValueError(
                    f"Cannot resume timeline in state '{status['state']}'"
                )

            status["state"] = "playing"
            print(
                f"[OK] Timeline '{timeline_id}' resumed from {status['progress']}%"
            )

            if callable(broadcast_callback):
                await broadcast_callback(
                    timeline_id=timeline_id,
                    event_type="timeline_resumed",
                    progress=status["progress"],
                )

            await websocket.send_json(
                {
                    "type": "timeline_resumed",
                    "timeline_id": timeline_id,
                    "progress": status["progress"],
                }
            )

        except Exception as e:
            print(f"[x] Resume error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "timeline_error",
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    async def stop_timeline(
        self,
        websocket: WebSocket,
        timeline_id: str,
        device_id: str = None,
        broadcast_callback=None,
    ) -> None:
        """Stop a playing/paused timeline.

        Args:
            websocket: WebSocket connection
            timeline_id: Timeline to stop
            device_id: Optional device ID
            broadcast_callback: Broadcast callback
        """
        try:
            if timeline_id not in self.timeline_status:
                raise ValueError(f"Timeline '{timeline_id}' not found")

            status = self.timeline_status[timeline_id]
            if status["state"] not in ("playing", "paused"):
                raise ValueError(
                    f"Cannot stop timeline in state '{status['state']}'"
                )

            status["state"] = "stopped"
            status["progress"] = 0

            # Cancel playback task
            if timeline_id in self.timeline_tasks:
                task = self.timeline_tasks[timeline_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            print(f"[OK] Timeline '{timeline_id}' stopped")

            if callable(broadcast_callback):
                await broadcast_callback(
                    timeline_id=timeline_id,
                    event_type="timeline_stopped",
                )

            await websocket.send_json(
                {
                    "type": "timeline_stopped",
                    "timeline_id": timeline_id,
                }
            )

        except Exception as e:
            print(f"[x] Stop error: {e}")
            self.stats["errors"] += 1
            await websocket.send_json(
                {
                    "type": "timeline_error",
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    async def get_timeline_status(
        self,
        websocket: WebSocket,
        timeline_id: str,
    ) -> None:
        """Get status of a timeline.

        Args:
            websocket: WebSocket connection
            timeline_id: Timeline ID
        """
        try:
            if timeline_id not in self.timeline_status:
                raise ValueError(f"Timeline '{timeline_id}' not found")

            status = self.timeline_status[timeline_id]
            timeline = self.timelines.get(timeline_id, {})

            await websocket.send_json(
                {
                    "type": "timeline_status",
                    "timeline_id": timeline_id,
                    "state": status["state"],
                    "progress": status["progress"],
                    "duration": timeline.get("duration", 0),
                }
            )

        except Exception as e:
            print(f"[x] Status error: {e}")
            await websocket.send_json(
                {
                    "type": "timeline_error",
                    "error": str(e),
                    "timeline_id": timeline_id,
                }
            )

    def get_all_timeline_ids(self) -> list:
        """Get all uploaded timeline IDs.

        Returns:
            List of timeline IDs
        """
        return list(self.timelines.keys())

    def get_timeline_info(self, timeline_id: str) -> Optional[dict]:
        """Get timeline info.

        Args:
            timeline_id: Timeline ID

        Returns:
            Timeline info dict or None
        """
        if timeline_id not in self.timelines:
            return None

        timeline = self.timelines[timeline_id]
        status = self.timeline_status.get(timeline_id, {})

        return {
            "id": timeline_id,
            "event_count": len(timeline.get("events", [])),
            "duration": timeline.get("duration", 0),
            "state": status.get("state", "unknown"),
            "progress": status.get("progress", 0),
        }

    async def cleanup(self) -> None:
        """Cleanup all timeline resources."""
        for timeline_id in list(self.timeline_tasks.keys()):
            task = self.timeline_tasks[timeline_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.timelines.clear()
        self.timeline_tasks.clear()
        self.timeline_status.clear()
