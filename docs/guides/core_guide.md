# Core Usage Guide

This page combines the small starter guides into one compact reference.

## Quick Start

1. Read [README.md](../../README.md).
2. Skim [docs/LIBRARY.md](../LIBRARY.md) for the API surface.
3. Use `config/devices.yaml` and `config/effects.yaml` as the main runtime inputs.

## Device Management

Device setup, capability lookup, and driver wiring are covered by:

1. [docs/guides/custom_driver.md](custom_driver.md)
2. [docs/guides/troubleshooting.md](troubleshooting.md)
3. [config/README.md](../../config/README.md)

## Testing and Protocols

Use the focused protocol and test docs for behavior-specific workflows:

1. [docs/guides/protocol_testing.md](protocol_testing.md)
2. [tests/](../../tests)
3. [playsem/drivers/serial_driver.py](../../playsem/drivers/serial_driver.py)

## Cross-Protocol Discovery

The device registry demonstrates shared visibility across protocols.

1. [examples/device_registry_demo.py](../../examples/device_registry_demo.py)
2. [playsem/device_registry.py](../../playsem/device_registry.py)
