import sys
import subprocess
import time
from pathlib import Path

import httpx
import pytest

# Ensure project root (and gui package) are on sys.path before imports/collection
root_dir = Path(__file__).resolve().parent.parent
gui_dir = root_dir / "gui"
for path in (root_dir, gui_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure(config):
    """Guarantee sys.path contains the project root during collection."""
    for path in (root_dir, gui_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


@pytest.fixture(scope="session")
def live_server():
    """
    Fixture that starts the FastAPI test server in a separate process
    and yields the server's base URL.
    """
    server_host = "127.0.0.1"
    server_port = 8090
    server_url = f"http://{server_host}:{server_port}"

    # Run the server as a module to pick up package imports
    command = [sys.executable, "-m", "tools.test_server.main"]
    process = subprocess.Popen(command, cwd=root_dir)

    # Wait for the server to be ready
    health_url = f"{server_url}/health"
    is_ready = False
    start_time = time.time()
    timeout = 30  # seconds

    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                response = client.get(health_url)
                if response.status_code == 200 and response.json() == {
                    "status": "ok"
                }:
                    is_ready = True
                    break
        except httpx.RequestError:
            time.sleep(0.5)  # Wait and retry

    if not is_ready:
        process.terminate()
        pytest.fail(f"Server did not start within {timeout} seconds.")

    # Yield the server URL to the tests
    yield server_url

    # Teardown: stop the server
    process.terminate()
    process.wait()
