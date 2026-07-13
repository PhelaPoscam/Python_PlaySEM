#!/usr/bin/env python3
"""
Virtual Device Lab — interactive REPL for experimenting with sensory effects.

Drives mock light, wind, vibration, and scent devices directly from a
command prompt. No hardware, no config files, no external services, no
effect-mapping layer — just direct device control.

Commands:
    light brightness <0-255>            Set LED brightness
    light color <r> <g> <b>            Set LED color (0-255 each)
    light off                           Turn light off
    wind speed <0-100> [forward|rev]    Set fan speed and direction
    wind off                            Stop fan
    vibe <0-100> [ms]                   Vibrate at intensity for duration
    vibe off                            Stop vibration
    scent <name> [0-100]                Diffuse a scent
    scent off                           Stop scent
    storm                               Run a quick thunderclap burst
    reset                               Reset all devices
    state                               Show current device states
    help                                Show this help
    quit                                Exit

Usage:
    python examples/virtual_lab.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_project_root = Path(__file__).resolve()
for parent in _project_root.parents:
    if (parent / "pyproject.toml").exists():
        _project_root = parent
        break
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from playsem.drivers.mock_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice,
    MockScentDevice,
)

# ── ANSI helpers ─────────────────────────────────────────────────────────

R = "\033[0m"
B = "\033[1m"
D = "\033[2m"


def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


YL = rgb(255, 220, 50)
CY = rgb(100, 200, 255)
RD = rgb(255, 120, 80)
MG = rgb(180, 130, 255)
GR = rgb(100, 255, 100)
GY = rgb(150, 150, 150)


def _bar(value: int, width: int = 15) -> str:
    pct = max(0, min(100, value)) / 100.0
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


SCENTS = {"rose", "ocean", "coffee", "pine", "vanilla", "citrus"}


def show_state(light, wind, vibe, scent):
    """Pretty-print all device states."""
    ls, ws, vs, ss = light.state, wind.state, vibe.state, scent.state

    print(f"\n{B}  ── DEVICE STATES ──{R}\n")

    r, g, b = ls.get("r", 0), ls.get("g", 0), ls.get("b", 0)
    br = ls.get("brightness", 0)
    swatch = f"\033[48;2;{r};{g};{b}m   \033[0m" if br > 0 else "   "
    print(
        f"  {YL}💡 LIGHT{R}    {swatch}  "
        f"brightness={_bar(br)} {br:3d}  RGB({r:3d},{g:3d},{b:3d})"
    )

    speed = ws.get("speed", 0)
    direction = ws.get("direction", "forward")
    arrow = "→" if direction == "forward" else "←"
    print(
        f"  {CY}🌬️ WIND{R}     {arrow}  "
        f"speed={_bar(speed)} {speed:3d}%  dir={direction}"
    )

    intensity = vs.get("intensity", 0)
    dur = vs.get("duration", 0)
    print(
        f"  {RD}📳 VIBE{R}     intensity={_bar(intensity)} {intensity:3d}%  "
        f"duration={dur}ms"
    )

    sn = ss.get("scent") or "none"
    si = ss.get("intensity", 0)
    print(f"  {MG}👃 SCENT{R}    type={sn:<10s} intensity={_bar(si)} {si:3d}%")


async def interactive_loop(light, wind, vibe, scent):
    """Main REPL."""

    print(f"\n{B}  ⚡ PlaySEM Virtual Device Lab{R}")
    print(f"  {D}Type 'help' for commands, 'quit' to exit.{R}")
    print(f"  {D}All devices are simulated — experiment freely!{R}")

    show_state(light, wind, vibe, scent)

    while True:
        try:
            raw = input(f"\n{B}lab>{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            break

        elif cmd in ("help", "h", "?"):
            print(
                f"""
  {B}Commands:{R}
    {YL}light brightness <0-255>{R}            Set LED brightness
    {YL}light color <r> <g> <b>{R}            Set LED color (0-255 each)
    {YL}light off{R}                           Turn light off
    {CY}wind speed <0-100> [forward|rev]{R}    Set fan speed and direction
    {CY}wind off{R}                            Stop fan
    {RD}vibe <0-100> [ms]{R}                  Vibrate at intensity
    {RD}vibe off{R}                            Stop vibration
    {MG}scent <name> [0-100]{R}               Diffuse a scent
    {MG}scent off{R}                           Stop scent
    {B}storm{R}                                 Run a lightning burst
    {B}reset{R}                                 Reset all devices
    {B}state{R}                                 Show device states
    {B}help{R}                                  This message
    {B}quit{R}                                  Exit

  {D}Scent options:{R} {', '.join(sorted(SCENTS))}
