# Development Documentation

Technical documentation for developers working on PlaySEM library internals, protocol servers, and testing infrastructure.

## 📚 Contents

### Protocol Implementation
- **[MULTI_PROTOCOL_DISCOVERY.md](MULTI_PROTOCOL_DISCOVERY.md)** - Multi-protocol device discovery mechanisms
- **[PROTOCOL_FIXES.md](PROTOCOL_FIXES.md)** - Issues fixed in protocol servers (HTTP 422, MQTT WinError, etc.)
- **[PROTOCOL_TESTING.md](PROTOCOL_TESTING.md)** - How to test protocol servers (MQTT, CoAP, WebSocket, HTTP, UPnP)
- **[SERIAL_TESTING_GUIDE.md](SERIAL_TESTING_GUIDE.md)** - Serial communication testing without hardware

## 🎯 When to Use

Use these docs when:
- ✅ Implementing or debugging protocol servers
- ✅ Testing without physical devices
- ✅ Adding new protocol support
- ✅ Contributing to PlaySEM core library

## 📖 For Users

If you're using PlaySEM (not developing it):
- **Getting Started** → See `../LIBRARY.md`
- **API Reference** → See `../reference/`
- **Migration Guide** → See `../REFACTORING.md`

---

**Last Updated**: December 10, 2025  
**Package Version**: playsem (official library)
