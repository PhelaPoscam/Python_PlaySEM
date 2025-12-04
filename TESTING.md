# Testing Guide

## Running Tests

### Quick Test Run (Recommended)
```bash
pytest tests/ -v --timeout=60
```

**Time:** ~12 seconds on Windows  
**Status:** ✅ All tests pass

### Why NOT to use `--cov` on Windows

Running tests with coverage reporting (`--cov`) on Windows causes **indefinite hangs** (21+ minutes):

```bash
# ❌ DO NOT DO THIS - will hang for 20+ minutes
pytest tests/ --cov=src --cov-report=xml --cov-report=term
```

#### Root Cause
- **Windows + asyncio + coverage** interact poorly
- The `pytest-cov` plugin interferes with Windows async event loops
- Particularly affects tests with async/await and threaded operations (MQTT, HTTP, CoAP, UPnP)
- Linux/Mac may not have this issue

#### Workaround
Until this is fixed, use **one of these approaches**:

**Option 1: Skip coverage entirely** (fastest)
```bash
pytest tests/ -v --timeout=60
```

**Option 2: Use a Linux runner** (CI/CD)
```bash
# Works fine on GitHub Actions ubuntu-latest
pytest tests/ --cov=src --cov-report=xml --cov-report=term
```

**Option 3: Manual coverage** (not recommended)
```bash
# Analyze without reporting
coverage run -m pytest tests/
coverage report
```

## Test Organization

### Core Tests (Fast, ~0.3s)
- `test_device_manager.py` - Device management
- `test_config_loader.py` - Configuration loading
- `test_effect_metadata.py` - Effect metadata parsing
- `test_effect_dispatcher.py` - Effect dispatch logic

### Protocol Server Tests (~11s, includes startup/shutdown)
- `test_mqtt_broker.py` - MQTT server
- `test_websocket_server.py` - WebSocket server
- `test_upnp_server.py` - UPnP server
- `test_coap_server_integration.py` - CoAP server (1 test skipped: known hang)

### Total Test Time
- **Without coverage:** ~12 seconds ✅
- **With coverage:** 20+ minutes (hangs) ❌

## Pytest Configuration

See `pytest.ini`:
```ini
[pytest]
markers =
    integration: mark network/integration tests
    smoke: mark quick smoke tests for CI
addopts = -ra -q --timeout=60
asyncio_mode = auto
timeout = 60
```

- `--timeout=60`: Kills individual tests that hang for >60 seconds
- `asyncio_mode = auto`: Enables pytest-asyncio auto mode
- Markers allow filtering: `pytest -m smoke` for quick CI

## CI/CD Notes

- GitHub Actions: Use `ubuntu-latest` if coverage is needed
- Local development: Skip `--cov` and use the quick test run
- If coverage is critical, consider migrating to non-Windows CI runners
