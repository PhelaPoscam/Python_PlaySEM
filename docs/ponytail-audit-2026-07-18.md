# Ponytail Audit — Python_PlaySEM
**Date:** 2026-07-18
**Repo:** ~24,200 LOC Python, 121 files, 39 test files
**Verdict:** The core library is well-structured. The test server (`tools/test_server/`) is the primary source of bloat — a 1,111-line legacy monolith coexists with its modular replacement. Duplication is the biggest time-sink: 7 patterns copy-pasted across 30+ files.

---

## 1. DELETE — Dead code, unreachable files

| # | Location | What | Why |
|---|----------|------|-----|
| 1 | `tools/test_server/handlers.py` | 21-line shim re-exporting from `handlers/` package | Unreachable — Python's package `handlers/` wins at import time. This file is dead. |
| 2 | `tests/integration/conftest.py` | 8 lines of `sys.path.insert` | Root `tests/conftest.py:12,18` already does this. Integration conftest is redundant. |
| 3 | `.editorconfig:59` | `legacy_backup/**` exclusion | Directory does not exist on disk. Orphan config. |
| 4 | `tools/__init__.py` | Empty file | `tools/` is not a package — nothing imports from it. |
| 5 | `examples/__init__.py` | Empty file | Same — not a package. |

**Impact:** ~30 lines deleted, zero risk.

---

## 2. SIMPLIFY — Reduce, merge, or collapse

### 2a. Legacy `ControlPanelServer` — 1,111 lines
- **File:** `tools/test_server/main.py`
- **Issue:** The modular server (`tools/test_server/app/main.py`, 419 lines) exists alongside the monolithic `ControlPanelServer` (1,111 lines). The monolith is instantiated at module level (`server = ControlPanelServer()` on line 1073), exposing `server` and `legacy_app` globals.
- **Fix:** Pick one. Either delete the monolith and migrate all callers to `app/main.py`, or mark it `ponytail:` and freeze it.
- **Decision required.** ~1,100 lines at stake.

### 2b. `_LegacyPublishDriver` — 30 lines
- **File:** `playsem/device_manager.py:788-817`
- **Issue:** A minimal driver wrapper for legacy tests that use `client.publish()`. Referenced at line 88.
- **Fix:** Audit whether the tests that need this can use `MockConnectivityDriver` directly instead. If yes, delete.

### 2c. `_DummyTimeline` / `_DummyDispatcher` stubs
- **File:** `tools/test_server/main.py:104-128`
- **Issue:** Inline stub classes that print to stdout. `playsem` already has `Timeline` (403 lines) and `EffectDispatcher` (736 lines).
- **Fix:** These stubs only exist because the legacy server doesn't use real playsem objects. If the monolith is deleted (see 2a), these go with it.

### 2d. `EffectDispatcher` — 8 public dispatch methods
- **File:** `playsem/effect_dispatcher.py`
- Methods:
  - `dispatch_effect()` (L177) — sync, returns bool
  - `dispatch_effect_result()` (L205) — sync, returns `DispatchResult`
  - `dispatch_effect_metadata()` (L341) — sync, metadata variant
  - `dispatch_effect_metadata_result()` (L362) — sync, metadata+result
  - `async_dispatch_effect()` — async mirror
  - `async_dispatch_effect_result()` — async mirror
  - `async_dispatch_effect_metadata()` — async mirror
  - `async_dispatch_effect_metadata_result()` — async mirror
- **Fix:** The 4 sync methods delegate to async via `_run_awaitable_blocking`. Consider collapsing to 2 async methods + sync wrappers, or 4 methods total with a `result_format` parameter instead of `_result` / `_metadata_result` suffixes.

### 2e. `DeviceManager` — 3 initialization modes, 4 connect methods
- **File:** `playsem/device_manager.py`
- **Issue:** Multi-driver, single-driver, and legacy-client init modes. Connect: `connect_all`, `async_connect_all`, `connect_device`, `async_connect_device`.
- **Fix:** Mark the legacy-client mode `ponytail:` or delete it. The 4 connect methods are defensible (sync/async × all/one) but document which are primary.

### 2f. `os._exit(0)` force-exit
- **File:** `tools/test_server/main.py:1077`
- **Issue:** Bypasses all cleanup. Use `sys.exit(0)` unless there's a documented reason for the hard kill.

---

## 3. DEDUPLICATE — Same logic, multiple copies

### 3a. `get_local_ip()` — 6 copies
Identical 8-line socket function in:
- `tools/websocket/server.py:48`
- `examples/protocols/websocket_demo.py:47`
- `examples/protocols/upnp_demo.py:34`
- `examples/protocols/coap_demo.py:47`
- `examples/protocols/mqtt_demo.py:47`
- `examples/protocols/http_demo.py:48`

**Fix:** Extract to `playsem/utils/network.py` → `get_local_ip()`. Import from there.

### 3b. `"type": "device_list"` broadcast payload — 9 sites
Inline dict construction at:
- `tools/test_server/main.py:285, 425, 462, 631, 935, 940`
- `tools/test_server/app/main.py:105, 145, 157`

