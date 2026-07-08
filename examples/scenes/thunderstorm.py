#!/usr/bin/env python3
"""
Thunderstorm Scene — a multi-sensory demo using mock devices.

Simulates a thunderstorm across all four sensory channels WITHOUT needing
any physical hardware. Drives mock devices directly — no config files,
no external services, no effect-mapping indirection.

Usage:
    python examples/scenes/thunderstorm.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from playsem.drivers.mock_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

# ── ANSI helpers ────────────────────────────────────────────────────────────

_R = "\033[0m"
_B = "\033[1m"
_D = "\033[2m"


def _fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


C_LIGHT = _fg(255, 220, 50)
C_WIND = _fg(100, 200, 255)
C_VIBE = _fg(255, 120, 80)
C_SCENT = _fg(180, 130, 255)
C_TIME = _fg(150, 150, 150)
C_BRIGHT = _fg(255, 255, 255)
C_FLASH = _bg(255, 255, 200) + _fg(0, 0, 0)

# ── scene data ──────────────────────────────────────────────────────────────
# Each cue: (timestamp_ms, description, callable)
# The callable receives (light, wind, vibe, scent) and drives them directly.


def _build_cues():
    """Return a sorted list of (timestamp_ms, description, callback)."""
    cues: list[tuple[int, str, callable]] = []  # type: ignore[syntax]

    def at(ms: int, desc: str):
        """Decorator: register a cue at the given timestamp."""

        def deco(fn):
            cues.append((ms, desc, fn))
            return fn

        return deco

    # ── phase 0: calm before the storm ──
    @at(0, "calm breeze begins")
    def _(l, w, v, s):
        w.set_speed(10)
        w.set_direction("forward")

    @at(0, "distant ocean scent")
    def _(l, w, v, s):
        s.set_scent("ocean", 15)

    @at(2500, "grey sky darkens")
    def _(l, w, v, s):
        l.set_color(180, 180, 200)
        l.set_brightness(80)

    # ── phase 1: first distant lightning ──
    @at(4000, "⚡ distant flash")
    def _(l, w, v, s):
        l.set_color(255, 255, 240)
        l.set_brightness(230)

    @at(4150, "flash fades")
    def _(l, w, v, s):
        l.set_color(180, 180, 200)
        l.set_brightness(80)

    @at(4200, "low rumble")
    def _(l, w, v, s):
        v.set_intensity(30)
        v.set_duration(600)

    # ── phase 2: wind picks up ──
    @at(5000, "wind intensifies")
    def _(l, w, v, s):
        w.set_speed(55)

    @at(5000, "pine scent in the air")
    def _(l, w, v, s):
        s.set_scent("pine", 40)

    # ── phase 3: close lightning strike ──
    @at(7000, "⚡ CLOSE STRIKE!")
    def _(l, w, v, s):
        l.set_color(255, 255, 255)
        l.set_brightness(255)

    @at(7100, "thunderclap")
    def _(l, w, v, s):
        v.set_intensity(85)
        v.set_duration(1200)
        w.set_speed(90)
        w.set_direction("reverse")

    @at(7200, "flash fades")
    def _(l, w, v, s):
        l.set_color(100, 100, 140)
        l.set_brightness(60)

    # ── phase 4: rolling thunder ──
    @at(8500, "rolling thunder")
    def _(l, w, v, s):
        v.set_intensity(50)
        v.set_duration(2000)

    @at(9000, "another flash")
    def _(l, w, v, s):
        l.set_color(200, 200, 255)
        l.set_brightness(180)

    @at(9200, "flash fades")
    def _(l, w, v, s):
        l.set_color(100, 100, 140)
        l.set_brightness(60)

    # ── phase 5: double flash ──
    @at(10000, "⚡ flash")
    def _(l, w, v, s):
        l.set_color(255, 255, 230)
        l.set_brightness(240)

    @at(10080, "flash fades")
    def _(l, w, v, s):
        l.set_color(180, 180, 200)
        l.set_brightness(100)

    @at(10150, "⚡ second flash")
    def _(l, w, v, s):
        l.set_color(255, 240, 200)
        l.set_brightness(220)

    @at(10200, "thunder rumble")
    def _(l, w, v, s):
        v.set_intensity(70)
        v.set_duration(1000)

    @at(10270, "flash fades")
    def _(l, w, v, s):
        l.set_color(150, 150, 180)
        l.set_brightness(80)

    # ── phase 6: heavy rain ──
    @at(11000, "heavy wind + rain")
    def _(l, w, v, s):
        w.set_speed(75)
        w.set_direction("forward")

    @at(11000, "petrichor fills the air")
    def _(l, w, v, s):
        s.set_scent("ocean", 65)

    # ── phase 7: finale ──
    @at(13000, "⚡ GRAND FINALE flash")
    def _(l, w, v, s):
        l.set_color(255, 255, 255)
        l.set_brightness(255)

    @at(13100, "MAX thunder")
    def _(l, w, v, s):
        v.set_intensity(100)
        v.set_duration(1500)

    @at(13150, "flash fades")
    def _(l, w, v, s):
        l.set_color(150, 150, 180)
        l.set_brightness(80)

    @at(13500, "⚡ final flash")
    def _(l, w, v, s):
        l.set_color(200, 180, 255)
        l.set_brightness(200)

    @at(13700, "lights out")
    def _(l, w, v, s):
        l.set_color(60, 60, 80)
        l.set_brightness(30)

    # ── phase 8: fading out ──
    @at(15000, "wind dies down")
    def _(l, w, v, s):
        w.set_speed(20)

    @at(15000, "last gentle rumble")
    def _(l, w, v, s):
        v.set_intensity(15)
        v.set_duration(500)

    @at(15500, "lingering pine")
    def _(l, w, v, s):
        s.set_scent("pine", 10)

    @at(16800, "scene ends")
    def _(l, w, v, s):
        l.set_brightness(0)
        l.set_color(0, 0, 0)
        w.set_speed(0)
        v.set_intensity(0)
        s.stop_scent()

    cues.sort(key=lambda x: x[0])
    return cues


# ── rendering ────────────────────────────────────────────────────────────────


def _bar(value: int, width: int = 20) -> str:
    pct = max(0, min(100, value)) / 100.0
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


def render_device_states(
    light: MockLightDevice,
    wind: MockWindDevice,
    vibe: MockVibrationDevice,
    scent: MockScentDevice,
    elapsed_ms: int,
    total_ms: int,
    current_cue: str = "",
    cue_count: int = 0,
    total_cues: int = 0,
) -> str:
    ls = light.state
    ws = wind.state
    vs = vibe.state
    ss = scent.state

    pct = min(100, int(elapsed_ms / max(1, total_ms) * 100))
    progress = _bar(pct, width=40)

    lines: list[str] = []

    ts = f"{elapsed_ms / 1000:.1f}s / {total_ms / 1000:.1f}s"
    lines.append(
        f"\n{C_BRIGHT}{_B}⚡ THUNDERSTORM SCENE{_R}  "
        f"{C_TIME}{ts}{_R}  [{progress}] {pct}%"
    )

    if current_cue:
        lines.append(f"  {C_FLASH} ▶ {current_cue} {_R}")
    lines.append(f"  {_D}cues: {cue_count}/{total_cues}{_R}")

    lines.append("")

    # Light — RGB swatch + brightness
    r, g, b = ls.get("r", 0), ls.get("g", 0), ls.get("b", 0)
    br = ls.get("brightness", 0)
    swatch = _bg(r, g, b) + "   " + _R if br > 0 else "   "
    lines.append(
        f"  {C_LIGHT}💡 LIGHT{_R}    {swatch}  "
        f"brightness={_bar(br, 12)} {br:3d}  "
        f"RGB({r:3d},{g:3d},{b:3d})"
    )

    # Wind
    speed = ws.get("speed", 0)
    direction = ws.get("direction", "forward")
    arrow = "→" if direction == "forward" else "←"
    lines.append(
        f"  {C_WIND}🌬️ WIND{_R}     {arrow}  "
        f"speed={_bar(speed, 12)} {speed:3d}%  "
        f"dir={direction}"
    )

    # Vibration
    intensity = vs.get("intensity", 0)
    dur = vs.get("duration", 0)
    lines.append(
        f"  {C_VIBE}📳 VIBE{_R}     "
        f"intensity={_bar(intensity, 12)} {intensity:3d}%  "
        f"duration={dur}ms"
    )

    # Scent
    sn = ss.get("scent") or "none"
    si = ss.get("intensity", 0)
    lines.append(
        f"  {C_SCENT}👃 SCENT{_R}    "
        f"type={sn:<10s}  "
        f"intensity={_bar(si, 12)} {si:3d}%"
    )

    return "\n".join(lines)


def _clear_screen() -> None:
    if os.name == "nt":
        _ = os.system("cls")
    else:
        print("\033[2J\033[H", end="")


# ── main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Create devices directly — no manager, no dispatcher, no config
    light = MockLightDevice("storm_light")
    wind = MockWindDevice("storm_wind")
    vibe = MockVibrationDevice("storm_vibe")
    scent = MockScentDevice("storm_scent")

    cues = _build_cues()
    total_ms = cues[-1][0] if cues else 0

    print(C_BRIGHT + _B + "\n" + "=" * 60 + _R)
    print(C_BRIGHT + _B + "  PlaySEM — Thunderstorm Scene Demo" + _R)
    print(C_BRIGHT + _B + "=" * 60 + _R)
    print(f"  {_D}All devices are simulated. No hardware required.{_R}")
    print(
        f"  {_D}{len(cues)} cues across {total_ms / 1000:.0f}s timeline.{_R}"
    )

    print(
        render_device_states(
            light,
            wind,
            vibe,
            scent,
            elapsed_ms=0,
            total_ms=total_ms,
            current_cue="Starting scene...",
            cue_count=0,
            total_cues=len(cues),
        )
    )
    print(f"\n{C_BRIGHT}  Press Ctrl+C to stop at any time{_R}")
    await asyncio.sleep(1.0)

    start = time.monotonic()
    cue_index = 0
    completed = False

    try:
        while not completed:
            now = time.monotonic()
            elapsed_ms = int((now - start) * 1000)

            # Fire any due cues
            while cue_index < len(cues) and cues[cue_index][0] <= elapsed_ms:
                ts, desc, fn = cues[cue_index]
                fn(light, wind, vibe, scent)
                _clear_screen()
                print(
                    render_device_states(
                        light,
                        wind,
                        vibe,
                        scent,
                        elapsed_ms=elapsed_ms,
                        total_ms=total_ms,
                        current_cue=desc,
                        cue_count=cue_index + 1,
                        total_cues=len(cues),
                    )
                )
                cue_index += 1

            if cue_index >= len(cues):
                completed = True
                break

            # Render idle frames (no new cue)
            _clear_screen()
            print(
                render_device_states(
                    light,
                    wind,
                    vibe,
                    scent,
                    elapsed_ms=elapsed_ms,
                    total_ms=total_ms,
                    cue_count=cue_index,
                    total_cues=len(cues),
                )
            )

            # Sleep until next cue or next frame
            next_cue_ms = cues[cue_index][0]
            wait = max(0.02, (next_cue_ms - elapsed_ms) / 1000.0)
            await asyncio.sleep(min(wait, 0.1))

    except KeyboardInterrupt:
        print(f"\n{C_VIBE}  Scene interrupted.{_R}")

    # Final render
    _clear_screen()
    final_ms = int((time.monotonic() - start) * 1000)
    print(
        render_device_states(
            light,
            wind,
            vibe,
            scent,
            elapsed_ms=min(final_ms, total_ms),
            total_ms=total_ms,
            current_cue="🌩️  SCENE COMPLETE" if completed else "⏹️  STOPPED",
            cue_count=cue_index,
            total_cues=len(cues),
        )
    )
    print(
        f"\n{C_BRIGHT}{_B}  {'Thunderstorm finished!' if completed else 'Stopped.'}{_R}"
    )
    print(f"  {_D}{cue_index}/{len(cues)} cues fired.{_R}\n")


if __name__ == "__main__":
    asyncio.run(main())
