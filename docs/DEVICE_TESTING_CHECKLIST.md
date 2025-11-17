# 📋 Device Testing Checklist

Use this checklist to systematically test your devices with PythonPlaySEM.

---

## 🎯 Phase 3.5 Goals

- [ ] Test mobile phone vibration via Web API
- [ ] Test mobile phone via Bluetooth BLE
- [ ] Test Arduino/ESP32 via Serial USB
- [ ] Measure end-to-end latency
- [ ] Document performance characteristics
- [ ] Create baseline metrics before Phase 4 optimization

---

## 📱 Mobile Phone Testing

### Test 1: Web Vibration API ✅ (Easiest!)

**Setup:**
- [ ] Open `examples/web/phone_tester.html` on smartphone
- [ ] Verify "Vibration API supported" message shows

**Basic Tests:**
- [ ] Test "Short Buzz" (200ms) - Should feel brief tap
- [ ] Test "Medium" (1s) - Should feel clear pulse
- [ ] Test "Strong" (2s) - Should feel sustained vibration
- [ ] Test "Maximum" (3s) - Should feel intense vibration

**Custom Tests:**
- [ ] Set intensity to 20% - Test (should be gentle)
- [ ] Set intensity to 50% - Test (should be moderate)
- [ ] Set intensity to 80% - Test (should be strong)
- [ ] Set duration to 500ms - Test (half second)
- [ ] Set duration to 2000ms - Test (2 seconds)

**Pattern Tests:**
- [ ] S.O.S Pattern - Should feel short-short-short-long
- [ ] Triple Pulse - Should feel 3 distinct pulses
- [ ] Rapid Fire - Should feel rapid succession
- [ ] Crescendo - Should feel increasing intensity

**Performance:**
- Total tests completed: ____
- Average duration: ____ ms
- Did all patterns work? ☐ Yes ☐ No
- Any unexpected behavior? ________________

---

### Test 2: Bluetooth BLE Integration

**Prerequisites:**
- [ ] Install BLE app (nRF Connect for Android / LightBlue for iOS)
- [ ] Read `docs/MOBILE_PHONE_SETUP.md`
- [ ] Know BLE UUIDs (Service: 180A, Characteristic: 2A56)

**Setup Phase:**
- [ ] Open BLE app on phone
- [ ] Create BLE peripheral
- [ ] Add service (UUID: 180A)
- [ ] Add characteristic (UUID: 2A56)
- [ ] Set properties: Read, Write, Notify
- [ ] Start advertising with name "MyPhone_Vibrator"
- [ ] Verify advertising status shows "Active"

