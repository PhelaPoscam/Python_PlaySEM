# Testing Guide

## Overview

Complete testing checklist for PythonPlaySEM GUI application.

---

## Test Environment Setup

### Prerequisites
- Backend server running: `python examples/server/main.py`
- GUI application: `python -m gui.app`
- Python 3.14+ with virtual environment
- PyQt6 6.7.0 + qasync

### Quick Setup
```powershell
# Terminal 1
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python examples/server/main.py

# Terminal 2
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python -m gui.app
```

---

## Test Cases (12 Total)

### Test 1: Application Launch ✓

**Purpose**: Verify GUI starts without errors

**Steps**:
1. Open terminal in project directory
2. Run: `python -m gui.app`
3. Wait for window to appear

**Expected**:
- [ ] PyQt6 window opens
- [ ] Title: "PythonPlaySEM Control Panel"
- [ ] Three tabs: Connection, Devices, Effects
- [ ] Status bar at bottom
- [ ] No errors in terminal

**Success Criteria**:
```
14:xx:xx - [INFO] __main__ - Starting PythonPlaySEM GUI Application
14:xx:xx - [INFO] __main__ - GUI application started successfully
```

---

### Test 2: Connection Panel Verification ✓

**Purpose**: Verify UI components are initialized

**Steps**:
1. GUI open on Connection tab
2. Observe all elements

**Expected**:
- [ ] Protocol dropdown shows: "websocket", "http"
- [ ] Host field: "127.0.0.1"
- [ ] Port field: "8090"
- [ ] Status indicator: gray/red (disconnected)
- [ ] Status label: "Disconnected"
- [ ] "Connect" button enabled
- [ ] "Disconnect" button disabled

---

### Test 3: WebSocket Connection ✓

**Purpose**: Verify WebSocket protocol works

**Steps**:
1. Connection tab visible
2. Protocol: "websocket" (default)
3. Click "Connect"
4. Wait 2-3 seconds
5. Check backend terminal

**Expected**:
- [ ] Status indicator: green
- [ ] Status label: "Connected"
- [ ] "Connect" button: disabled
- [ ] "Disconnect" button: enabled
- [ ] Backend shows:
  ```
  ('127.0.0.1', XXXXX) - "WebSocket /ws" [accepted]
  [OK] Client connected
  ```
- [ ] No errors

---

### Test 4: Device Panel (Scanning) ✓

**Purpose**: Verify device discovery works

**Steps**:
1. Connected via WebSocket
2. Click "Devices" tab
3. Click "Scan Devices"
4. Wait 2-3 seconds

**Expected**:
- [ ] Devices tab opens
- [ ] 3 mock devices appear:
  - [ ] Mock Light Device
  - [ ] Mock Vibration Device
  - [ ] Mock Wind Device
- [ ] Status bar shows: "3 device(s) connected"

---

### Test 5: Effect Panel (Device Selection) ✓

**Purpose**: Verify effect UI appears

**Steps**:
1. Select "Mock Light Device" in Devices tab
2. Click "Effects" tab
3. Observe controls

**Expected**:
- [ ] Effects tab opens
- [ ] Device name shows in UI
- [ ] Effect type dropdown with:
  - [ ] Light, Vibration, Wind, Scent, Heat, Cold
- [ ] Intensity slider (0-100)
- [ ] Duration spinbox (0-60000ms)
- [ ] Color picker button
- [ ] "Send Effect" button: **GREEN**

---

### Test 6: Send Effect (WebSocket) ✓

**Purpose**: Verify effect transmission works

**Steps**:
1. Mock Light Device selected
2. Effect Type: "Light"
3. Intensity: 75
4. Duration: 2000ms
5. Select a color
6. Click "Send Effect"

**Expected**:
- [ ] Button click succeeds
- [ ] Status bar: "Sent: Light"
- [ ] Button remains enabled
- [ ] GUI responsive
- [ ] Backend shows:
  ```
  [RECV] Received message: {effect data}
  ```

---

### Test 7: Disconnect (WebSocket) ✓

**Purpose**: Verify disconnection works

**Steps**:
1. Connection tab
2. Click "Disconnect"
3. Wait for status update
4. Check backend

