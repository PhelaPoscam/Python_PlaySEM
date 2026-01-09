if __package__ in (None, ""):
    raise RuntimeError(
        "Execute via module to ensure package imports work: python -m examples.server.main"
    )

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
