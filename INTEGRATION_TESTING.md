# Integration Testing Guide

## 🎯 What We Learned: The WebSocket Bug

**You discovered a critical bug** that all our unit tests missed! The WebSocket server crashed with:
```
TypeError: WebSocketServer._handle_client() missing 1 required positional argument: 'path'
```

### Why Did Unit Tests Miss This?

**Unit Tests** (what we had):
- ✅ Tested `_parse_effect()` - worked fine
- ✅ Tested `_broadcast()` - worked fine
- ✅ Tested message processing logic - worked fine
- ❌ **Never tested the actual WebSocket connection handler signature**
- ❌ **Never started a real `websockets` server**

We used `AsyncMock()` objects to simulate WebSocket clients, but **never actually integrated with the real `websockets` library** which calls `_handle_client()`.

### The Root Cause

The code used the **old websockets API** (pre-v10.0):
```python
async def _handle_client(self, websocket, path):  # Old API
```

But `websockets 15.0.1` uses the **new API**:
```python
async def _handle_client(self, websocket):  # New API (no path)
```

### The Key Lesson

```python
# Unit test (what we did) - PASSED ✅
mock_websocket = AsyncMock()
await server._handle_client(mock_websocket, "/")  # We control the call

# Integration test (what we needed) - WOULD HAVE FAILED ❌
await websockets.serve(server._handle_client, "localhost", 8765)
# ↑ websockets library controls the call signature!
# It would call _handle_client(websocket) without 'path'
```

---

## 📊 Unit Tests vs Integration Tests

### Unit Tests
**Purpose:** Test individual functions/methods in isolation  
**Speed:** ⚡ Fast (milliseconds)  
**Scope:** Single function or class method  
**Mocking:** Heavy use of mocks and stubs  
**What They Catch:** Logic errors, edge cases, algorithm correctness  
**What They Miss:** API signature mismatches, library compatibility, real I/O issues  

**Example:**
```python
def test_websocket_server_parse_effect(websocket_server):
    """Unit test - tests logic only"""
    data = {"effect_type": "light", "intensity": 80, "duration": 1000}
    effect = websocket_server._parse_effect(data)
    
    assert effect.effect_type == "light"
    assert effect.intensity == 80
```

