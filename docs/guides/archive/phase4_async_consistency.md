# Phase 4 Async Consistency Decision

Date: 2026-04-13
Status: Completed

## Decision

Selected strategy: keep `DeviceManager` synchronous and use explicit async bridge adapters.

Rationale:

1. Preserves backwards compatibility for existing sync call sites.
2. Avoids broad breaking changes across protocol servers, tests, and examples.
3. Enables incremental migration path for async-capable drivers.

## Implemented Behavior

1. Single-driver mode (`connectivity_driver`) now supports sync and async driver methods.
2. Mapped multi-driver mode now supports sync and async methods for:
   - `is_connected`
   - `connect`
   - `disconnect`
   - `send_command`
3. Async bridge executes awaitables:
   - directly with `asyncio.run` when no loop is running
   - in an isolated thread loop when called from an active event loop
4. Timeout guard added via `async_bridge_timeout` in `DeviceManager`.
   - default: `5.0` seconds
   - set `None` to disable timeout
   - set `None` to disable timeout

## Runtime Integration in Phase 3/4

1. Managed queue processing is integrated behind runtime flags in:
   - `Timeline` via `process_managed_queue`
   - `WebSocketServer` via `process_managed_queue`
2. Defaults remain backward-compatible (`False`).

## Validation Summary

1. DeviceManager bridge tests pass for:
   - async single-driver send/connect/disconnect
   - async mapped driver connect/send/disconnect
   - mixed sync+async burst dispatch
   - timeout failure path
2. Dispatcher, timeline, and websocket protocol tests pass with new optional queue processing.

## Residual Risks

1. Bridge timeout exception currently fails the specific call path but does not cancel in-flight async work already running in thread loop.
2. Very high-volume async bridging may increase thread churn under event-loop-heavy workloads.

## Next Suggested Step

1. Add bridge-level metrics (timeouts, bridge thread count, awaitable duration percentiles) for production observability.
