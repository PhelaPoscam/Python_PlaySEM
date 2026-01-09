# Phone Vibration Tester Server

**Purpose**: Simple HTTP server for testing phone vibration API on mobile devices.

## What It Does

Serves HTML test pages from `tools/web/` (phone vibration tester) on port 8091, accessible from mobile devices on the same WiFi network.

## Usage

```bash
python tools/test_server/phone_tester_server.py
```

Then on your phone:
1. Connect to same WiFi network as PC
2. Open browser: `http://YOUR_PC_IP:8091/phone_tester.html`
3. Tap buttons to test vibration patterns

## Features

- **CORS enabled** for mobile access
- **Auto IP detection** (displays local network IP)
- **Mobile-friendly** serving from `tools/web/`
- **Port 8091** (separate from main test server on 8090)

## Status

⚠️ **Note**: This is a standalone demo/testing utility, separate from the main PlaySEM test server architecture.

**Related Files**:
- `tools/web/phone_tester.html` (if exists - HTML UI for vibration testing)
- `tools/ui_demos/` (other HTML demo pages)

## Integration

This server is **NOT** part of the main modular architecture. It's a simple utility for mobile vibration testing during hardware development.
