"""Playwright end-to-end UI tests for Super Controller.

Requires browser installation:
    python -m playwright install

These tests start a uvicorn server instance in a background thread and then
exercise the unified UI: connection status, effect send button, history update.
"""

import threading
import time
import pytest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

import uvicorn
from tools.test_server.main import ControlPanelServer

SERVER_PORT = 8091
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


@pytest.fixture(scope="module")
def server_thread():
    server = ControlPanelServer()
    config = uvicorn.Config(
        server.app,
        host="127.0.0.1",
        port=SERVER_PORT,
        log_level="warning",
    )
    uvicorn_server = uvicorn.Server(config)

    t = threading.Thread(target=uvicorn_server.run, daemon=True)
    t.start()

    # Wait until server appears responsive
    for _ in range(50):
        if uvicorn_server.started:  # type: ignore
            break
        time.sleep(0.1)
    yield
    # No formal shutdown path needed (daemon thread exits with pytest)


@pytest.mark.skipif(sync_playwright is None, reason="Playwright not installed")
@pytest.mark.timeout(30)
def test_ui_basic_flow(server_thread):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(
            f"{BASE_URL}/super_controller", wait_until="domcontentloaded"
        )

        # Assert essential elements present
        assert page.locator("#deviceList").count() == 1
        assert page.locator("#sendEffect").is_visible()
        assert page.locator("#effectHistory").is_visible()

        # Trigger a protocol effect send (WebSocket)
        page.click("#sendEffect")
        time.sleep(0.5)  # Allow websocket message roundtrip

        # Verify history updated (first item should now reference Sent)
        history_entries = page.locator(".effect-item")
        assert history_entries.count() >= 1
        first_text = history_entries.first.text_content() or ""
        assert "Sent" in first_text or "Effect" in first_text

        browser.close()
