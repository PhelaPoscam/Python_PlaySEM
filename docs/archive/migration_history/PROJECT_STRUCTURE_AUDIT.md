# Project Structure Audit & Organization Plan

**Date**: 2025-12-10  
**Status**: Pre-Phase 3 Cleanup

---

## 📊 Current Project Structure Analysis

### 1. **playsem/** - Core Library ✅ KEEP & MAINTAIN

**Status**: Production-ready library  
**Purpose**: Core framework for sensory effects  
**Contents**:
```
playsem/
├── device_manager.py       ✅ Core component
├── effect_dispatcher.py    ✅ Core component
├── effect_metadata.py      ✅ Core component
├── device_registry.py      ✅ NEW (Phase 2)
├── __init__.py            ✅ Clean exports
├── config/
│   ├── __init__.py        ✅ Clean
│   └── loader.py          ✅ Configuration
├── drivers/
│   ├── __init__.py        ✅ Clean exports
│   ├── base_driver.py     ✅ Interface
│   ├── serial_driver.py   ✅ Implementation
│   ├── mqtt_driver.py     ✅ Implementation
│   ├── bluetooth_driver.py ✅ Implementation
│   └── mock_driver.py     ✅ Testing
└── effects/               ⚠️ Check what's here
```

**Actions**:
- ✅ Keep as-is (active library code)
- Check what's in `effects/` subdirectory
- Ensure all imports are clean

---

### 2. **examples/** - Usage Examples 🟡 REVIEW & ORGANIZE

**Status**: Partially useful  
**Contents**:
```
examples/
├── simple_cli.py          ✅ Good example
├── device_registry_demo.py ✅ Good example
├── __init__.py            ✅ Ok
└── server/                ⚠️ Check what's here
    └── __pycache__/
```

**Actions**:
- ✅ Keep `simple_cli.py` - clean example
- ✅ Keep `device_registry_demo.py` - good demo
- 🔍 Audit `server/` - might be obsolete
- Remove `__init__.py` if empty
- Consider renaming/organizing by use case

**Recommendation**: Keep only the two working examples, potentially organize by category if more are added

---

### 3. **gui/** - PyQt6 Interface ⚠️ OPTIONAL

**Status**: Optional component (works but not required)  
**Purpose**: Graphical interface  
**Contents**:
```
gui/
├── app.py                    ⚠️ Main app
├── app_controller.py        ⚠️ Logic
├── example_custom_protocols.py ⚠️ Example
├── quickstart.py            ⚠️ Launcher
├── README.md                ✅ Documentation
├── __init__.py              ✅ Ok
├── protocols/               ⚠️ Protocol implementations
├── ui/                      ⚠️ UI components
├── widgets/                 ⚠️ Custom widgets
└── __pycache__/
```

**Questions for Phase 3**:
- Is this actively maintained?
- Should it stay as optional component?
- Does it use Device Registry from playsem/?
- Could it be moved to `examples/gui/` instead?

**Recommendation**: 
- Keep it working but flag as "optional GUI"
- OR move to `examples/gui_app/` if it's just an example
- Update to use Device Registry from `playsem/`

---

### 4. **scripts/** - Utility Scripts 🟡 REVIEW

**Status**: Minimal  
**Contents**:
```
scripts/
└── run_tests.py         ⚠️ What does this do?
```

**Questions**:
- What does `run_tests.py` do?
- Can we just use `pytest` directly?
- Is this needed?

**Recommendation**: 
- Audit & potentially remove if redundant with `pytest`
- Or document its purpose

---

### 5. **src/** - Old Structure 🔴 DEPRECATED

**Status**: Deprecated (kept for backwards compatibility)  
**Contents**:
```
src/
├── config_loader.py        ❌ Use playsem/config/
├── device_capabilities.py  ❌ Check if used
├── device_manager.py       ❌ Use playsem/
├── effect_dispatcher.py    ❌ Use playsem/
├── effect_metadata.py      ❌ Use playsem/
├── main.py                 ❌ Old entry point
├── timeline.py             ❌ Check if used
├── __init__.py             ✅ Migration message
├── device_driver/          ❌ Use playsem/drivers/
└── protocol_servers/       ❌ Check if used
```

