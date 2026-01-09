"""
Status bar widget for displaying application status.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatusBarWidget(QWidget):
    """Widget for displaying status information."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: red; font-size: 14px;")
        layout.addWidget(self.status_indicator)

        # Status text
        self.status_text = QLabel("Disconnected")
        layout.addWidget(self.status_text)

        # Spacer
        layout.addStretch()

        # Info label
        self.info_label = QLabel("Ready")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def set_status(self, status: str, color: str = "gray"):
        """Update status text and color."""
        self.status_text.setText(status)

        color_map = {
            "green": "#4CAF50",
            "red": "#F44336",
            "orange": "#FF9800",
            "gray": "#999999",
        }

        hex_color = color_map.get(color, color)
        self.status_indicator.setStyleSheet(
            f"color: {hex_color}; font-size: 14px;"
        )

    def update_info(self, info: str):
        """Update info text."""
        self.info_label.setText(info)
