# Troubleshooting Playbooks

This guide provides practical runbooks for common operational failures.

## 1. Reconnect Storms

### Reconnect Storm Symptoms

1. Repeated connect/disconnect log loops.
2. Commands intermittently fail after disconnect events.
3. Device state flaps between connected and disconnected.

### Reconnect Storm Immediate Actions

1. Confirm retry budgets are bounded (`max_attempts`).
2. Increase initial backoff delay to reduce burst reconnect pressure.
3. Check broker/serial/BLE endpoint stability outside application layer.
4. Verify driver connection state is reset on disconnect.

### Reconnect Storm Root Cause Checks

1. Invalid credentials or TLS mismatch.
2. Endpoint overload or unstable network path.
3. Unhandled exceptions in driver callbacks.
4. Too-aggressive retry policy causing synchronized reconnect waves.

### Reconnect Storm Mitigation

1. Add jitter to reconnect delays where possible.
2. Increase `initial_delay` and `max_delay` in retry policy.
3. Add circuit-breaker cooldown after retry budget exhaustion.

## 2. Queue Backpressure (Managed Dispatch)

### Queue Backpressure Symptoms

1. Queue size grows continuously.
2. Effects are delayed or appear stale.
3. Dead-letter queue increases rapidly.

### Queue Backpressure Immediate Actions

1. Verify queue processing is enabled in one runtime path:
   - timeline path with `process_managed_queue=True`
   - protocol server path with `process_managed_queue=True`
2. Inspect failure policy (`drop`, `retry`, `dead_letter`).
3. Confirm downstream drivers are connected and accepting commands.

### Queue Backpressure Root Cause Checks

1. Queue enabled but never drained.
2. Retry policy requeues indefinitely due to repeated command failures.
3. Device command throughput lower than incoming effect rate.

### Queue Backpressure Mitigation

1. Use explicit retry budget (`max_dispatch_retries`).
2. Prioritize critical effects and drop low-priority noise under load.
3. Add monitoring for queue length and processing latency.

## 3. Async Bridge Timeouts

### Async Bridge Timeout Symptoms

1. `send_command` returns failure after timeout threshold.
2. Logs indicate async bridge timeout exceptions.
3. Intermittent failures under high concurrent mixed sync+async load.

### Async Bridge Timeout Immediate Actions

1. Check `async_bridge_timeout` in `DeviceManager` configuration.
2. Identify slow async driver operations and external dependencies.
3. Validate event-loop availability and thread health.

### Async Bridge Timeout Root Cause Checks

1. Long-running awaitables in driver connect/send paths.
2. Blocking operations inside async methods.
3. External services causing prolonged await times.

### Async Bridge Timeout Mitigation

1. Reduce per-call async workload and split large operations.
2. Increase timeout where hardware/network latency requires it.
3. Add timing metrics around async driver methods.

## 4. Capability Validation Failures

### Capability Validation Failure Symptoms

1. Dispatcher raises capability validation errors.
2. Commands rejected before reaching driver send path.

### Capability Validation Failure Immediate Actions

1. Verify driver `get_capabilities()` payload is valid and complete.
2. Ensure effect type names match capability `effect_type` values.
3. Check parameter names/types/ranges against capability schema.

### Capability Validation Failure Mitigation

1. Correct capability contract in driver implementation.
2. Correct effect mapping in `effects.yaml`.
3. Keep validation enabled in staging to catch contract drift early.

## 5. Escalation Checklist

1. Collect relevant logs (driver reconnect attempts, queue outcomes, timeout traces).
2. Capture current retry/queue/bridge timeout settings.
3. Reproduce with targeted test suites.
4. Attach capability payload for affected devices.
