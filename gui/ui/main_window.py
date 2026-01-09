"""
Main application window for PythonPlaySEM GUI.
"""

import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QTabWidget,
    QListWidget,
)
from PyQt6.QtCore import pyqtSignal, QObject
from qasync import asyncSlot

from ..app_controller import AppController, ConnectionConfig
from .connection_panel import ConnectionPanel
from .device_panel import DevicePanel
from .effect_panel import EffectPanel
from .status_bar import StatusBarWidget

logger = logging.getLogger(__name__)


class SignalBridge(QObject):
    """Bridge for emitting Qt signals from async code."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    device_list_updated = pyqtSignal(list)
    effect_sent = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PythonPlaySEM Control Panel")
        self.setGeometry(100, 100, 1200, 800)

        # Controller
        self.controller = AppController()
        self.setup_callbacks()

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Tab widget for different panels
        tabs = QTabWidget()

        # Connection panel
        self.connection_panel = ConnectionPanel()
        self.connection_panel.connect_requested.connect(self.on_connect)
        self.connection_panel.disconnect_requested.connect(self.on_disconnect)
        self.connection_panel.mqtt_broker_requested.connect(
            self.on_start_mqtt_broker
        )
        self.connection_panel.protocol_server_requested.connect(
            self.on_protocol_server_requested
        )
        tabs.addTab(self.connection_panel, "Connection")

        # Device panel
        self.device_panel = DevicePanel()
        self.device_panel.device_selected.connect(self.on_device_selected)
        self.device_panel.scan_requested.connect(self.on_scan_devices)
        tabs.addTab(self.device_panel, "Devices")

        # Effect panel
        self.effect_panel = EffectPanel()
        self.effect_panel.effect_sent.connect(self.on_send_effect)
        tabs.addTab(self.effect_panel, "Effects")

        # Effect history
        self.effect_history = QListWidget()
        self.effect_history.setMinimumHeight(120)
        layout.addWidget(self.effect_history)

        layout.addWidget(tabs)

        # Status bar
        self.status_widget = StatusBarWidget()
        layout.addWidget(self.status_widget)

        central_widget.setLayout(layout)

    def setup_callbacks(self):
        """Set up controller callbacks."""
        self.controller.set_callbacks(
            on_connected=self.on_connected,
            on_disconnected=self.on_disconnected,
            on_device_list_updated=self.on_device_list_updated,
            on_effect_sent=self.on_effect_sent,
            on_error=self.on_error,
        )

    @asyncSlot(str, str, int, dict)
    async def on_connect(
        self, protocol: str, host: str, port: int, kwargs: dict
    ):
        """Handle connection request."""
        try:
            config = ConnectionConfig(
                protocol=protocol, host=host, port=port, extra_options=kwargs
            )
            await self.controller.connect(config)
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.on_error(str(e))

    @asyncSlot()
    async def on_disconnect(self):
        """Handle disconnection request."""
        try:
            await self.controller.disconnect()
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            self.on_error(str(e))

    @asyncSlot(str, int)
    async def on_start_mqtt_broker(self, host: str, ws_port: int):
        """Handle request to start backend MQTT broker via WebSocket control plane."""
        self.connection_panel.set_mqtt_status(
            "Starting MQTT broker...", "orange"
        )
        ok = await self.controller.start_mqtt_broker(host, ws_port)
        if ok:
            self.connection_panel.set_mqtt_status(
                "MQTT broker running", "green"
            )
            self.status_widget.update_info("MQTT broker started")
        else:
            self.connection_panel.set_mqtt_status("MQTT broker failed", "red")

    @asyncSlot(dict)
    async def on_send_effect(self, effect_data: dict):
        """Handle effect send request."""
        try:
            await self.controller.send_effect(effect_data)
        except Exception as e:
            logger.error(f"Effect send failed: {e}")
            self.on_error(str(e))

    @asyncSlot()
    async def on_scan_devices(self):
        """Handle device scan request."""
        try:
            await self.controller.scan_devices()
        except Exception as e:
            logger.error(f"Device scan failed: {e}")
            self.on_error(str(e))

    def on_device_selected(self, device_id: str):
        """Handle device selection."""
        device = self.controller.devices.get(device_id)
        if device:
            self.effect_panel.set_target_device(device)
            self.status_widget.update_info(
                f"Selected: {device.get('name', device_id)}"
            )

    # Callbacks from controller
    def on_connected(self):
        """Connection established."""
        self.connection_panel.set_connected(True)
        self.status_widget.set_status("Connected", "green")
        logger.info("Connected to backend")

    def on_disconnected(self):
        """Connection lost."""
        self.connection_panel.set_connected(False)
        self.status_widget.set_status("Disconnected", "red")
        self.device_panel.clear_devices()
        logger.info("Disconnected from backend")

    def on_device_list_updated(self, devices: list):
        """Device list updated."""
        self.device_panel.update_devices(devices)
        count = len(devices)
        self.status_widget.update_info(f"{count} device(s) connected")

    def on_effect_sent(self, effect_data: dict):
        """Effect sent successfully."""
        effect_type = effect_data.get("effect_type", "unknown")
        self.status_widget.update_info(f"Sent: {effect_type}")
        logger.info(f"Effect sent: {effect_type}")
        summary = f"{effect_type} -> {effect_data.get('device_id', 'unknown')}"
        self.effect_history.addItem(summary)

    def on_error(self, error_msg: str):
        """Error occurred."""
        self.status_widget.set_status("Error", "orange")
        logger.error(f"Application error: {error_msg}")
        QMessageBox.warning(self, "Error", error_msg)

    @asyncSlot(str, int)
    async def on_start_mqtt_broker(self, host: str, ws_port: int):
        """Handle request to start backend MQTT broker via WebSocket control plane."""
        self.connection_panel.set_mqtt_status(
            "Starting MQTT broker...", "orange"
        )
        ok = await self.controller.start_mqtt_broker(host, ws_port)
        if ok:
            self.connection_panel.set_mqtt_status(
                "MQTT broker running", "green"
            )
            self.status_widget.update_info("MQTT broker started")
        else:
            self.connection_panel.set_mqtt_status("MQTT broker failed", "red")

    @asyncSlot(str, str, str)
    async def on_protocol_server_requested(
        self, action: str, protocol: str, host: str
    ):
        """Handle start/stop protocol server request."""
        if action == "start":
            self.connection_panel.set_protocol_status(protocol, False)
            ok = await self.controller.start_protocol_server(
                protocol, host, 8090
            )
            if ok:
                self.connection_panel.set_protocol_status(protocol, True)
                self.status_widget.update_info(
                    f"{protocol.upper()} server started"
                )
            else:
                self.connection_panel.set_protocol_status(protocol, False)
        elif action == "stop":
            ok = await self.controller.stop_protocol_server(
                protocol, host, 8090
            )
            if ok:
                self.connection_panel.set_protocol_status(protocol, False)
                self.status_widget.update_info(
                    f"{protocol.upper()} server stopped"
                )
            else:
                self.connection_panel.set_protocol_status(protocol, True)

    def closeEvent(self, event):
        """Handle window close event."""
        if self.controller.protocol and self.controller.protocol.is_connected:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Connection is active. Disconnect before exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Disconnect asynchronously without blocking
                try:
                    asyncio.create_task(self.controller.disconnect())
                except Exception as e:
                    logger.warning(f"Error scheduling disconnect: {e}")

        event.accept()
