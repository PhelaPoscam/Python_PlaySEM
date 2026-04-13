# Production Hardening Guide

This guide describes the recommended production posture for PythonPlaySEM.

## Scope

Use this checklist when moving from demo/test usage to production usage.

## 1. Driver Reliability

1. Implement bounded retry/reconnect in all real drivers.
2. Expose reconnect telemetry (`attempts`, `last_error`, recovery time).
3. Ensure disconnect handling always resets connection state.
4. Use explicit retry budgets to avoid infinite reconnect loops.

## 2. Capability Contract Enforcement

1. Ensure each driver returns a standard capability dictionary from `get_capabilities()`.
2. Enable capability validation in dispatch paths:
   - `EffectDispatcher(..., validate_capabilities=True)`
3. Reject unsupported effects and invalid parameters before sending commands.

## 3. Dispatch Control

1. Use managed queue mode for bursty workloads:
   - `EffectDispatcher(..., managed_mode=True, failure_policy="retry")`
2. Define one queue-draining runtime path:
   - timeline path or protocol server path
3. Use dead-letter policy for postmortem visibility in critical flows.

## 4. Sync and Async Consistency

1. Keep `DeviceManager` sync mode with async bridge unless full async migration is planned.
2. Set `async_bridge_timeout` explicitly for your workload.
3. Monitor timeout occurrences and investigate hanging async calls.

## 5. Protocol Server Operations

1. Use authentication where supported (API key/token).
2. Use TLS/WSS for external network exposure.
3. Validate clean start/stop lifecycle during deployment tests.
4. Add health checks and readiness checks at service boundaries.

## 6. Testing Gate Before Release

Minimum required test gate:

1. Driver resilience tests
2. Dispatcher queue/failure policy tests
3. Manager sync+async bridge tests
4. End-to-end effect flow test to concrete driver

Recommended command set:

1. `python -m pytest -q tests/test_device_manager.py`
2. `python -m pytest -q tests/test_effect_dispatcher.py`
3. `python -m pytest -q tests/test_driver_resilience.py`
4. `python -m pytest -q tests/integration/test_phase5_reference_driver_flow.py`

## 7. Known Non-Production Components

Treat these as development/demo components unless hardened separately:

1. Monolithic test server under `tools/test_server/main.py`

## 8. Operational Metrics to Collect

1. Reconnect success rate
2. Dispatch success/failure ratio
3. Dead-letter queue growth rate
4. Async bridge timeout count
5. End-to-end effect latency percentiles

## 9. Rollout Strategy

1. Start with one concrete device class (for example, RGB light).
2. Run canary deployment with capability validation enabled.
3. Observe reconnect and timeout metrics.
4. Expand to additional device classes after stability is proven.