**Actions**:
- 🔴 Mark as DEPRECATED (already done)
- 📦 Archive to `archive/src_deprecated/` if taking up space
- 📝 Document in migration guide

**Recommendation**: 
- Keep as-is for backwards compatibility
- OR archive if not needed by any active code

---

### 6. **tests/** - Unit Tests ✅ KEEP & EXPAND

**Status**: Good coverage  
**Contents** (18 test files):
```
tests/
├── conftest.py
├── test_device_registry.py     ✅ NEW (Phase 2, 12 tests)
├── test_config_loader.py       ✅ Core library
├── test_device_manager.py      ✅ Core library
├── test_effect_dispatcher.py   ✅ Core library
├── test_effect_metadata.py     ✅ Core library
├── test_capabilities.py        ⚠️ Check
├── test_timeline.py            ⚠️ Check
├── test_gui_components.py      ⚠️ Optional (GUI)
├── test_gui_modules.py         ⚠️ Optional (GUI)
├── test_mqtt_broker.py         ⚠️ Protocol specific
├── test_coap_server_integration.py   ⚠️ Protocol specific
├── test_upnp_server.py         ⚠️ Protocol specific
├── test_websocket_server.py    ⚠️ Protocol specific
├── test_protocol_servers.py    ⚠️ Protocol specific
├── test_control_panel_server.py ⚠️ Protocol specific
├── test_routing_integration.py ⚠️ Integration
├── test_smoke_protocols.py     ⚠️ Smoke tests
├── test_integration.py         ⚠️ Integration
├── test_playwright_super_controller.py ⚠️ End-to-end
└── test_super_controller_ui.py ⚠️ GUI tests
```

**Organization needed**:
- Core library tests (5) → Keep together
- GUI tests (3) → Move to `tests/gui/`
- Protocol tests (5) → Move to `tests/protocols/`
- Integration tests (3) → Move to `tests/integration/`
- Smoke/E2E tests (2) → Move to `tests/e2e/`

**Recommendation**:
- Reorganize into subdirectories
- Keep core tests at root level
- Create proper test hierarchy

---

### 7. **tools/** - Platform Tools & Server 🟡 PHASE 3 TARGET

**Status**: Main refactoring target  
**Contents**:
```
tools/
├── get_capabilities.py      ⚠️ Utility
├── mock_device_demo.py      ⚠️ Demo
├── README.md               ✅ Documentation
├── __init__.py             ✅ Ok
├── test_server/            🎯 PHASE 3 FOCUS
│   ├── main.py            🔴 1879 lines - MONOLITHIC
│   ├── phone_tester_server.py ⚠️ Related?
│   └── __init__.py
├── bluetooth/              ⚠️ Protocol driver?
├── coap/                   ⚠️ Protocol driver?
├── http/                   ⚠️ Protocol driver?
├── mqtt/                   ⚠️ Protocol driver?
├── serial/                 ⚠️ Protocol driver?
├── timeline/               ⚠️ Timeline handling
├── ui/                     ⚠️ UI utilities
├── upnp/                   ⚠️ Protocol driver?
└── websocket/              ⚠️ Protocol driver?
```

**Phase 3 Work**:
- 🎯 Split `tools/test_server/main.py` (1879 lines) into modules:
  - Protocol handlers
  - Device registry integration
  - Effect routing
  - Configuration
  - Main server loop
  
- Organize protocol implementations
- Move protocol files to proper location
- Use Device Registry as core

**Recommendation**:
- This is the main Phase 3 target
- Keep structure as-is until Phase 3
- Will refactor into clean modules

---

### 8. **config/** - Configuration Files ✅ KEEP

**Status**: Configuration data  
**Contents**:
```
config/
├── devices.yaml           ✅ Device definitions
├── effects.yaml           ✅ Effect mappings
└── protocols.yaml         ✅ Protocol config
```

**Recommendation**:
- Keep as-is
- These are data files, not code
- Reference in documentation

---

### 9. **docs/** - Documentation 🟡 NEEDS ORGANIZATION

**Status**: Partially organized  
**Current structure**:
```
docs/
├── COMPLETION_SUMMARY.md  ✅ Current status
├── LIBRARY.md             ✅ API reference
├── PROJECT_CLEANUP.md     ✅ What changed
├── REFACTORING.md         ✅ Migration guide
├── index.md               ✅ Navigation
├── archive/               📦 Old docs
├── development/           ⚠️ Some useful, some old
├── guides/                ✅ User guides
└── reference/             ✅ Technical reference
```

