# Troubleshooting Guide

## Common Issues and Solutions

### GUI Issues

#### 1. GUI Window Won't Open

**Symptoms**: No window appears, or immediate crash

**Solutions**:

```bash
# Check Python version (requires 3.10+)
python --version

# Reinstall PyQt6 and qasync
pip install --upgrade PyQt6==6.7.0 qasync>=0.27.0

# Try running with debug output
python gui/app.py
```

**If still failing**:
- Check that `gui/app.py` exists
- Verify all imports in `gui/app.py`: `from qasync import QEventLoop`
- Make sure backend server is NOT required to launch GUI (can connect later)

---

#### 2. "RuntimeError: no running event loop"

**Symptoms**: Error appears when clicking buttons

**Root cause**: Async operations running without event loop context

**Solution**: This is FIXED in latest version
- Ensure you have `qasync >= 0.27.0` installed
- Check `gui/app.py` uses `QEventLoop` from qasync
- Verify all async handlers use `@asyncSlot` decorator

```python
# ❌ WRONG - causes event loop error
async def on_button_click():
    await protocol.connect()

# ✅ CORRECT
@asyncSlot()
async def on_button_click():
    await protocol.connect()
```

---

#### 3. Window Freezes When Connecting

**Symptoms**: GUI becomes unresponsive during device scan

**Root cause**: Long operations blocking event loop

**Solutions**:

1. Make sure operation is `async`:
```python
@asyncSlot()
async def on_scan_devices(self):
    # This is non-blocking
    await self.controller.scan_devices()
```

2. Check that backend server is running:
```bash
# Terminal 1: Start backend
python examples/server/main.py

# Terminal 2: Start GUI
python gui/app.py
```

3. If still freezing, backend may be slow:
- Check backend terminal for errors
- Verify `localhost:8090` is accessible

---

#### 4. "Cannot set parent, new parent is in a different thread"

**Symptoms**: QObject errors, app crashes

**Root cause**: Using threading with Qt objects

**Solution**: Removed in latest version (no more AsyncWorker class)
- Don't use `threading.Thread` with Qt objects
- Use `@asyncSlot` instead
- All async operations use shared event loop

---

#### 5. Effects Panel Won't Load

**Symptoms**: Effects list empty or error shown

**Solutions**:

1. Check `config/effects.yaml` exists:
```bash
ls config/effects.yaml
```

2. Verify effect format:
```yaml
effects:
  - id: rainbow
    name: Rainbow Effect
    duration: 5000
```

3. Check device is connected:
- Connect device first
- Then refresh effects
- Check backend logs for errors

---

### Connection Issues

#### 6. "Failed to Connect" - WebSocket

**Symptoms**: WebSocket protocol fails to connect

**Root cause**: Backend not running or wrong protocol selected

**Solutions**:

```bash
# 1. Start backend server
python examples/server/main.py
# Should see: "Uvicorn running on http://127.0.0.1:8090"

# 2. Verify backend is listening
netstat -an | find "8090"  # Windows
# Should show: LISTENING 127.0.0.1:8090

# 3. Test connection manually
python -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('ws://127.0.0.1:8090/ws') as ws:
        print('Connected!')
asyncio.run(test())
"
```

**If backend won't start**:
```bash
# Check if port is already in use
netstat -ano | find ":8090"  # Windows
lsof -i :8090  # macOS/Linux

# Kill process if needed
taskkill /PID <PID> /F  # Windows
```

---

#### 7. "Failed to Connect" - HTTP

**Symptoms**: HTTP protocol connection fails

**Root cause**: Wrong endpoint path or network issue

**Solution**: Latest version fixed endpoint path
- HTTP now connects to `/api/devices` (not `/api`)
- Ensure backend is running
- Check network: `curl http://127.0.0.1:8090/api/devices`

---

#### 8. "Connection Timed Out"

**Symptoms**: Hang when trying to connect

**Solutions**:

1. Backend might be starting slowly:
   - Wait 5 seconds for backend to fully start
   - Try again

2. Backend not accessible:
```bash
# Test from terminal
curl http://127.0.0.1:8090/api/devices

# Should return JSON with devices
```

3. Firewall blocking:
   - Check firewall settings
   - Ensure localhost (127.0.0.1) is not blocked
   - Disable firewall temporarily to test

---

### Device Issues

#### 9. No Devices Found

**Symptoms**: Device list is empty

**Solutions**:

1. Backend mock devices disabled:
```bash
# Check backend logs
# Should show device initialization

# Check config/devices.yaml
cat config/devices.yaml

# Should have mock devices defined:
mock_devices:
  - id: device-1
    name: Living Room
```

2. Devices not being returned by backend:
```bash
# Test endpoint directly
curl http://127.0.0.1:8090/api/devices

# Should return JSON:
# {"devices": [{"id": "device-1", ...}]}
```

3. Protocol not connected:
   - Connect to device first (via Connect button)
   - Device list only appears after connection

---

#### 10. Serial Device Not Detected

**Symptoms**: Real serial devices don't appear

**Solutions**:

1. Check device is connected:
```bash
# Windows
mode COM3  # or whatever port

# Linux/macOS
ls /dev/ttyUSB*
```

2. Check permissions:
```bash
# Windows - may need admin
# Right-click cmd.exe → Run as administrator

# Linux - add user to dialout group
sudo usermod -a -G dialout $USER
```

3. Check serial driver is installed:
```bash
# Look for `serial_driver.py` in device_driver/
ls src/device_driver/serial_driver.py
```