**Expected**:
- [ ] Status indicator: red
- [ ] Status label: "Disconnected"
- [ ] "Connect" button: enabled
- [ ] "Disconnect" button: disabled
- [ ] Backend shows:
  ```
  [x] Client disconnected
  ```

---

### Test 8: HTTP Protocol ✓

**Purpose**: Verify HTTP/REST protocol works

**Steps**:
1. Disconnected
2. Connection tab
3. Change protocol: "websocket" → "http"
4. Click "Connect"
5. Wait for connection

**Expected**:
- [ ] Status indicator: green
- [ ] Status label: "Connected"
- [ ] Connection succeeds
- [ ] Backend shows:
  ```
  HTTP Request: GET /api/devices "HTTP/1.1 200 OK"
  ```
- [ ] HTTP polling starts (requests every ~1 second)

---

### Test 9: Error Handling ✓

**Purpose**: Verify graceful error handling

**Steps**:
1. Connected via WebSocket
2. Stop backend (Ctrl+C)
3. Wait 5 seconds
4. Try to send effect
5. Try to scan devices

**Expected**:
- [ ] Error message in status bar
- [ ] GUI doesn't crash
- [ ] Can click "Disconnect"
- [ ] No unhandled exceptions
- [ ] Can restart backend and reconnect

---

### Test 10: UI Responsiveness ✓

**Purpose**: Verify UI doesn't freeze

**Steps**:
1. Connected to backend
2. Rapidly click tabs
3. Send multiple effects
4. Switch protocols
5. Resize window

**Expected**:
- [ ] All clicks respond immediately
- [ ] No freezing or lag
- [ ] Status updates in real-time
- [ ] Window resizes smoothly
- [ ] Can close without hanging

---

### Test 11: Reconnection ✓

**Purpose**: Verify reconnection after disconnect

**Steps**:
1. Connected via WebSocket
2. Click "Disconnect"
3. Wait for disconnection
4. Click "Connect" again
5. Check status

**Expected**:
- [ ] Disconnects cleanly
- [ ] Reconnects successfully
- [ ] Status indicator updates
- [ ] Backend shows:
  ```
  [OK] Client connected. Total clients: 1
  ```

---

### Test 12: Protocol Switching ✓

**Purpose**: Verify switching between protocols

**Steps**:
1. Connected via WebSocket
2. Click "Disconnect"
3. Change protocol to HTTP
4. Click "Connect"
5. Send an effect
6. Disconnect
7. Switch to WebSocket
8. Connect and send effect

**Expected**:
- [ ] Both protocols work
- [ ] No memory leaks
- [ ] No resource issues
- [ ] Application stable
- [ ] Effects send on both protocols

---

## Test Results Form

### Session Information

**Testing Date**: _______________

**Tester Name**: _______________

**Environment**:
- Python Version: _______________
- PyQt6 Version: _______________
- qasync Version: _______________
- OS: _______________
- Browser/Terminal: _______________

### Results Table

| Test # | Name | Pass | Fail | Notes |
|--------|------|------|------|-------|
| 1 | Application Launch | [ ] | [ ] | |
| 2 | Connection Panel | [ ] | [ ] | |
| 3 | WebSocket Connection | [ ] | [ ] | |
| 4 | Device Scanning | [ ] | [ ] | |
| 5 | Effect Panel | [ ] | [ ] | |
| 6 | Send Effect (WS) | [ ] | [ ] | |
| 7 | Disconnect (WS) | [ ] | [ ] | |
| 8 | HTTP Protocol | [ ] | [ ] | |
| 9 | Error Handling | [ ] | [ ] | |
| 10 | UI Responsiveness | [ ] | [ ] | |
| 11 | Reconnection | [ ] | [ ] | |
| 12 | Protocol Switching | [ ] | [ ] | |

**Total Passed**: _____ / 12

### Overall Status

- [ ] **ALL PASS** (Ready for production)
- [ ] **SOME FAILURES** (Report issues)
- [ ] **BLOCKED** (Critical issues)

### Issues Found

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Performance Notes

- WebSocket latency: _______________ ms
- HTTP latency: _______________ ms
- Memory usage: _______________ MB
- CPU usage: _______________ %

### Additional Comments

```
___________________________________________________________________

___________________________________________________________________

___________________________________________________________________
```