**Fix:** Single helper `_device_to_dict(device) -> dict` returning the canonical 8-field shape. Call from all 9 sites.

### 3c. Protocol endpoint defaults block — 4 copies
The `if "mqtt" in protocols and "mqtt" not in endpoints:` pattern:
- `tools/test_server/main.py:133, 368-406`
- `tools/test_server/app/main.py:181-187`
- `tools/test_server/services/protocol_service.py:228-253` (canonical)

**Fix:** Import from `protocol_service.py`. Delete inline copies.

### 3d. `MockClient = type("MockClient", (), {...})()` — 4 copies
Identical inline dynamic mock:
- `tools/coap/server.py:55`
- `tools/mqtt/server_public.py:59`
- `tools/mqtt/server.py:65`
- `tools/websocket/server.py:91`

**Fix:** Extract to `playsem/testing.py` or a shared `tools/common.py`.

### 3e. `_env_int()` + port constants — 2 copies
Identical function + 4 port constants in:
- `tools/test_server/main.py:39-54`
- `tools/test_server/app/main.py:29-44`

**Fix:** Move to `tools/test_server/config.py` (which already exists with `ServerConfig`).

### 3f. `ConnectedDevice` dataclass — 2 copies
- `tools/test_server/main.py:58-81` (plain class, 24 lines)
- `tools/test_server/services/device_service.py:8` (`@dataclass`)

**Fix:** Single definition in `device_service.py`. Delete from `main.py`, import if needed.

### 3g. `sys.path.insert(0, ...)` — ~30 files
Nearly every demo, tool, and test script bootstraps its own path.
- **Tests:** Already covered by `pythonpath = .` in `pytest.ini`. The `sys.path.insert` in `tests/conftest.py:12,18` and `tests/integration/conftest.py:8` are redundant.
- **Tools/examples:** These need it because they're run as scripts, not installed packages. Acceptable but noisy.

**Fix:** Install the package in editable mode (`pip install -e .`) — then remove all `sys.path.insert` from tests. For tools/examples, the `sys.path.insert` is a known tradeoff and should be marked `ponytail:` at the top of each file.

### 3h. `register_device()` — 5 implementations
- `playsem/device_registry.py:130` — canonical, correct
- `playsem/drivers/mock_driver.py:340` — delegates to registry, legitimate
- `tools/test_server/main.py:668` — HTTP endpoint handler, legitimate (route, not method)
- `tools/test_server/services/device_service.py:27` — service method, legitimate
- `tools/test_server/routes/devices.py:26` — FastAPI route, legitimate

**Fix:** The 4 test_server instances are legitimate route/service layers, not duplication. No action needed.

---

## 4. REPLACE — Stdlib or existing deps

### 4a. Custom `.env` parser — 44 lines
- **File:** `tools/test_server/env_loader.py`
- **Issue:** Hand-rolled line-by-line parser with quote stripping. `python-dotenv` is NOT a dependency.
- **Fix:** This is 44 lines of working code. Adding `python-dotenv` adds a dep for no real gain. **Keep as-is**, mark `ponytail:`.

### 4b. Custom XML serializer — 70 lines
- **File:** `playsem/utils/serializer.py:36-76`
- **Issue:** `_sanitize_xml_tag()` + `_build_xml_tree()` + `serialize_to_xml()` are hand-rolled. `xmltodict` IS a dependency (used in `ConfigLoader`).
- **Fix:** Replace `serialize_to_xml()` with `xmltodict.unparse()`. Delete ~40 lines.

### 4c. `SlidingWindowLimiter` — 96 lines
- **File:** `playsem/utils/rate_limiter.py`
- **Issue:** Custom sliding-window rate limiter.
- **Fix:** **Keep.** 96 lines, thread-safe, no external dep needed. Mark `ponytail:` noting the ceiling (single-process, in-memory).

### 4d. `json_default()` — 12 lines
- **File:** `playsem/utils/serializer.py:15-27`
- **Issue:** Custom fallback for datetime, Decimal, UUID, bytes, set.
- **Fix:** **Keep.** This is exactly what `json_default` should be — minimal and explicit.

### 4e. `retry_policy.py` — 33 lines
- **File:** `playsem/drivers/retry_policy.py`
- **Issue:** Bounded exponential backoff dataclass.
- **Fix:** **Keep.** 33 lines, no dep needed.

---

## 5. CONFIG INCONSISTENCY

| Tool | Line length | Source |
|------|-------------|--------|
| `.editorconfig` | **79** | `max_line_length = 79` |
| `.flake8` | **100** | `max-line-length = 100` |
| `black` | **88** | `pyproject.toml` line-length = 88 |

Three different standards. Black enforces 88 at commit time, but `.editorconfig` tells editors to wrap at 79, and flake8 allows 100. **Pick one** (88 is the sensible default since black enforces it).

### CI gaps
- No `mypy` in CI (configured in pyproject.toml but never run)
- No `pytest --cov` (pytest-cov is a dev dep but unused)
- `demo-smoke` job has `continue-on-error: true` — failures are invisible

