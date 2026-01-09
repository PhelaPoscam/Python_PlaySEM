# UI Demo Pages

This directory contains standalone HTML demo pages for testing PlaySEM GUI features.

## Contents

- **super_controller.html** (890 lines) - Full-featured controller UI demo
- **super_receiver.html** - Receiver/display UI for testing
- **mobile_device.html** - Mobile-optimized device control interface

## Purpose

These are **demo/testing pages**, not part of the main application. They can be:
- Served via `tools/test_server/phone_tester_server.py` (port 8091)
- Opened directly in browser for UI testing
- Used as reference for GUI component development

## Status

⚠️ **Standalone demos** - Not integrated with the main `gui/` application structure.

## Usage

Open directly in browser or serve via HTTP server:

```bash
# Option 1: Direct browser
open tools/ui_demos/super_controller.html

# Option 2: Via phone_tester_server.py (if configured)
python tools/test_server/phone_tester_server.py
```

## Related

- Main GUI: `gui/` (production application)
- Protocol examples: `examples/protocols/`
- Test server: `tools/test_server/app/`