**Issues to fix**:
- ❓ Redundancy check needed
- ❓ Dead links check
- ❓ Outdated content in development/
- ❓ Clear structure for Phase 3 docs

---

## 🎯 Organization Plan

### Phase: Documentation Audit & Cleanup (BEFORE Phase 3)

**Step 1: Docs Organization** (This step)
1. ✅ Create structure for Phase 3 documentation
2. ✅ Audit for redundancy
3. ✅ Consolidate overlapping guides
4. ✅ Remove outdated content
5. ✅ Create clear navigation

**Step 2: Project Cleanup** (This step)
1. ✅ Keep playsem/ as-is
2. ✅ Keep core tests
3. ❓ Reorganize tests/ structure
4. ❓ Decide on GUI (keep/move/archive)
5. ❓ Audit tools/ subdirectories
6. ❓ Archive old src/ if not needed

**Step 3: Phase 3 Preparation** (Before Phase 3)
1. Document what main.py does
2. Identify components to split
3. Plan new module structure
4. Set up test structure for new modules

---

## 📋 Specific Recommendations

### Keep As-Is (No Changes)
- ✅ `playsem/` - Core library
- ✅ `config/` - Configuration files
- ✅ `docs/` - Documentation (minor cleanup)
- ✅ Core tests in `tests/`

### Reorganize (Medium Priority)
- 🟡 `examples/` - Keep good ones, audit `server/`
- 🟡 `tests/` - Move to subdirectories by category
- 🟡 `tools/` - Audit structure, plan Phase 3

### Decision Needed (Low Priority)
- ❓ `gui/` - Keep as optional or move to examples?
- ❓ `scripts/` - Keep or remove?
- ❓ `src/` - Archive or keep for backwards compat?

### Documentation Tasks (HIGH PRIORITY)
1. **Create Phase 3 documentation section**
   - Document test reorganization plan
   - Document main.py components
   - Document refactoring strategy

2. **Consolidate overlapping guides**
   - Check for duplicate info
   - Remove outdated content
   - Add cross-references

3. **Create architecture diagram**
   - Show current structure
   - Show Phase 3 target structure
   - Document dependency flow

---

## 🔜 Next Actions

### Before Phase 3:

1. **Organize docs/** (URGENT)
   - [ ] Audit for redundancy
   - [ ] Remove outdated content
   - [ ] Consolidate overlapping sections
   - [ ] Create Phase 3 roadmap document

2. **Plan tests reorganization** (MEDIUM)
   - [ ] Document test structure plan
   - [ ] Create test categories
   - [ ] Plan where to move what

3. **Document main.py structure** (HIGH)
   - [ ] List all components in main.py
   - [ ] Identify refactoring boundaries
   - [ ] Plan new module structure

4. **Make folder decisions** (LOW)
   - [ ] GUI: Keep/Move/Archive?
   - [ ] scripts/: Keep/Remove?
   - [ ] src/: Archive/Keep?
   - [ ] examples/server/: Delete/Keep?

---

## 📊 Summary Table

| Folder | Status | Action | Priority |
|--------|--------|--------|----------|
| playsem/ | ✅ Ready | Keep | ✅ |
| examples/ | 🟡 Partial | Audit | 🟡 |
| gui/ | ⚠️ Optional | Decide | 🟡 |
| scripts/ | 🟡 Minimal | Decide | 🔴 |
| src/ | 🔴 Deprecated | Archive/Keep | 🟡 |
| tests/ | ✅ Good | Reorganize | 🟡 |
| tools/ | 🎯 Target | Phase 3 | ✅ |
| config/ | ✅ Data | Keep | ✅ |
| docs/ | 🟡 Partial | Reorganize | ✅ |

---

## ⚠️ Critical Path for Phase 3

1. **NOW**: Organize docs and plan structure
2. **THEN**: Reorganize tests if needed
3. **THEN**: Document main.py components
4. **PHASE 3**: Refactor tools/test_server/main.py using Device Registry

Ready to proceed with docs organization? 👇
