"""
PythonPlaySEM GUI Application.

A desktop GUI application for controlling sensory effects across multiple devices
using various communication protocols (WebSocket, HTTP, MQTT, CoAP, etc).
"""

import sys
import asyncio
import logging
from pathlib import Path

from qasync import QEventLoop
from PyQt6.QtWidgets import QApplication

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Main entry point for the GUI application."""
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
