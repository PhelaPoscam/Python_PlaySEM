"""
UI Routes - Web UI serving endpoints.

Endpoints:
- GET / - Main controller
- GET /controller - Controller UI
- GET /receiver - Receiver UI
- GET /super_controller - Super controller UI
- GET /mobile_device - Mobile device UI
- GET /static/{path} - Static assets
"""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse


class UIRoutes:
    """Routes for UI serving."""

    def __init__(self, router: APIRouter, ui_files_dir: Path):
        """Initialize UI routes.

        Args:
            router: FastAPI router
            ui_files_dir: Directory containing UI files
        """
        self.router = router
        self.ui_files_dir = ui_files_dir
        self._register_routes()

    def _register_routes(self):
        """Register UI routes."""

        @self.router.get("/")
        async def root():
            """Serve main controller UI."""
            ui_file = self.ui_files_dir / "controller.html"
            if ui_file.exists():
                return FileResponse(str(ui_file), media_type="text/html")
            return HTMLResponse("<h1>PlaySEM Controller</h1>")

        @self.router.get("/controller")
        async def controller():
            """Serve controller UI."""
            ui_file = self.ui_files_dir / "controller.html"
            if ui_file.exists():
                return FileResponse(str(ui_file), media_type="text/html")
            return HTMLResponse("<h1>PlaySEM Controller</h1>")

        @self.router.get("/receiver")
        async def receiver():
            """Serve receiver UI."""
            ui_file = self.ui_files_dir / "receiver.html"
            if ui_file.exists():
                return FileResponse(str(ui_file), media_type="text/html")
            return HTMLResponse("<h1>PlaySEM Receiver</h1>")

        @self.router.get("/super_controller")
        async def super_controller():
            """Serve super controller UI."""
            ui_file = self.ui_files_dir / "super_controller.html"
            if ui_file.exists():
                return FileResponse(str(ui_file), media_type="text/html")
            return HTMLResponse("<h1>PlaySEM Super Controller</h1>")

        @self.router.get("/mobile_device")
        async def mobile_device():
            """Serve mobile device UI."""
            ui_file = self.ui_files_dir / "mobile_device.html"
            if ui_file.exists():
                return FileResponse(str(ui_file), media_type="text/html")
            return HTMLResponse("<h1>PlaySEM Mobile Device</h1>")

        @self.router.get("/static/{path:path}")
        async def serve_static(path: str):
            """Serve static assets.

            Args:
                path: Asset path

            Returns:
                Static file response
            """
            file_path = self.ui_files_dir / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            return HTMLResponse("Not found", status_code=404)
