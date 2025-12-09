"""
Connection panel widget for managing protocol connections.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from ..protocols import ProtocolFactory

logger = logging.getLogger(__name__)


class ConnectionPanel(QWidget):
    """Panel for connection configuration and management."""

    connect_requested = pyqtSignal(str, str, int)  # protocol, host, port
    disconnect_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout()

        # Connection group
        group = QGroupBox("Backend Connection")
        group_layout = QVBoxLayout()

        # Protocol selection
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocol:"))
        self.protocol_combo = QComboBox()
        protocols = ProtocolFactory.available_protocols()
        self.protocol_combo.addItems(protocols)
        self.protocol_combo.setCurrentText("websocket")
        protocol_layout.addWidget(self.protocol_combo)
        group_layout.addLayout(protocol_layout)

        # Host
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit("127.0.0.1")
        host_layout.addWidget(self.host_input)
        group_layout.addLayout(host_layout)

        # Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setMinimum(1)
        self.port_spinbox.setMaximum(65535)
        self.port_spinbox.setValue(8090)
        port_layout.addWidget(self.port_spinbox)
        group_layout.addLayout(port_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

        # Connection buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        button_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.disconnect_button)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def on_connect_clicked(self):
        """Handle connect button click."""
        protocol = self.protocol_combo.currentText()
        host = self.host_input.text().strip()
        port = self.port_spinbox.value()

        if not host:
            QMessageBox.warning(self, "Input Error", "Please enter a host")
            return

        self.connect_requested.emit(protocol, host, port)

    def on_disconnect_clicked(self):
        """Handle disconnect button click."""
        self.disconnect_requested.emit()

    def set_connected(self, connected: bool):
        """Update connection status display."""
        self.is_connected = connected

        if connected:
            self.status_label.setText("Status: Connected ✓")
            self.status_label.setStyleSheet("color: green;")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.protocol_combo.setEnabled(False)
            self.host_input.setEnabled(False)
            self.port_spinbox.setEnabled(False)
        else:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red;")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.protocol_combo.setEnabled(True)
            self.host_input.setEnabled(True)
            self.port_spinbox.setEnabled(True)
