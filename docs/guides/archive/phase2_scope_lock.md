# Phase 2 Scope Lock

Date: 2026-04-13
Depends on: Phase 1 baseline report (`docs/guides/archive/phase1_baseline_report.md`)

## In Scope

1. Driver resilience framework for reconnect/retry/backoff.
2. Integration in these drivers:
   - `playsem/drivers/mqtt_driver.py`
   - `playsem/drivers/serial_driver.py`
   - `playsem/drivers/bluetooth_driver.py`
3. Observability for reconnect lifecycle:
   - attempts
   - backoff delay
   - terminal failure reason
   - time-to-recover
4. Failure-injection tests:
   - broker restart/disconnect
   - serial port unavailable/reconnect
   - BLE disconnect/reconnect

## Out of Scope

1. Full async-first `DeviceManager` refactor.
2. Dispatcher queue/priority redesign (Phase 3).
3. New concrete hardware drivers (Phase 5).
4. GUI redesign or feature expansion.

## Acceptance Criteria

1. Reconnect success rate >= 99.0% in transient-disconnect tests.
2. Max command loss <= 1 command per affected device in 10-second disconnect window.
3. No regression in baseline suites:
   - `python -m pytest -q`
   - `python -m pytest -q tests/integration`
   - `python -m pytest -q tests/protocols`
   - `python -m pytest -q tests/test_device_manager.py tests/test_effect_dispatcher.py`
4. New resilience tests added and passing in CI-compatible mode.

## Risks and Constraints

1. Mixed sync/thread/async architecture may require adapter logic to avoid deadlocks.
2. Some protocol tests are currently skipped due to known environment/CI constraints.
3. Retry behavior must be bounded to avoid runaway loops.

## Definition of Done

1. All in-scope drivers implement bounded reconnect/retry policy.
2. Failure-injection tests pass with documented assumptions.
3. Baseline suites show no new failures.
4. Release notes updated with resilience behavior and limitations.
