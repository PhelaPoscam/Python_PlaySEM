"""Playwright end-to-end UI tests for Super Controller.

Requires browser installation:
    python -m playwright install

These tests start a uvicorn server instance in a background thread and then
exercise the unified UI: connection status, effect send button, history update.
"""

import threading
import time
import socket
from urllib.request import urlopen
from urllib.error import URLError
import pytest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

import uvicorn
from tools.test_server.main import ControlPanelServer


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server_thread():
    server_port = _get_free_port()
    base_url = f"http://127.0.0.1:{server_port}"

    server = ControlPanelServer()
    config = uvicorn.Config(
        server.app,
        host="127.0.0.1",
        port=server_port,
        log_level="warning",
    )
    uvicorn_server = uvicorn.Server(config)

    t = threading.Thread(target=uvicorn_server.run, daemon=True)
    t.start()

    # Wait until startup flag and health endpoint are responsive.
    started = False
    for _ in range(80):
        if uvicorn_server.started:  # type: ignore[attr-defined]
            started = True
            try:
                with urlopen(f"{base_url}/health", timeout=1.0) as response:
                    if response.status == 200:
                        break
            except URLError:
                pass
        time.sleep(0.1)

    if not started:
        pytest.fail("Playwright fixture failed to start uvicorn server")

    yield base_url

    uvicorn_server.should_exit = True
    t.join(timeout=3)


@pytest.mark.skipif(sync_playwright is None, reason="Playwright not installed")
@pytest.mark.timeout(30)
def test_ui_basic_flow(server_thread):
    base_url = server_thread
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(
            f"{base_url}/super_controller", wait_until="domcontentloaded"
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
