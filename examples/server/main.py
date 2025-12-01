# Ensure repository root is importable when running as a script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.test_server.main import ControlPanelServer, ConnectedDevice

__all__ = ["ControlPanelServer", "ConnectedDevice"]


def _run(host: str = "127.0.0.1", port: int = 8090):
    """Run the example Control Panel Server with uvicorn on the given host/port."""
    import uvicorn

    server = ControlPanelServer()
    uvicorn.run(server.app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    # Basic CLI: allow overriding host/port via env or simple args in the future
    _run()
