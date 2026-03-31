# Benchmark Scripts

This directory contains scripts used for validating the instantiation of protocol handlers and for performance benchmarking.

These scripts are **not** standard `pytest` tests and are intended for manual execution or specific performance measurement jobs, not as part of the main CI/CD test suite.

## Scripts:

*   `protocol_validation.py`: Comprehensive protocol validation and performance benchmark. Measures startup time and latency for various protocol handlers (HTTP, CoAP, UPnP, MQTT, WebSocket).
*   `validate_protocols.py`: Basic validation script to ensure all protocol handlers can be instantiated.

## Usage:

To run these scripts, execute them directly from your terminal:

```bash
python benchmark/protocol_validation.py
python benchmark/validate_protocols.py
```

**Note:** These scripts might attempt to bind to specific network ports. Ensure no other services are using these ports, or modify the scripts to use dynamic port allocation if running in a shared environment.