"""Simple GUI and controller component tests."""

import os
import sys

import pytest
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_controller():
    """Test AppController creation and initialization."""
    print("\n" + "=" * 60)
    print("Testing AppController")
    print("=" * 60)

    try:
        from gui.app_controller import AppController

        # Create controller
        print("[1] Creating AppController...")
        controller = AppController()
        print("[+] Created successfully")

        # Check state
        print("[2] Checking initial state...")
        assert not controller.is_running, "Should not be running initially"
        assert controller.protocol is None, "Should have no protocol initially"
        print("[+] Initial state correct")

        # Check protocols
        print("[3] Checking available protocols...")
        from gui.protocols import ProtocolFactory

        protocols = ProtocolFactory.available_protocols()
        print(f"[+] Available: {protocols}")
        assert "websocket" in protocols
        assert "http" in protocols

        # Check devices
        print("[4] Checking device dictionary...")
        assert isinstance(controller.devices, dict)
        print("[+] Device dict initialized (empty)")

        print("\n[+] AppController tests PASSED\n")
        return True

    except Exception as e:
        logger.error(f"[X] AppController test failed: {e}", exc_info=True)
        return False


@pytest.mark.skipif(
    not os.environ.get("DISPLAY") and sys.platform.startswith("linux"),
    reason="GUI tests require display server (skip on headless Linux CI)",
)
def test_gui():
    """Test GUI component creation."""
    print("\n" + "=" * 60)
    print("Testing GUI Components")
    print("=" * 60)

    try:
        from PyQt6.QtWidgets import QApplication
        from gui.ui.main_window import MainWindow

        # Create QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        # Create main window
        print("[1] Creating MainWindow...")
        window = MainWindow()
        print("[+] Window created")

        # Check title
        print("[2] Checking window title...")
        title = window.windowTitle()
        print(f"[+] Title: '{title}'")

        # Check components exist
        print("[3] Checking UI components...")
        assert hasattr(window, "connection_panel"), "No connection_panel"
        print("[+] connection_panel exists")

        assert hasattr(window, "device_panel"), "No device_panel"
        print("[+] device_panel exists")

        assert hasattr(window, "effect_panel"), "No effect_panel"
        print("[+] effect_panel exists")

        assert hasattr(window, "controller"), "No controller"
        print("[+] controller exists")

        # Check controller is AppController
        print("[4] Checking controller type...")
        from gui.app_controller import AppController

        assert isinstance(window.controller, AppController)
        print("[+] Controller is AppController")

        # Clean up
        window.close()

        print("\n[+] GUI component tests PASSED\n")
        return True

    except Exception as e:
        logger.error(f"[X] GUI test failed: {e}", exc_info=True)
        try:
            window.close()
        except:
            pass
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PythonPlaySEM GUI Component Tests")
    print("=" * 70)

    results = {}

    # Test controller
    results["AppController"] = test_controller()

    # Test GUI
    results["GUI Components"] = test_gui()

    # Print summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    for name, result in results.items():
        status = "[+] PASS" if result else "[X] FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
