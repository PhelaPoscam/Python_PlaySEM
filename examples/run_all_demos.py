#!/usr/bin/env python3
"""
Run all PlaySEM protocol demos in sequence.

Boots each embedded protocol server (HTTP, WebSocket, MQTT, CoAP, UPnP) in
turn, sends real effects through it, prints what was received, and exits 0
on full success or 1 if any demo fails. Designed to be the single command
"does PlaySEM work?" smoke test for humans and CI.

Usage:
    python examples/run_all_demos.py
    python examples/run_all_demos.py --only http,websocket
    python examples/run_all_demos.py --json  # machine-readable output
"""

import argparse
import asyncio
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEMO_DIR = Path(__file__).resolve().parent / "protocols"
AVAILABLE = ["http", "websocket", "mqtt", "coap", "upnp"]


def _load_demo(name: str) -> Callable[[], Awaitable[int]]:
    """Load a demo module by filename and return its main() coroutine."""
    path = DEMO_DIR / f"{name}_demo.py"
    spec = importlib.util.spec_from_file_location(f"demo_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load demo spec: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def _split_selectors(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


async def run_one(name: str, results: List[Dict[str, Any]]) -> bool:
    """Run a single demo by name, record the outcome, return success."""
    started = time.monotonic()
    print(f"\n{'=' * 60}\n[{name.upper()}] starting\n{'=' * 60}")
    try:
        main = _load_demo(name)
        exit_code = await main()
        elapsed = time.monotonic() - started
        ok = exit_code == 0
        results.append(
            {
                "demo": name,
                "ok": ok,
                "elapsed_s": round(elapsed, 2),
                "exit_code": exit_code,
            }
        )
        print(f"\n[{name.upper()}] {'OK' if ok else 'FAILED'} in {elapsed:.2f}s")
        return ok
    except SystemExit as exc:
        elapsed = time.monotonic() - started
        ok = exc.code in (0, None)
        results.append(
            {
                "demo": name,
                "ok": ok,
                "elapsed_s": round(elapsed, 2),
                "exit_code": exc.code,
                "via": "SystemExit",
            }
        )
        print(f"\n[{name.upper()}] {'OK' if ok else 'FAILED'} (SystemExit {exc.code})")
        return ok
    except Exception as exc:
        elapsed = time.monotonic() - started
        results.append(
            {
                "demo": name,
                "ok": False,
                "elapsed_s": round(elapsed, 2),
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=4).splitlines(),
            },
        )
        print(f"\n[{name.upper()}] CRASHED: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        default=",".join(AVAILABLE),
        help=f"Comma-separated demo names. Available: {','.join(AVAILABLE)}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON summary at the end (also useful for CI).",
    )
    args = parser.parse_args()

    selected = _split_selectors(args.only)
    unknown = [s for s in selected if s not in AVAILABLE]
    if unknown:
        print(f"Unknown demo(s): {unknown}. Available: {AVAILABLE}")
        return 2

    results: List[Dict[str, Any]] = []
    overall_ok = True
    for name in selected:
        ok = await run_one(name, results)
        overall_ok = overall_ok and ok
        await asyncio.sleep(0.5)  # let prior broker release its socket

    print(f"\n{'=' * 60}\nSUMMARY\n{'=' * 60}")
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        elapsed = r.get("elapsed_s", 0.0)
        print(f"  [{status}] {r['demo']:<10} {elapsed:>6.2f}s")
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"\n{passed}/{total} demos passed")

    if args.json:
        print("\n--- JSON ---")
        print(
            json.dumps({"passed": passed, "total": total, "results": results}, indent=2)
        )

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
