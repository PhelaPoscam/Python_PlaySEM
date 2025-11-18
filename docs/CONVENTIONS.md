# Documentation Conventions

Purpose: keep documentation discoverable, consistent, and centralized while avoiding Markdown file sprawl.

General rules
- Single entry point: docs/README.md is the master index. Always add new links there.
- Prefer docs/ over scattering docs alongside code. Only colocate docs next to code when they are tightly coupled and short.
- Keep files small and task-focused. Split long documents into clear sections or multiple files if needed.
- Use relative links that work on GitHub and local clones.

Where to put new docs
- Getting started and onboarding: docs/getting-started/ (create if needed)
- How-to guides and step-by-step workflows: docs/guides/
- Reference, architecture, specifications, and longer-form explanations: docs/reference/
- Testing strategies, playbooks, and procedures: docs/testing/
- Roadmaps and planning: docs/roadmap/
- Archived or superseded content: docs/archive/

File naming
- Use Upper_Snake_Case with short, descriptive names, e.g. CONTROL_PANEL_GUIDE.md, MQTT_SERVER_REFERENCE.md
- Prefix families of docs consistently, e.g. TIMELINE_*, PROTOCOL_*, DRIVER_*
- Keep names stable to preserve links. If you must rename, leave a stub file that points to the new location.

Linking and indexing
- After adding a document, update docs/README.md under the correct category.
- If you colocate a doc next to code (examples/, demos/, src/), add a short pointer entry in docs/README.md to that location.
- Prefer section anchors (#section-title) for deep links within longer documents.

Co-location vs centralization
- Co-locate a doc if:
  - It is specific to a single example/demo and unlikely to be reused elsewhere, and
  - It is short (e.g., local README with run instructions)
- Otherwise, place it in docs/ and link to it from the code directory's README.

Stubs policy (non-destructive moves)
- When moving an existing document to docs/, leave a stub file at the old path with:
  - A one-paragraph explanation
  - A link to the new canonical location
- Keep the stub for at least one release to avoid breaking bookmarks.

Structure examples
- docs/guides/CONTROL_PANEL_GUIDE.md (how to use the control panel)
- docs/reference/TIMELINE_PLAYER.md (timeline player details)
- docs/testing/PROTOCOL_TESTING.md (protocol validation checklist)

Review checklist for new docs
- Does the document belong under guides, reference, or testing?
- Is the filename short, descriptive, and stable?
- Is it linked from docs/README.md?
- Are external links validated?

Maintenance
- Periodically sweep for new .md files outside docs/ and either link them from docs/README.md or migrate them into docs/ with stubs left behind.
- Move stale content to docs/archive/ to keep the active surface small.
