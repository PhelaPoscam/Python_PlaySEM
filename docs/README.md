# Project Documentation Index

This index centralizes links to documentation across the repository. Some documents have been consolidated under docs/ with stubs left at their original locations to preserve backward compatibility. Use this as the single entry point to discover guides, reference material, and testing procedures.

Conventions for adding new docs are in docs/CONVENTIONS.md.


- Getting Started
  - Root Overview and Quick Start: [README.md](../README.md)
  - Docs Index (this page): [docs/README.md](./README.md)

- Guides
  - [CONTROL_PANEL_GUIDE.md](./guides/CONTROL_PANEL_GUIDE.md)
  - [MOBILE_PHONE_SETUP.md](./guides/MOBILE_PHONE_SETUP.md)
  - [UPNP_GUIDE.md](./guides/UPNP_GUIDE.md)

- Reference / Architecture
  - [CONTROL_PANEL_ARCHITECTURE.md](./CONTROL_PANEL_ARCHITECTURE.md)
  - [UNIVERSAL_DRIVER_INTEGRATION.md](./UNIVERSAL_DRIVER_INTEGRATION.md)
  - Timeline Player Guide: [TIMELINE_PLAYER.md](./reference/TIMELINE_PLAYER.md)

- Testing
  - Device Testing Checklist: [DEVICE_TESTING_CHECKLIST.md](./DEVICE_TESTING_CHECKLIST.md)
  - Protocol Testing Guide: [PROTOCOL_TESTING.md](./testing/PROTOCOL_TESTING.md)
  - General Testing Notes: [TESTING.md](./archive/TESTING.md)
  - Integration Testing: [INTEGRATION_TESTING.md](./archive/INTEGRATION_TESTING.md)

- Roadmap & Planning
  - [ROADMAP.md](./ROADMAP.md)
  - Phase 2 Completion Notes: [PHASE2_COMPLETION.md](./archive/PHASE2_COMPLETION.md)
  - Phase 2 Enhancements: [PHASE2_ENHANCEMENTS.md](./archive/PHASE2_ENHANCEMENTS.md)

- Subsystem Docs located with code (kept in-place for now)
  - Control Panel README: [examples/control_panel/README.md](../examples/control_panel/README.md)
  - Control Panel Sample Timeline: [sample_timeline.xml](../examples/control_panel/sample_timeline.xml)

- External Clients & Web Tools
  - Clients (HTTP/MQTT/CoAP/UPnP/WebSocket): [examples/clients/](../examples/clients/)
  - Web Phone Tester: [web/phone_tester.html](../web/phone_tester.html) and [web/phone_tester_server.py](../web/phone_tester_server.py)
  - WebSocket Client Demo: [web/websocket_client.html](../web/websocket_client.html)

- Demos
  - See runnable demos under [demos/](../demos/)

- Source & Tests
  - Source code: [src/](../src/)
  - Tests: [tests/](../tests/)

- Archive
  - Archived docs directory: [docs/archive/](./archive/)


Housekeeping plan
- Maintain a single index here; avoid creating new README.md files scattered across code folders.
- When adding a new document:
  1) Prefer placing it under docs/guides, docs/reference, or docs/testing.
  2) Add a link to it in this index under the appropriate category.
  3) If a document must live alongside code (e.g., highly specific to a demo), add a short pointer in this index.

Status: Consolidation in progress. Selected docs have been moved into docs/ with stubs left in their original locations to avoid breaking links.