### Integration Tests
**Purpose:** Test components working together with real dependencies  
**Speed:** 🐢 Slower (seconds)  
**Scope:** Multiple components + external libraries  
**Mocking:** Minimal - use real libraries  
**What They Catch:** API mismatches, library compatibility, network issues, file I/O problems  
**What They Miss:** Detailed edge cases (that's what unit tests are for)  

**Example:**
```python
@pytest.mark.asyncio
async def test_websocket_real_connection():
    """Integration test - tests with real websockets library"""
    server = WebSocketServer(host="localhost", port=18765, dispatcher=dispatcher)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.3)
    
    # This uses the REAL websockets.connect() function
    async with websockets.connect("ws://localhost:18765") as websocket:
        welcome = await websocket.recv()
        # ... test real communication ...
```

---

## 🧪 Integration Tests We Created

### 1. ConfigLoader Integration Tests
**File:** `tests/test_config_loader_integration.py`

**What It Tests:**
- Loading actual `devices.yaml` and `effects.yaml` from disk
- Real file I/O with the operating system
- YAML parser handling comments, unicode, nested structures
- Error handling with actual file system errors

**Why It Matters:**
- Catches file permission issues
- Catches YAML parser incompatibilities
- Catches path resolution problems (relative vs absolute)
- Catches encoding issues (UTF-8, unicode)

### 2. DeviceManager Integration Tests
**File:** `tests/test_device_manager_integration.py`

**What It Tests:**
- Loading devices from real config files
- Using actual MockDeviceBase instances (not mocks)
- Real device lifecycle (register → use → unregister)
- Multiple devices working simultaneously

**Why It Matters:**
- Catches device driver interface changes
- Catches threading/concurrency issues
- Catches state management bugs

### 3. EffectDispatcher Integration Tests
**File:** `tests/test_effect_dispatcher_integration.py`

**What It Tests:**
- Complete pipeline: EffectMetadata → EffectDispatcher → DeviceManager → Device
- Real config files driving the setup
- Multiple effects to multiple devices
- Device errors and recovery

**Why It Matters:**
- Catches end-to-end workflow issues
- Catches data transformation bugs
- Catches error propagation problems

### 4. MQTT Server Integration Tests
**File:** `tests/test_mqtt_server_integration.py`

**What It Tests:**
- Connecting to real MQTT broker (mosquitto)
- Sending actual MQTT messages over network
- Real pub/sub behavior with topics
- QoS levels, retained messages
- Invalid JSON handling

**Why It Matters:**
- Catches MQTT broker compatibility issues
- Catches network timeout problems
- Catches message serialization bugs
- **Would have caught our WebSocket bug if we had done similar tests!**

**Note:** Tests skip automatically if MQTT broker not running:
```python
requires_mqtt = pytest.mark.skipif(
    not mqtt_available,
    reason="MQTT broker not running on localhost:1883"
)
```

### 5. WebSocket Server Integration Tests
**File:** `tests/test_websocket_integration.py`

**What It Tests:**
- Starting real WebSocket server with `websockets.serve()`
- Connecting real WebSocket clients with `websockets.connect()`
- Real bidirectional communication
- Multiple simultaneous clients
- Invalid JSON handling
- Ping/pong protocol

**Why It Matters:**
- **THIS IS THE TEST THAT WOULD HAVE CAUGHT THE BUG!**
- Catches API signature mismatches (like we had)
- Catches async/await issues
- Catches real network communication problems

---

## 🚀 Running Integration Tests

### Run All Tests (Unit + Integration)
```bash
pytest -v
```

### Run Only Integration Tests
```bash
pytest tests/*_integration.py -v
```

### Run Specific Integration Test File
```bash
pytest tests/test_websocket_integration.py -v
```

### Run With Coverage
```bash
pytest --cov=src --cov-report=html
```

### Skip Slow Tests (Run Only Unit Tests)
```bash
pytest -m "not integration"  # (if we add @pytest.mark.integration)
```

---

## 📈 Test Pyramid

```
          /\
         /  \        E2E Tests (Few)
        /____\       - Full system with real browser/devices
       /      \      
      /        \     Integration Tests (Some)
     /__________\    - Real libraries, real I/O
    /            \   
   /              \  Unit Tests (Many)
  /________________\ - Fast, isolated, mocked
```

**Our Current Status:**
- ✅ **40 Unit Tests** - Fast, isolated, good coverage
- ✅ **5 Integration Test Files** - Real dependencies, catch compatibility issues
- ⏳ **E2E Tests** - Future: Full system with real VR/Unity clients

---

## 🎓 Best Practices We Learned

### 1. **Always Test External Libraries**
If you use a library (websockets, paho-mqtt, etc.), write at least ONE integration test that actually uses it.

### 2. **Test Real I/O**
- Real file loading (not StringIO)
- Real network calls (not mocked sockets)
- Real database queries (not mocked connections)

### 3. **Fast Feedback Loop**
- Unit tests should run in < 1 second total
- Integration tests can take 5-10 seconds
- Run unit tests frequently, integration tests before commits

### 4. **Separate Test Files**
- `test_*.py` - Unit tests
- `test_*_integration.py` - Integration tests
- Makes it easy to run them separately

### 5. **Skip Gracefully**
Use `@pytest.mark.skipif()` for tests that require external services:
```python
@pytest.mark.skipif(not mqtt_available, reason="MQTT broker not running")
def test_mqtt_real_connection():
    ...
```

### 6. **Clean Up Resources**
Always clean up in `finally` blocks:
```python
try:
    server.start()
    # ... test code ...
finally:
    server.stop()
```

---

## 🐛 Bugs Integration Tests Have Caught

### 1. WebSocket Handler Signature (YOU FOUND THIS!)
- **Bug:** `_handle_client(self, websocket, path)` vs `_handle_client(self, websocket)`
- **Impact:** Server crashed on every connection
- **Unit Tests:** All passed ✅
- **Integration Test:** Would have failed immediately ❌

### 2. (Future Bugs Will Be Listed Here)

---

## 🔮 Future Integration Tests To Add

### 1. Serial Device Integration
When we implement real serial devices:
```python
@pytest.mark.skipif(not serial_port_available, reason="No serial device")
def test_serial_device_real_communication():
    driver = SerialDriver("/dev/ttyUSB0")
    driver.send_effect("light", 100, 1000)
    # Verify actual serial communication
```

### 2. Unity/Unreal Integration
Test with actual VR clients:
```python
@pytest.mark.unity
def test_unity_client_websocket_integration():
    # Start server
    # Launch Unity client
    # Send effects
    # Verify Unity receives them
```

### 3. Cloud Integration
Test with AWS IoT or Azure IoT Hub:
```python
@pytest.mark.cloud
def test_aws_iot_mqtt_integration():
    # Connect to real AWS IoT
    # Publish effects
    # Verify delivery
```

---

## 📚 Resources

- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Integration Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Async Testing with pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

---

## ✅ Summary

**What Changed:**
1. ✅ Created 5 integration test files
2. ✅ Fixed the WebSocket handler signature bug
3. ✅ Learned the difference between unit and integration tests
4. ✅ Established pattern for future integration tests

**Key Takeaway:**
> **"Integration tests are slow, but they catch the bugs that matter most - the ones where your code meets the real world."**

Your discovery of the WebSocket bug proves that **both unit AND integration tests are essential**. Unit tests give us confidence in our logic, integration tests give us confidence in our real-world compatibility.

From now on, every new feature should have:
1. Unit tests (logic, edge cases)
2. At least one integration test (real library usage)

**Great find! 🎯**
