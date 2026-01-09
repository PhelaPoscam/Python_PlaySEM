"""
Device panel widget for managing connected devices.
"""

import logging
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)


class DevicePanel(QWidget):
    """Panel for managing connected devices."""

    device_selected = pyqtSignal(str)  # device_id
    scan_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout()

        # Devices group
        group = QGroupBox("Connected Devices")
        group_layout = QVBoxLayout()

        # Device list
        self.device_list = QListWidget()
        self.device_list.itemSelectionChanged.connect(
            self.on_selection_changed
        )
        group_layout.addWidget(self.device_list)

        # Buttons
        button_layout = QHBoxLayout()

        self.scan_button = QPushButton("Scan Devices")
        self.scan_button.clicked.connect(self.scan_requested.emit)
        button_layout.addWidget(self.scan_button)

        button_layout.addStretch()

        group_layout.addLayout(button_layout)
        group.setLayout(group_layout)
        layout.addWidget(group)

        # Info label
        self.info_label = QLabel("No devices connected")
        layout.addWidget(self.info_label)

        layout.addStretch()
        self.setLayout(layout)

    def update_devices(self, devices: List[Dict[str, Any]]):
        """Update the device list display."""
        self.devices = {d["id"]: d for d in devices}
        self.device_list.clear()

        for device in devices:
            device_id = device.get("id", "unknown")
            device_name = device.get("name", "Unknown Device")
            device_type = device.get("type", "").capitalize()
            protocols = ", ".join(device.get("protocols", [])) or "unknown"
            capabilities = (
                ", ".join(device.get("capabilities", [])) or "unknown"
            )

            text = f"{device_name} ({device_type}) | {protocols}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, device_id)
            item.setToolTip(
                f"ID: {device_id}\nProtocols: {protocols}\nCapabilities: {capabilities}"
            )
            self.device_list.addItem(item)

        # Update info
        count = len(devices)
        self.info_label.setText(f"{count} device(s) available")

    def clear_devices(self):
        """Clear the device list."""
        self.devices.clear()
        self.device_list.clear()
        self.info_label.setText("No devices connected")

    def on_selection_changed(self):
        """Handle device selection change."""
        current_item = self.device_list.currentItem()
        if current_item:
            device_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.device_selected.emit(device_id)
