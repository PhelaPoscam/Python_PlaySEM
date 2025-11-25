# Archive - Historical Documentation

This folder contains documentation from **completed project phases** that is no longer actively needed but preserved for historical reference.

---

## 📦 Archived Files

### Phase 2 Documentation (November 2025)
- **PHASE2_COMPLETION.md** - Phase 2 summary: MQTT, WebSocket, CoAP, UPnP, HTTP REST servers
- **PHASE2_ENHANCEMENTS.md** - Authentication and HTTP REST API additions
- **TESTING.md** - Original testing guide for WebSocket and MQTT servers
- **INTEGRATION_TESTING.md** - Integration testing methodology and lessons learned

---

## ℹ️ Why Archived?

These documents were essential during development but are now **superseded** by:

- **Current user guides** in `docs/guides/` (CONTROL_PANEL_GUIDE, UPNP_GUIDE, etc.)
- **Active project documentation** in `docs/` (ROADMAP.md, DEVICE_TESTING_CHECKLIST.md)
- **Main README.md** with up-to-date installation and usage instructions

---

## 📖 What's in the Archive?

### PHASE2_COMPLETION.md
- Comprehensive Phase 2 summary
- UPnP server implementation details
- Test results and statistics
- Lines of code added: ~1,590

### PHASE2_ENHANCEMENTS.md
- Authentication features (MQTT TLS, WebSocket WSS, HTTP API keys)
- HTTP REST API documentation
- Security best practices
- Production recommendations

### TESTING.md
- Original WebSocket and MQTT testing guides
- Step-by-step testing procedures
- Troubleshooting for mosquitto
- Public broker testing instructions

### INTEGRATION_TESTING.md
- The WebSocket bug discovery story
- Unit tests vs integration tests comparison
- Lessons learned about API compatibility
- Integration test examples and best practices

---

## 🎯 When to Reference Archive

**Use archived docs when:**
- Researching past implementation decisions
- Understanding why certain choices were made
- Learning about bugs that were fixed
- Historical context for architecture

**Use current docs when:**
- Actually using the system
- Testing features
- Deploying to production
- Developing new features

---

## 🔄 Migration Path

If a document becomes actively useful again, it should be:
1. Reviewed and updated
2. Moved back to `docs/` or `docs/guides/`
3. Linked from `docs/README.md`

---

**Archive Created**: November 17, 2025  
**Reason**: Consolidation after Phase 3 completion
