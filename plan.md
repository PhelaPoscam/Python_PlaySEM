# Phase 3 Modular Server Restoration Plan

Date: 2026-03-30
Status: Verification & CI Fixes (Step 8 Complete, pending CI)

## Progress Log

- [x] Step 1 started and implemented: modular factory integration tests created.
- [x] Baseline validated: tests currently `xfail` because `tools.test_server.app` is missing.
- [x] Step 2 implemented: added `ServerConfig` and `create_app` skeleton.
- [x] Step 2 validation: `tests/integration/test_modular_app_factory.py` now passes (4/4).
- [x] Step 3 implemented: extracted `DeviceService`, `EffectService`, and `ProtocolService`.
- [x] Step 3 validation: service unit tests + factory integration tests pass (7/7).
- [x] Step 4 implemented: added `dependencies.py` providers for config/services.
- [x] Step 4 validation: factory and service tests still pass (7/7).
- [x] Step 5 implemented: modularized route handlers into `routes/devices.py`, `routes/effects.py`, and `routes/ui.py`.
- [x] Step 5 validation: modular + service + API contract targeted tests pass (10/10).
- [x] Step 6 implemented: `tools/test_server/main.py` now exports runtime `app` from modular `create_app` while preserving legacy `ControlPanelServer` for compatibility tests.
- [x] Step 6 validation: targeted integration tests pass and `/health`, `/api/stats`, `/api/devices` return 200 via module-level `app`.
- [x] Step 7 implemented: verified `examples/platform/basic_server.py` startup and aligned README status to restored modular runtime.
- [x] Step 8 validation complete: full `pytest -q` passes after restoring WebSocket discovery behavior in modular app.

---

## 8. Plan Status Analysis (Current State)

### Summary

All 8 steps of the Phase 3 Modular Server Restoration are marked **complete** in the progress log. The modular architecture has been fully implemented. However, CI is currently failing due to two issues caught after the push.

### Modular Architecture — Implemented Files

All planned files exist and are properly wired:

| File | Status | Notes |
| :--- | :--- | :--- |
| **config.py** | ✅ Created | `ServerConfig` Pydantic model |
| **app/`__init__`.py** | ✅ Created | Exports `create_app` |
| **app/main.py** | ✅ Created | App factory with service wiring |
| **services/device_service.py** | ✅ Created | Device management logic |
| **services/effect_service.py** | ⚠️ Modified locally | Fixed `datetime.UTC` → `timezone.utc` (uncommitted) |
| **services/protocol_service.py** | ✅ Created | Protocol discovery tracking |
| **routes/devices.py** | ✅ Created | Device API routes |
| **routes/effects.py** | ✅ Created | Effect API routes |
| **routes/ui.py** | ✅ Created | UI serving routes |
| **dependencies.py** | ✅ Created | FastAPI `Depends` providers |
| **main.py** | ✅ Updated | Compatibility wrapper + legacy `ControlPanelServer` |
| **basic_server.py** | ✅ Updated | Now uses `create_app` + `ServerConfig` |

### Test Files Created

| File | Notes |
| :--- | :--- |
| **test_modular_app_factory.py** | Factory + endpoint integration tests |
| **test_modular_services.py** | Service unit tests |

### CI Failures — 2 Issues Found

The CI run (#61) failed on both macOS 3.10 and Windows 3.10 matrices.

#### Issue 1: `datetime.UTC` not available in Python 3.10

> [!IMPORTANT]
> `datetime.UTC` was introduced in Python 3.11. The project targets `>=3.10`.


- **Root cause**: `tools/test_server/services/effect_service.py` used `from datetime import UTC, datetime`
- **Status**: ✅ **Fixed locally** (changed to `from datetime import datetime, timezone` + `timezone.utc`), but **not yet committed/pushed**.

The fix is in git diff — 2 uncommitted files:
- **plan.md** — updated progress log
- **tools/test_server/services/effect_service.py** — UTC fix

#### Issue 2: `black` formatting violations in 6 files

> [!WARNING]
> CI reported 6 files would be reformatted by `black`.

The 6 files flagged:
1. `playsem/protocol_servers/coap_server.py`
2. `playsem/protocol_servers/http_server.py`
3. `playsem/protocol_servers/mqtt_server.py`
4. `playsem/protocol_servers/websocket_server.py`
5. `playsem/protocol_servers/upnp_server.py`
6. `tests/protocols/test_upnp_server.py`

**Status**: ✅ **All 6 files pass `black --check` locally now** (58 files unchanged, 0 would be reformatted). This suggests the formatting was fixed in a commit after the CI failure, or the CI was running a different `black` version.

### What Needs To Happen Next

> [!CAUTION]
> The `effect_service.py` fix is **uncommitted**. CI will keep failing until it's pushed.

1. **Commit and push** the 2 modified files (`effect_service.py` + `plan.md`)
2. **Verify CI passes** on all matrix targets (ubuntu, macos, windows × Python 3.10, 3.11, 3.12)
3. If `black` still fails in CI, check for version mismatch between local and CI `black` versions

### Quick Status

| Area | Local | CI (Remote) |
| :--- | :--- | :--- |
| **Modular architecture** | ✅ Complete | ✅ Complete |
| **`datetime.UTC` fix** | ✅ Fixed | ❌ Not pushed |
| **`black` formatting** | ✅ Passes | ❓ Needs re-run |
| **Full `pytest`** | ✅ Passes (step 8) | ❌ Blocked by import error |



