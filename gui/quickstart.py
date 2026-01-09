#!/usr/bin/env python3
"""
Quick Start Example - PythonPlaySEM Desktop GUI

This script demonstrates how to:
1. Install dependencies
2. Start the backend server
3. Launch the GUI application

Usage:
    python gui/quickstart.py
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_pyqt6():
    """Check if PyQt6 is installed."""
    try:
        import PyQt6 as _  # noqa: F401

        logger.info("✓ PyQt6 is installed")
        return True
    except ImportError:
        logger.error("✗ PyQt6 not found")
        logger.error("  Install with: pip install PyQt6==6.7.0")
        return False


def check_dependencies():
    """Check all required dependencies."""
    logger.info("Checking dependencies...")

    dependencies = {
        "websockets": "websockets",
        "httpx": "httpx",
        "fastapi": "fastapi",
    }

    missing = []
    for name, package in dependencies.items():
        try:
            __import__(package)
            logger.info(f"✓ {name} is installed")
        except ImportError:
            missing.append(f"  pip install {package}")
            logger.error(f"✗ {name} not found")

    if missing:
        logger.error("\nMissing dependencies. Install with:")
        for cmd in missing:
            logger.error(cmd)
        return False

    return True


def start_backend():
    """Start the backend server."""
    logger.info("\nStarting backend server...")
    logger.info("  Command: python examples/server/main.py")

    try:
        import uvicorn as _  # noqa: F401

        logger.info("✓ uvicorn is available")
    except ImportError:
        logger.error("✗ uvicorn not found")
        logger.error("  Install with: pip install uvicorn")
        return None

    logger.warning("\n⚠️  Backend server must be running separately!")
    logger.warning("    In a different terminal, run:")
    logger.warning("    python examples/server/main.py")
    logger.warning("")

    return True


def launch_gui():
    """Launch the GUI application."""
    logger.info("\nLaunching GUI application...")

    try:
        from gui.ui import MainWindow
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()

        logger.info("✓ GUI launched successfully")
        logger.info("\nQuick Start Guide:")
        logger.info("  1. Connection tab: Click 'Connect'")
        logger.info("  2. Devices tab: Click 'Scan Devices'")
        logger.info("  3. Select a device from the list")
        logger.info("  4. Effects tab: Adjust parameters and send effects")

        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"✗ Failed to launch GUI: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("PythonPlaySEM Desktop GUI - Quick Start")
    logger.info("=" * 60)

    # Check Python version
    if sys.version_info < (3, 10):
        logger.error(f"✗ Python 3.10+ required (you have {sys.version})")
        return False

    logger.info(f"✓ Python {sys.version.split()[0]}")

    # Check dependencies
    if not check_pyqt6():
        return False

    if not check_dependencies():
        return False

    # Start backend
    start_backend()

    # Launch GUI
    logger.info("\n" + "=" * 60)
    launch_gui()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
