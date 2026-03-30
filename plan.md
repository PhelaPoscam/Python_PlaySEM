# Phase 3 Modular Server Restoration Plan

Date: 2026-03-30
Status: In Progress

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

## 1. Verified Current State

- The modular server structure expected by platform examples is missing.
- `examples/platform/basic_server.py` imports `tools.test_server.app.create_app` and `tools.test_server.config.ServerConfig`, but those modules do not exist.
- Current implementation is monolithic in `tools/test_server/main.py` (~1075 lines) with routes and business logic centralized.
- Full `pytest` currently passes, which means existing tests do not catch this architecture/example drift.

## 2. Objectives

1. Restore a clean modular server architecture under `tools/test_server/`.
2. Keep runtime compatibility while migrating from monolith.
3. Make `examples/platform/basic_server.py` runnable again.
4. Add tests that validate `create_app` and core endpoints.
5. Update status/documentation only after implementation is truly complete.

## 3. Scope

### In Scope

- New modular layout:
  - `tools/test_server/app/__init__.py`
  - `tools/test_server/app/main.py`
  - `tools/test_server/services/device_service.py`
  - `tools/test_server/services/effect_service.py`
  - `tools/test_server/services/protocol_service.py`
  - `tools/test_server/routes/devices.py`
  - `tools/test_server/routes/effects.py`
  - `tools/test_server/routes/ui.py`
  - `tools/test_server/dependencies.py`
  - `tools/test_server/config.py`
- Compatibility wrapper strategy in `tools/test_server/main.py`.
- Example fix: `examples/platform/basic_server.py`.
- Tests for app factory and key endpoints.

### Out of Scope (for now)

- Deep behavior redesign of protocol handlers.
- Large API contract changes unrelated to modularization.
- Unrelated docs cleanup beyond touched architecture/status docs.

## 4. Execution Strategy (One by One)

### Step 1 - Baseline + Safety Net

- Add new integration tests for:
  - app factory creation (`create_app`)
  - `GET /health`
  - `GET /api/devices` (empty list baseline)
  - WebSocket connect to `/ws`
- Keep these tests initially xfail/guarded only if imports are unavailable, then make them pass as we implement.

Exit criteria:
- New tests exist and are wired into suite.
- Failure mode clearly indicates missing modular architecture.

### Step 2 - Config + Factory Skeleton

- Implement `tools/test_server/config.py` with `ServerConfig` (Pydantic).
- Implement `tools/test_server/app/main.py` with `create_app(config: ServerConfig | None = None)`.
- Export from `tools/test_server/app/__init__.py`.

Exit criteria:
- `create_app()` returns a FastAPI app.
- Startup does not crash.

### Step 3 - Service Layer Extraction

- Create `DeviceService`, `EffectService`, `ProtocolService`.
- Move business logic from monolith into services incrementally.

Exit criteria:
- Services are independently importable and unit-testable.
- No route directly contains heavy business logic.

### Step 4 - Dependency Injection Layer

- Create `tools/test_server/dependencies.py`.
- Provide dependency providers (config + services).

Exit criteria:
- Routes receive dependencies via FastAPI `Depends`.
- Minimal global state in route modules.

### Step 5 - Route Modularization

- Build route modules:
  - `routes/devices.py`
  - `routes/effects.py`
  - `routes/ui.py`
- Include routers in `create_app`.

Exit criteria:
- Existing endpoint behavior preserved for key APIs.
- `/health`, `/api/devices`, `/ws` function from modular app.

### Step 6 - Compatibility Wrapper in main.py

- Replace monolithic logic with thin compatibility entrypoint:
  - imports `create_app`
  - keeps current launch ergonomics where possible
- Optionally keep a temporary legacy module snapshot (non-default runtime path) until stabilization.

Exit criteria:
- Existing run paths do not break unexpectedly.
- Monolith is no longer source of truth.

### Step 7 - Example + Docs Alignment

- Verify/fix `examples/platform/basic_server.py` against restored architecture.
- Update README status table only once implementation and tests are green.

Exit criteria:
- Example runs successfully.
- Documentation reflects actual state (no false-complete claims).

### Step 8 - Final Validation

Automated:
- Run full `pytest` and ensure no regressions.

Manual:
- Start example server.
- Verify:
  - `GET /health` returns OK.
  - `GET /api/devices` returns empty list by default.
  - WebSocket connection to `/ws` succeeds.

Exit criteria:
- Automated + manual checks pass.

## 5. Risk Controls

- Migrate in small, reviewable commits by step.
- Keep compatibility wrapper while moving logic.
- Avoid problematic naming (`modules.py`), use explicit `services/` and `routes/`.
- Keep ASCII-safe file content and deterministic imports.

## 6. Definition of Done

- Modular architecture exists and is the runtime source of truth.
- Platform examples run without import errors.
- New factory/endpoint tests pass.
- Full test suite passes.
- README status is accurate.

## 7. Immediate Next Action

Proceed with Step 1 now: add modular app integration tests (factory + `/health` + `/api/devices` + `/ws`) and run targeted tests first.
