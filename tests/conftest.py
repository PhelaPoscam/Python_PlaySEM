import sys
from pathlib import Path
import pytest
import subprocess
import time
import httpx

# Add the project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
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
    server_script = root_dir / "tools" / "test_server" / "main.py"

    # Command to run the server
    command = [sys.executable, str(server_script)]

    # Start the server process
    process = subprocess.Popen(command)

    # Wait for the server to be ready
    health_url = f"{server_url}/health"
    is_ready = False
    start_time = time.time()
    timeout = 30  # seconds

    while time.time() - start_time < timeout:
        try:
            with httpx.Client() as client:
                response = client.get(health_url)
                if response.status_code == 200 and response.json() == {"status": "ok"}:
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