---

## 6. SHORTCUT LEDGER — Unmarked `ponytail:` violations

Only **1** `ponytail:` comment exists in the entire codebase (`tools/websocket/server.py:30`). The following shortcuts should be marked:

| Location | Shortcut | Mark |
|----------|----------|------|
| `tools/test_server/main.py:1073` | Module-level `server = ControlPanelServer()` | `ponytail: legacy global, delete when monolith is removed` |
| `tools/test_server/main.py:104-108` | `_DummyTimeline` stub | `ponytail: stub for shutdown tests, replaced by real Timeline when monolith removed` |
| `tools/test_server/main.py:1077` | `os._exit(0)` | `ponytail: hard exit, bypasses cleanup` |
| `playsem/device_manager.py:788` | `_LegacyPublishDriver` | `ponytail: kept for legacy test compat, delete when tests migrate to MockConnectivityDriver` |
| `playsem/device_manager.py:~600-655` | `_run_awaitable_blocking()` event-loop-in-thread | `ponytail: sync/async bridge via thread+new loop, replace with asyncio.run when sync API is dropped` |
| `tools/test_server/main.py` (broadcast loops) | Bare `except Exception: pass` | `ponytail: silent failure in broadcast, log+reconnect when production-ready` |
| ~30 tool/example files | `sys.path.insert(0, ...)` | `ponytail: script path bootstrap, remove when package is pip-installed` |
| `tests/conftest.py:169` | `except Exception: pass` in fixture teardown | `ponytail: swallow teardown errors, log when tests are stable` |

### `except Exception` density
**148 occurrences across 45 files.** Heaviest concentrations:
- `playsem/device_manager.py`: 14
- `tools/test_server/main.py`: 18
- `playsem/drivers/bluetooth_driver.py`: 11
- `playsem/protocol_servers/mqtt_server.py`: 10

Many are legitimate (driver error handling, protocol server resilience). The concern is the ~30% that are bare `pass` — these swallow real errors silently.

---

## 7. PRIORITY RANKING — What to do first

| Priority | Action | LOC impact | Risk |
|----------|--------|-----------|------|
| **P0** | Delete `tools/test_server/handlers.py` | -21 | None |
| **P0** | Delete `tests/integration/conftest.py` | -8 | None |
| **P0** | Remove orphan `.editorconfig:59` | -3 | None |
| **P1** | Decide on legacy `ControlPanelServer` | -1,111 or +ponytail | Medium |
| **P1** | Extract `get_local_ip()` to shared util | -40 net | Low |
| **P1** | Single `device_list` payload helper | -60 net | Low |
| **P1** | Consolidate protocol endpoint defaults | -50 net | Low |
| **P2** | Extract `MockClient` to shared util | -12 net | Low |
| **P2** | Move `_env_int` + ports to `config.py` | -16 net | Low |
| **P2** | Replace XML serializer with `xmltodict.unparse()` | -40 | Low |
| **P2** | Unify line-length config (pick 88) | 0 | Low |
| **P3** | Mark 8 shortcuts with `ponytail:` comments | 0 | None |
| **P3** | Add mypy + coverage to CI | 0 | Low |
| **P3** | Collapse `EffectDispatcher` 8→4 methods | -100 | Medium |
| **P4** | Remove `sys.path.insert` from tests (pip install -e) | -30 net | Low |
| **P4** | Audit `_LegacyPublishDriver` for deletion | -30 | Low |

**Total P0:** 32 lines, zero risk. Start here.
**Total P0–P2:** ~1,400 lines of deletion/simplification.

---

## 8. WHAT'S GOOD — Keep these

- **Core library structure** (`playsem/`) — clean separation of concerns, well-factored ABCs with multiple real implementations
- **Optional dependency pattern** (`_optional_import` in `utils/__init__.py`) — lazy, no mandatory heavy deps
- **`SlidingWindowLimiter`** — 96 lines, no deps, thread-safe. Correct abstraction level.
- **`retry_policy.py`** — 33 lines, dataclass, zero magic
- **`json_default()`** — minimal, explicit, correct
- **`EffectMetadata` + `EffectMetadataParser`** — well-separated data + parsing
- **`CommandEnvelope`** — frozen dataclass, immutable, correct
- **Protocol server separation** — each protocol is self-contained, optional, and independently testable
- **Test organization** — unit/integration/protocols split with auto-marking via conftest hooks
- **CI structure** — lint/test/smoke separation is correct

---

## Summary

**Biggest win:** Delete the legacy `ControlPanelServer` monolith (1,111 lines). It coexists with its modular replacement and nothing else uses it.

**Quick wins:** P0 items (32 lines, zero risk).

**Biggest pattern:** Duplication. The same 7 patterns are copy-pasted across 30+ files. Extracting them to shared utilities is mechanical and low-risk.

**Debt:** The `ponytail:` discipline is documented in `AGENTS.md` but only 1 comment exists. The 8 unmarked shortcuts above should be cataloged before more accumulate.
