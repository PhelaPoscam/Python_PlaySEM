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
    mqtt_broker_requested = pyqtSignal(str, int)  # host, ws_port
    protocol_server_requested = pyqtSignal(
        str, str, str
    )  # action (start/stop), protocol, host

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

        # MQTT broker control (uses WebSocket control plane)
        broker_layout = QHBoxLayout()
        self.mqtt_broker_button = QPushButton(
            "Start MQTT broker (via WS 8090)"
        )
        self.mqtt_broker_button.clicked.connect(self.on_start_mqtt_broker)
        broker_layout.addWidget(self.mqtt_broker_button)
        self.mqtt_status_label = QLabel("MQTT broker: unknown")
        broker_layout.addWidget(self.mqtt_status_label)
        group_layout.addLayout(broker_layout)

        # Protocol servers control panel
        servers_layout = QVBoxLayout()
        servers_label = QLabel("Protocol Servers:")
        servers_label.setStyleSheet("font-weight: bold;")
        servers_layout.addWidget(servers_label)

        # CoAP, UPnP, HTTP server buttons
        for protocol_name in ["coap", "upnp", "http"]:
            proto_layout = QHBoxLayout()
            start_btn = QPushButton(f"Start {protocol_name.upper()}")
            stop_btn = QPushButton(f"Stop {protocol_name.upper()}")
            status_label = QLabel(f"{protocol_name.upper()}: off")
            status_label.setStyleSheet("color: red;")

            start_btn.clicked.connect(
                lambda checked, p=protocol_name: self.on_start_protocol_server(
                    p
                )
            )
            stop_btn.clicked.connect(
                lambda checked, p=protocol_name: self.on_stop_protocol_server(
                    p
                )
            )

            proto_layout.addWidget(start_btn)
            proto_layout.addWidget(stop_btn)
            proto_layout.addWidget(status_label)

            servers_layout.addLayout(proto_layout)

            # Store references for status updates
            setattr(self, f"{protocol_name}_start_btn", start_btn)
            setattr(self, f"{protocol_name}_stop_btn", stop_btn)
            setattr(self, f"{protocol_name}_status_label", status_label)

        group_layout.addLayout(servers_layout)

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

    def on_start_mqtt_broker(self):
        """Trigger backend MQTT broker start via WebSocket control."""
        host = self.host_input.text().strip() or "127.0.0.1"
        self.mqtt_broker_requested.emit(host, 8090)

    def on_start_protocol_server(self, protocol: str):
        """Trigger backend protocol server start."""
        host = self.host_input.text().strip() or "127.0.0.1"
        self.protocol_server_requested.emit("start", protocol, host)

    def on_stop_protocol_server(self, protocol: str):
        """Trigger backend protocol server stop."""
        host = self.host_input.text().strip() or "127.0.0.1"
        self.protocol_server_requested.emit("stop", protocol, host)

    def set_mqtt_status(self, text: str, color: str = "gray"):
        """Update MQTT broker status label."""
        self.mqtt_status_label.setText(text)
        color_map = {
            "green": "#4CAF50",
            "red": "#F44336",
            "orange": "#FF9800",
            "gray": "#999999",
        }
        self.mqtt_status_label.setStyleSheet(
            f"color: {color_map.get(color, color)};"
        )

    def set_protocol_status(self, protocol: str, running: bool):
        """Update protocol server status label."""
        status_label = getattr(self, f"{protocol}_status_label", None)
        if status_label:
            color = "green" if running else "red"
            text = f"{protocol.upper()}: {'on' if running else 'off'}"
            status_label.setText(text)
            color_map = {"green": "#4CAF50", "red": "#F44336"}
            status_label.setStyleSheet(
                f"color: {color_map.get(color, 'red')};"
            )

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