### Tester Signature

**Name**: ________________________

**Date**: ________________________

**Time Spent**: ________________________

---

## Automated Tests

Run these for quick validation:

```bash
# GUI component tests
python tests/test_gui_components.py

# Protocol tests
python tests/test_gui_modules.py

# Integration tests
python tests/test_integration.py
```

**Expected**: All tests pass (9/9 categories)

---

## Quick Reference

### Commands

**Start Backend**:
```bash
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python examples/server/main.py
```

**Start GUI**:
```bash
cd 'c:\TUNI - Projects\Python Project\PythonPlaySEM'
python -m gui.app
```

**Run Tests**:
```bash
python tests/test_gui_components.py
python tests/test_gui_modules.py
python tests/test_integration.py
```

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Close window | Alt+F4 |
| Tab navigation | Ctrl+Tab |
| Focus connect button | Tab |
| Trigger button | Enter |

### Port Information

| Port | Service | URL |
|------|---------|-----|
| 8090 | Backend | http://127.0.0.1:8090 |
| 8090 | WebSocket | ws://127.0.0.1:8090/ws |

---

## Troubleshooting

### Test Fails Consistently

1. **Check logs**: Terminal shows detailed error messages
2. **Restart components**: Backend → GUI
3. **Clear cache**: Delete `.qodo/` folder
4. **Reinstall deps**: `pip install -r requirements.txt`

### Specific Failures

| Failure | Solution |
|---------|----------|
| "Connection refused" | Backend not running |
| "No route to host" | Firewall blocking port 8090 |
| "Device not found" | Scan devices again, wait 3sec |
| "Unknown error" | Check backend logs |
| "GUI freezes" | Restart both components |

---

## Success Checklist

Before marking as complete, verify:

- [ ] All 12 tests executed
- [ ] Test form filled completely
- [ ] All results documented
- [ ] Issues noted (if any)
- [ ] Performance acceptable
- [ ] No crashes observed
- [ ] All errors understood

---

## Automated Unit Tests

The project includes automated tests for core components.

### Quick Test Run (Recommended)

```bash
pytest tests/ -v --timeout=60
```

**Time**: ~12 seconds on Windows  
**Status**: ✅ All 9/9 tests pass

### Running Specific Tests

```bash
# Test device manager only
pytest tests/test_device_manager.py -v

# Test with markers
pytest -m smoke -v

# Run with verbose output
pytest tests/ -vv
```

### ⚠️ Windows Coverage Known Issue

Running tests with coverage reporting (`--cov`) on Windows causes **indefinite hangs** (20+ minutes):

```bash
# ❌ DO NOT DO THIS - will hang for 20+ minutes
pytest tests/ --cov=src --cov-report=xml --cov-report=term
```

**Root Cause**: Windows + asyncio + coverage interact poorly. The `pytest-cov` plugin interferes with Windows async event loops.

**Workaround Options**:

**Option 1: Skip coverage (fastest)** ✅
```bash
pytest tests/ -v --timeout=60
```

**Option 2: Use Linux runner** (CI/CD)
```bash
# Works fine on GitHub Actions ubuntu-latest
pytest tests/ --cov=src --cov-report=xml --cov-report=term
```

**Option 3: Manual coverage analysis**
```bash
coverage run -m pytest tests/
coverage report
```

### Test Organization

**Core Tests** (Fast, ~0.3s):
- `test_device_manager.py` - Device management
- `test_config_loader.py` - Configuration loading
- `test_effect_metadata.py` - Effect metadata parsing
- `test_effect_dispatcher.py` - Effect dispatch logic

**Integration Tests** (~11s, includes startup/shutdown):
- Server integration tests
- Protocol tests
- Device discovery tests

### Pytest Configuration

See `pytest.ini` for configuration:
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

### CI/CD Notes

- **GitHub Actions**: Use `ubuntu-latest` runner if coverage is needed
- **Local development**: Skip `--cov` and use quick test run
- **Coverage critical?**: Consider migrating to non-Windows CI runners

---

## See Also

- `GETTING_STARTED.md` - Quick start guide
- `DEVICES.md` - Device management
- `STATUS.md` - Current status
- `../README.md` - Full documentation

---

*Testing Guide - Last updated: December 9, 2025*
