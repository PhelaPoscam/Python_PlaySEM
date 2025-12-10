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
    QStackedWidget,
    QCheckBox,
)
from PyQt6.QtCore import pyqtSignal

from ..protocols import ProtocolFactory

logger = logging.getLogger(__name__)


class ConnectionPanel(QWidget):
    """Panel for connection configuration and management."""

    connect_requested = pyqtSignal(
        str, str, int, dict
    )  # protocol, host, port, kwargs
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
        self.protocol_combo.currentTextChanged.connect(
            self._on_protocol_changed
        )
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

        # Stacked widget for protocol-specific settings
        self.protocol_stack = QStackedWidget()
        self._setup_websocket_settings()
        self._setup_http_settings()
        self._setup_mqtt_settings()
        group_layout.addWidget(self.protocol_stack)

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

        # Get protocol-specific kwargs
        kwargs = {}
        if protocol == "mqtt":
            kwargs = {
                "client_id": self.mqtt_client_id.text(),
                "username": (
                    self.mqtt_username.text()
                    if self.mqtt_auth_checkbox.isChecked()
                    else None
                ),
                "password": (
                    self.mqtt_password.text()
                    if self.mqtt_auth_checkbox.isChecked()
                    else None
                ),
            }
            # MQTT default port
            if port == 8090:  # WebSocket default
                port = 1883

        self.connect_requested.emit(protocol, host, port, kwargs)

    def on_disconnect_clicked(self):
        """Handle disconnect button click."""
        self.disconnect_requested.emit()

    def _on_protocol_changed(self, protocol_name: str):
        """Switch protocol-specific panel when protocol changes."""
        if protocol_name == "websocket":
            self.protocol_stack.setCurrentIndex(0)
            self.port_spinbox.setValue(8090)
        elif protocol_name == "http":
            self.protocol_stack.setCurrentIndex(1)
            self.port_spinbox.setValue(8090)
        elif protocol_name == "mqtt":
            self.protocol_stack.setCurrentIndex(2)
            self.port_spinbox.setValue(1883)

    def _setup_websocket_settings(self):
        """Setup WebSocket-specific settings panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("No additional settings for WebSocket"))
        layout.addStretch()
        panel.setLayout(layout)
        self.protocol_stack.addWidget(panel)

    def _setup_http_settings(self):
        """Setup HTTP-specific settings panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("No additional settings for HTTP"))
        layout.addStretch()
        panel.setLayout(layout)
        self.protocol_stack.addWidget(panel)

    def _setup_mqtt_settings(self):
        """Setup MQTT-specific settings panel."""
        panel = QWidget()
        layout = QVBoxLayout()

        # Client ID
        client_id_layout = QHBoxLayout()
        client_id_layout.addWidget(QLabel("Client ID:"))
        self.mqtt_client_id = QLineEdit("pythonplaysem_gui")
        self.mqtt_client_id.setPlaceholderText("Unique MQTT client ID")
        client_id_layout.addWidget(self.mqtt_client_id)
        layout.addLayout(client_id_layout)

        # Authentication checkbox
        self.mqtt_auth_checkbox = QCheckBox("Enable Authentication")
        self.mqtt_auth_checkbox.stateChanged.connect(
            self._on_mqtt_auth_toggled
        )
        layout.addWidget(self.mqtt_auth_checkbox)

        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.mqtt_username = QLineEdit()
        self.mqtt_username.setPlaceholderText("Optional MQTT username")
        self.mqtt_username.setVisible(False)
        username_layout.addWidget(self.mqtt_username)
        layout.addLayout(username_layout)

        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.mqtt_password = QLineEdit()
        self.mqtt_password.setPlaceholderText("Optional MQTT password")
        self.mqtt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mqtt_password.setVisible(False)
        password_layout.addWidget(self.mqtt_password)
        layout.addLayout(password_layout)

        layout.addStretch()
        panel.setLayout(layout)
        self.protocol_stack.addWidget(panel)

    def _on_mqtt_auth_toggled(self, state):
        """Toggle MQTT authentication fields visibility."""
        is_checked = self.mqtt_auth_checkbox.isChecked()
        self.mqtt_username.setVisible(is_checked)
        self.mqtt_password.setVisible(is_checked)

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
