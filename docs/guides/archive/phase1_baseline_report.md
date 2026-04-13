# Phase 1 Baseline Report

Date: 2026-04-13
Scope: Baseline and scope lock for production-readiness hardening.

## Baseline Matrix

| Suite | Command | Result | Elapsed (s) |
|---|---|---|---:|
| Quick All | `python -m pytest -q` | PASS | 19.91 |
| Integration | `python -m pytest -q tests/integration` | PASS | 5.36 |
| Protocols | `python -m pytest -q tests/protocols` | PASS | 9.02 |
| Core Units | `python -m pytest -q tests/test_device_manager.py tests/test_effect_dispatcher.py` | PASS | 1.23 |

## Flakiness Snapshot (3 reruns each)

| Suite | Run 1 (s) | Run 2 (s) | Run 3 (s) | Exit Codes |
|---|---:|---:|---:|---|
| Integration | 5.12 | 6.44 | 6.12 | 0, 0, 0 |
| Protocols | 9.08 | 9.05 | 9.07 | 0, 0, 0 |
| Core Units | 1.23 | 1.32 | 1.33 | 0, 0, 0 |

Conclusion: No flakes observed in this run window.

## Skip Inventory (Observed)

- GUI-related skips from `tests/gui` and `tests/integration/test_integration.py` due to unavailable `gui.protocols` and related GUI modules.
- Protocol skips in `tests/protocols`:
  - CoAP integration skip due to known CI port overflow behavior (`aiocoap` WebSocket binding issue).
  - MQTT broker startup timing skip in one test path.

These skips are expected in current environment and did not cause suite failures.

## Architecture Baseline (Locked)

- `DeviceManager` is synchronous command routing: `playsem/device_manager.py`.
- MQTT driver uses threaded network loop (`loop_start`/`loop_stop`): `playsem/drivers/mqtt_driver.py`.
- Bluetooth driver is async (`AsyncBaseDriver`): `playsem/drivers/bluetooth_driver.py`.
- Protocol servers are async lifecycle components: `playsem/protocol_servers/`.
- Effect dispatch is immediate passthrough without queue semantics: `playsem/effect_dispatcher.py`.

## Phase 2 Entry SLOs (Locked Targets)

- Reconnect success rate after transient disconnect: >= 99.0% within retry budget.
- Max command loss during a 10-second transient disconnect window: <= 1 command per affected device.
- P95 dispatch latency under baseline load (single-device command path): <= 50 ms.

## Go/No-Go Decision

Decision: GO for Phase 2.

Rationale:
- Baseline suites passed consistently across reruns.
- No unexpected failures or instability observed.
- Known skips are documented and currently acceptable for Phase 2 hardening work.

## Follow-up Actions

1. Implement reconnect/retry policy abstraction for MQTT, Serial, and Bluetooth drivers.
2. Add failure-injection tests for disconnect/recovery scenarios.
3. Add reconnect observability fields in driver logs/metrics.