4. For now, use mock devices (no hardware needed):
   - Mock devices already configured in `config/devices.yaml`
   - Use for testing and development

---

### Effect Issues

#### 11. Effect Won't Send

**Symptoms**: Error when trying to send effect

**Solutions**:

1. Device must be connected first:
   - Click "Scan Devices"
   - Wait for devices to load
   - Select device

2. Effect must be valid:
```bash
# Check config/effects.yaml
cat config/effects.yaml

# Verify effect exists and has required fields
```

3. Backend must be running:
```bash
# Check backend terminal
# Should show: "Uvicorn running"

# Test endpoint
curl -X POST http://127.0.0.1:8090/api/devices/device-1/effects \
  -H "Content-Type: application/json" \
  -d '{"id":"rainbow"}'
```

---

#### 12. Effect Duration Wrong

**Symptoms**: Effects run longer/shorter than expected

**Root cause**: Duration units or configuration issue

**Solutions**:

1. Check duration format in config:
```yaml
effects:
  - id: rainbow
    duration: 5000  # milliseconds (5 seconds)
```

2. Verify backend is applying duration:
   - Check `examples/server/main.py`
   - Look for effect duration handling

---

### Testing Issues

#### 13. Tests Won't Run

**Symptoms**: pytest fails or hangs

**Solutions**:

```bash
# 1. Ensure pytest installed
pip install pytest pytest-asyncio

# 2. Run specific test file
pytest tests/test_device_manager.py -v

# 3. Run with timeout (prevent hangs)
pytest tests/ -v --timeout=10

# 4. Check conftest.py exists
ls tests/conftest.py
```

**If tests hang on asyncio**:
```bash
# Kill hanging processes
taskkill /F /IM python.exe  # Windows
pkill -f pytest  # Linux/macOS

# Try running with asyncio mode
pytest --asyncio-mode=auto tests/
```

---

#### 14. Import Errors in Tests

**Symptoms**: ModuleNotFoundError when running tests

**Solutions**:

```bash
# 1. Verify structure
ls -R src/
ls -R gui/

# 2. Check __init__.py files exist
ls src/__init__.py
ls src/device_driver/__init__.py
ls gui/__init__.py

# 3. Run tests from correct directory
cd c:/path/to/PythonPlaySEM
pytest tests/

# 4. Check PYTHONPATH
set PYTHONPATH=%CD%  # Windows
export PYTHONPATH=$PWD  # Linux/macOS
pytest tests/
```

---

### Backend Issues

#### 15. Backend Crashes on Startup

**Symptoms**: Backend starts then immediately exits

**Solutions**:

1. Check port is not in use:
```bash
netstat -ano | find ":8090"  # Windows
# If port in use, find and kill:
taskkill /PID <PID> /F
```

2. Check FastAPI installed:
```bash
pip install fastapi uvicorn websockets
```

3. Run with full error output:
```bash
python examples/server/main.py 2>&1 | more
```

4. Check Python version:
```bash
python --version  # Should be 3.10+
```

---

#### 16. Backend Logs Show Errors

**Symptoms**: Backend shows error messages

**Solutions**:

**Common errors**:

1. `Address already in use`:
   - Port 8090 occupied
   - Change port in `examples/server/main.py`
   - Or kill existing process

2. `ModuleNotFoundError`:
   - Missing dependency
   - Run: `pip install fastapi uvicorn websockets`

3. `FileNotFoundError` (config files):
   - Check `config/devices.yaml` exists
   - Check `config/effects.yaml` exists
   - Should be in project root

---

### Network/Environment Issues

#### 17. "Address Already in Use"

**Symptoms**: Port 8090 already in use

**Solutions**:

```bash
# Find what's using port
netstat -ano | find ":8090"  # Windows
lsof -i :8090  # macOS/Linux

# Kill the process
taskkill /PID <PID> /F  # Windows
kill -9 <PID>  # macOS/Linux

# Or use different port
# Edit examples/server/main.py:
# uvicorn.run(app, host="127.0.0.1", port=8091)
```

---

#### 18. "Connection Refused"

**Symptoms**: Can't connect to localhost:8090

**Solutions**:

1. Backend not running:
   - Terminal should show "Uvicorn running on..."
   - Start with: `python examples/server/main.py`

2. Backend running on different host:
```bash
# Check backend logs
# Should show: "Uvicorn running on http://127.0.0.1:8090"
# Not: "0.0.0.0:8090" or other address
```

3. Firewall blocking:
   - Try disabling temporarily
   - Or whitelist localhost
   - Or use VPN if through proxy

---

## Getting More Help

### Debug Mode

Enable verbose logging:

```python
# Add to gui/app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Logs

```bash
# Backend logs (terminal where it runs)
# Shows: connections, devices, effects

# GUI logs (terminal where it runs)
# Shows: button clicks, protocol operations

# Test logs
# Generate with: pytest -v
```

### Reproduce Issue

When reporting issues:
1. Note exact error message
2. Check terminal logs
3. Try with mock devices first
4. Verify backend is running
5. Check Python version
6. List installed packages: `pip list`

---

## Still Not Working?

1. **Read the logs carefully** - They usually explain the issue
2. **Try with mock devices** - Rules out hardware issues
3. **Check the guides** - [DEVICES.md](devices.md) or [TESTING.md](testing.md)
4. **Review code** - Source is in `gui/` and `src/`
5. **Check requirements** - `cat requirements.txt`

---

*Last updated: December 9, 2025*