**Discovery Phase:**
- [ ] Open Control Panel (http://localhost:8090)
- [ ] Click "Connect" to server
- [ ] Select "Bluetooth (BLE)" from dropdown
- [ ] Click "Scan for Devices"
- [ ] Wait for scan to complete (5 seconds)
- [ ] Verify phone appears in discovered devices list
- [ ] Device name matches: ________________
- [ ] Device address noted: ________________

**Connection Phase:**
- [ ] Click "Connect" button next to phone
- [ ] Wait for connection confirmation
- [ ] Phone appears in "Connected Devices" list
- [ ] Connection status shows green dot
- [ ] Device added to "Target Device" dropdown

**Effect Testing:**
- [ ] Select phone from "Target Device" dropdown
- [ ] Choose "vibration" effect type
- [ ] Click "Short Buzz" preset
  - [ ] Effect sent (check activity log)
  - [ ] Latency recorded: ____ ms
  - [ ] Phone vibrated: ☐ Yes ☐ No
- [ ] Click "Medium Pulse" preset
  - [ ] Latency: ____ ms
  - [ ] Vibration felt: ☐ Yes ☐ No
- [ ] Click "Strong Vibe" preset
  - [ ] Latency: ____ ms
  - [ ] Vibration felt: ☐ Yes ☐ No
- [ ] Custom test: 75% intensity, 1500ms duration
  - [ ] Latency: ____ ms
  - [ ] Vibration felt: ☐ Yes ☐ No

**Performance Metrics:**
- Average latency: ____ ms
- Minimum latency: ____ ms
- Maximum latency: ____ ms
- Success rate: ____ / ____ (ratio)
- Connection stable: ☐ Yes ☐ No
- Any disconnections: ☐ Yes ☐ No

**Troubleshooting (if needed):**
- [ ] Restarted BLE advertising
- [ ] Unpaired device from phone settings
- [ ] Checked BLE app permissions
- [ ] Verified characteristic properties
- [ ] Tried shorter device name
- [ ] Checked phone battery saver mode off

---

## 🔌 Arduino / ESP32 Serial Testing

### Test 3: Serial USB Connection

**Prerequisites:**
- [ ] Arduino/ESP32 connected via USB
- [ ] Drivers installed (CH340, FTDI, etc.)
- [ ] Know COM port number (check Device Manager on Windows)

**Hardware Setup:**
- Device type: ________________ (Arduino Uno, ESP32, etc.)
- COM port: ________________
- Baudrate: ________________ (usually 9600)
- USB cable quality: ☐ Good ☐ Questionable

**Discovery Phase:**
- [ ] Open Control Panel
- [ ] Select "Serial (USB)" from dropdown
- [ ] Click "Scan for Devices"
- [ ] Verify device appears in list
- [ ] Device description: ________________
- [ ] COM port matches expected: ☐ Yes ☐ No

**Connection Phase:**
- [ ] Click "Connect" button
- [ ] Connection confirmed in activity log
- [ ] Device appears in connected devices
- [ ] No errors shown: ☐ Yes ☐ No

**Effect Testing:**
- [ ] Select device from dropdown
- [ ] Send test command (any effect type)
- [ ] Check serial monitor/log for received data
- [ ] Latency: ____ ms
- [ ] Command format correct: ☐ Yes ☐ No

**Arduino Sketch (if available):**
```cpp
// Paste your Arduino code here for reference
// Should read serial data and respond
```

**Performance:**
- Serial baudrate: ________________
- Average latency: ____ ms
- Data received correctly: ☐ Yes ☐ No
- Connection stable: ☐ Yes ☐ No

---

## 📊 Latency Measurements

### End-to-End Latency Testing

**Test Configuration:**
- Device type: ________________
- Connection type: ________________ (BLE, Serial, MQTT)
- Network conditions: ________________

**Test Series 1: Single Effects**
| Test # | Effect Type | Intensity | Duration | Latency (ms) | Success |
|--------|-------------|-----------|----------|--------------|---------|
| 1      | Vibration   | 50%       | 1000ms   | ____         | ☐       |
| 2      | Vibration   | 20%       | 200ms    | ____         | ☐       |
| 3      | Vibration   | 80%       | 2000ms   | ____         | ☐       |
| 4      | Light       | 50%       | 1000ms   | ____         | ☐       |
| 5      | Wind        | 50%       | 1000ms   | ____         | ☐       |

**Test Series 2: Rapid Fire (5 effects in quick succession)**
| Test # | Interval (ms) | Avg Latency | Success Rate |
|--------|---------------|-------------|--------------|
| 1      | 100ms         | ____        | ____ / 5     |
| 2      | 250ms         | ____        | ____ / 5     |
| 3      | 500ms         | ____        | ____ / 5     |
| 4      | 1000ms        | ____        | ____ / 5     |

**Summary Statistics:**
- Overall average latency: ____ ms
- Minimum observed: ____ ms
- Maximum observed: ____ ms
- Standard deviation: ____ ms
- 95th percentile: ____ ms

**Baseline Metrics (Before Phase 4 Optimization):**
```
Device: ________________
Connection: ________________
Average Latency: ____ ms
Success Rate: _____%
Notes: ________________________________
```

---

## 🔧 System Integration Testing

### Test 4: Multiple Protocols + Multiple Drivers

**Goal:** Verify architecture is truly universal

**Setup:**
- [ ] Phone connected via Bluetooth
- [ ] Arduino connected via Serial (if available)
- [ ] MQTT device ready (optional)

**Test Scenario:**
- [ ] Send effect to phone (BLE) - Works: ☐ Yes ☐ No
- [ ] Send effect to Arduino (Serial) - Works: ☐ Yes ☐ No
- [ ] Send effect to MQTT device - Works: ☐ Yes ☐ No
- [ ] Send effects to multiple devices simultaneously
  - [ ] All devices respond: ☐ Yes ☐ No
  - [ ] No conflicts/errors: ☐ Yes ☐ No

---

## 🎯 Success Criteria

### Minimum Viable Testing (MVP)
- [ ] Phone vibration works via Web API ✅ (Essential!)
- [ ] Control panel loads and connects ✅
- [ ] Can scan for at least one device type ✅
- [ ] Can send effects successfully ✅
- [ ] Latency measured < 200ms ✅

### Full Testing Complete
- [ ] Phone tested with Web API ✅
- [ ] Phone tested with Bluetooth BLE ✅
- [ ] Serial device tested (Arduino/ESP32) ✅
- [ ] Latency measurements documented ✅
- [ ] Performance baseline established ✅
- [ ] All issues documented in notes ✅

### Ready for Phase 4
- [ ] MVP criteria met ✅
- [ ] At least 2 device types tested ✅
- [ ] Latency baseline < 200ms ✅
- [ ] Connection stability verified ✅
- [ ] Test report created ✅

---

## 📝 Notes and Observations

### What Worked Well:
```
(Note your successes here)


```

### Issues Encountered:
```
(Note problems, workarounds, errors)


```

### Performance Surprises:
```
(Unexpected latency, behavior, etc.)


```

### Recommendations for Phase 4:
```
(What should be optimized?)


```

---

## 📅 Testing Log

| Date | Time | Tester | Device | Result | Notes |
|------|------|--------|--------|--------|-------|
|      |      |        |        |        |       |
|      |      |        |        |        |       |
|      |      |        |        |        |       |

---

## ✅ Sign-Off

**Testing Completed By:** ____________________

**Date:** ____________________

**Phase 3.5 Status:** ☐ Complete ☐ Partial ☐ Blocked

**Ready for Phase 4?** ☐ Yes ☐ No ☐ With Reservations

**Notes:**
```


```

---

**Next:** Once testing is complete, proceed to Phase 4 (Delay Compensation) using the baseline metrics established here! 🚀
