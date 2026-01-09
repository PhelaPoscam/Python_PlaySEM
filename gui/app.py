"""
PythonPlaySEM GUI Application.

A desktop GUI application for controlling sensory effects across multiple devices
using various communication protocols (WebSocket, HTTP, MQTT, CoAP, etc).
"""

import sys
import asyncio
import logging

from qasync import QEventLoop
from PyQt6.QtWidgets import QApplication

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Expect `playsem` to be installed (e.g., `pip install -e .`).
=======
if __package__ in (None, ""):
    raise RuntimeError(
        "Execute the GUI as a module to resolve imports: python -m gui.app"
    )
>>>>>>> refactor/modular-server


def main():
    """Main entry point for the GUI application."""
    try:
        from gui.ui import MainWindow
    except ModuleNotFoundError:
        # Fallback for editable/local runs if package is not installed yet.
        PROJECT_ROOT = Path(__file__).parent.parent
        sys.path.insert(0, str(PROJECT_ROOT))
        from gui.ui import MainWindow

    logger.info("Starting PythonPlaySEM GUI Application")

    # Create application with async support
    app = QApplication(sys.argv)

    # Install the qasync event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("GUI application started successfully")

    # Run event loop
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
