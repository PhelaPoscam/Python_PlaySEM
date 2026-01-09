import sys
import pytest
import subprocess
import time
import httpx
from pathlib import Path

# CRITICAL: Add root to sys.path BEFORE any imports
# This must happen during module load, not during test collection
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def pytest_configure(config):
    """
    Pytest hook that runs early in the startup process.
    Ensures project root is in sys.path before test discovery.
    """
    # Double-check root_dir is in sys.path (should already be from module load)
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))


@pytest.fixture(scope="session")
def live_server():
    """
    Fixture that starts the FastAPI test server in a separate process
    and yields the server's base URL.
    """
    server_host = "127.0.0.1"
    server_port = 8090
    server_url = f"http://{server_host}:{server_port}"
    # Command to run the server as module (new architecture, with /health)
    command = [
        sys.executable,
        "-m",
        "tools.test_server.main_new",
    ]

    # Start the server process
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