"""
            )

        elif cmd == "state":
            show_state(light, wind, vibe, scent)

        elif cmd == "reset":
            light.reset()
            wind.reset()
            vibe.reset()
            scent.reset()
            print(f"  {GR}✓ all devices reset{R}")

        elif cmd == "storm":
            print(f"\n  {YL}⚡ Thunderclap!{R}")
            light.set_color(255, 255, 255)
            light.set_brightness(255)
            await asyncio.sleep(0.08)
            vibe.set_intensity(90)
            vibe.set_duration(400)
            wind.set_speed(80)
            wind.set_direction("reverse")
            scent.set_scent("ocean", 60)
            await asyncio.sleep(0.2)
            light.set_brightness(0)
            light.set_color(0, 0, 0)
            await asyncio.sleep(0.3)
            wind.set_speed(10)
            wind.set_direction("forward")
            print(f"  {GR}✓ burst complete{R}")
            show_state(light, wind, vibe, scent)

        elif cmd == "light":
            if len(parts) < 2:
                print(
                    f"  {RD}usage: light <brightness|color|off> [args...]{R}"
                )
                continue
            sub = parts[1].lower()
            if sub == "off":
                light.set_brightness(0)
                light.set_color(0, 0, 0)
            elif sub == "brightness" and len(parts) >= 3:
                try:
                    light.set_brightness(int(parts[2]))
                except ValueError:
                    print(f"  {RD}brightness must be a number 0-255{R}")
                    continue
            elif sub == "color" and len(parts) >= 5:
                try:
                    light.set_color(
                        int(parts[2]), int(parts[3]), int(parts[4])
                    )
                except ValueError:
                    print(f"  {RD}color values must be numbers 0-255{R}")
                    continue
            else:
                print(
                    f"  {RD}usage: light brightness <0-255>  |  light color <r> <g> <b>  |  light off{R}"
                )
                continue
            show_state(light, wind, vibe, scent)

        elif cmd == "wind":
            if len(parts) < 2:
                print(f"  {RD}usage: wind <speed|off> [args...]{R}")
                continue
            sub = parts[1].lower()
            if sub == "off":
                wind.set_speed(0)
            elif sub == "speed" and len(parts) >= 3:
                try:
                    wind.set_speed(int(parts[2]))
                except ValueError:
                    print(f"  {RD}speed must be a number 0-100{R}")
                    continue
                if len(parts) >= 4:
                    d = parts[3].lower()
                    if d in ("forward", "fwd", "f"):
                        wind.set_direction("forward")
                    elif d in ("reverse", "rev", "r"):
                        wind.set_direction("reverse")
            else:
                # shorthand: wind <speed> [direction]
                try:
                    wind.set_speed(int(parts[1]))
                except ValueError:
                    print(
                        f"  {RD}usage: wind speed <0-100> [forward|rev]  |  wind off{R}"
                    )
                    continue
                if len(parts) >= 3:
                    d = parts[2].lower()
                    if d in ("forward", "fwd", "f"):
                        wind.set_direction("forward")
                    elif d in ("reverse", "rev", "r"):
                        wind.set_direction("reverse")
            show_state(light, wind, vibe, scent)

        elif cmd in ("vibe", "vibration"):
            if len(parts) < 2:
                print(
                    f"  {RD}usage: vibe <0-100> [duration_ms]  |  vibe off{R}"
                )
                continue
            if parts[1].lower() == "off":
                vibe.set_intensity(0)
                vibe.set_duration(0)
            else:
                try:
                    vibe.set_intensity(int(parts[1]))
                except ValueError:
                    print(f"  {RD}intensity must be a number 0-100{R}")
                    continue
                if len(parts) >= 3:
                    try:
                        vibe.set_duration(int(parts[2]))
                    except ValueError:
                        print(f"  {RD}duration must be a number (ms){R}")
                        continue
            show_state(light, wind, vibe, scent)

        elif cmd == "scent":
            if len(parts) < 2:
                print(f"  {RD}usage: scent <name|off> [intensity 0-100]{R}")
                continue
            if parts[1].lower() == "off":
                scent.stop_scent()
            else:
                name = parts[1].lower()
                if name not in SCENTS:
                    print(
                        f"  {RD}unknown scent: {name}. "
                        f"Valid: {', '.join(sorted(SCENTS))}{R}"
                    )
                    continue
                intensity = int(parts[2]) if len(parts) > 2 else 50
                scent.set_scent(name, intensity)
            show_state(light, wind, vibe, scent)

        else:
            print(f"  {RD}unknown: {cmd}. Type 'help'.{R}")


async def main():
    light = MockLightDevice("lab_light")
    wind = MockWindDevice("lab_wind")
    vibe = MockVibrationDevice("lab_vibe")
    scent = MockScentDevice("lab_scent")

    try:
        await interactive_loop(light, wind, vibe, scent)
    finally:
        pass  # mock devices need no cleanup

    print(f"\n  {D}Lab closed.{R}\n")


if __name__ == "__main__":
    asyncio.run(main())
