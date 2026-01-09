"""
Effect panel widget for sending sensory effects.
"""

import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QColorDialog,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class EffectPanel(QWidget):
    """Panel for sending sensory effects."""

    effect_sent = pyqtSignal(dict)  # effect_data

    def __init__(self):
        super().__init__()
        self.target_device: Optional[Dict[str, Any]] = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout()

        # Target device info
        self.target_label = QLabel("Target: Not selected")
        self.target_label.setStyleSheet("font-weight: bold; color: #666;")
        layout.addWidget(self.target_label)

        # Effect type
        effect_layout = QHBoxLayout()
        effect_layout.addWidget(QLabel("Effect Type:"))
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(
            ["light", "vibration", "wind", "scent", "heat", "cold"]
        )
        self.effect_combo.currentTextChanged.connect(
            self.on_effect_type_changed
        )
        effect_layout.addWidget(self.effect_combo)
        layout.addLayout(effect_layout)

        # Intensity
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(50)
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)
        intensity_layout.addWidget(self.intensity_slider)

        self.intensity_label = QLabel("50")
        self.intensity_label.setMinimumWidth(30)
        intensity_layout.addWidget(self.intensity_label)
        layout.addLayout(intensity_layout)

        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (ms):"))
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setMinimum(0)
        self.duration_spinbox.setMaximum(60000)
        self.duration_spinbox.setValue(1000)
        self.duration_spinbox.setSingleStep(100)
        duration_layout.addWidget(self.duration_spinbox)
        layout.addLayout(duration_layout)

        # Color picker (for light effects)
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton("Pick Color")
        self.color_button.clicked.connect(self.on_pick_color)
        self.color_display = QPushButton()
        self.color_display.setFixedWidth(100)
        self.set_color(QColor(255, 255, 255))
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_display)
        layout.addLayout(color_layout)

        # Custom parameters
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Custom Param:"))
        self.param_input = QDoubleSpinBox()
        self.param_input.setMinimum(0)
        self.param_input.setMaximum(1000)
        self.param_input.setValue(0)
        param_layout.addWidget(self.param_input)
        layout.addLayout(param_layout)

        layout.addSpacing(20)

        # Send button
        self.send_button = QPushButton("Send Effect")
        self.send_button.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "padding: 10px; "
            "font-weight: bold; "
            "border-radius: 5px; "
            "}"
        )
        self.send_button.clicked.connect(self.on_send_clicked)
        self.send_button.setEnabled(False)
        layout.addWidget(self.send_button)

        layout.addStretch()
        self.setLayout(layout)

        self.current_color = QColor(255, 255, 255)

    def on_effect_type_changed(self, effect_type: str):
        """Handle effect type change."""
        # Enable/disable color picker based on effect type
        self.color_button.setEnabled(effect_type == "light")

    def on_intensity_changed(self, value: int):
        """Handle intensity slider change."""
        self.intensity_label.setText(str(value))

    def on_pick_color(self):
        """Handle color picker button click."""
        color = QColorDialog.getColor(self.current_color, self, "Select Color")
        if color.isValid():
            self.set_color(color)

    def set_color(self, color: QColor):
        """Set the selected color."""
        self.current_color = color
        hex_color = color.name().upper()
        self.color_display.setStyleSheet(f"background-color: {hex_color};")
        self.color_display.setText(hex_color)

    def on_send_clicked(self):
        """Handle send effect button click."""
        if not self.target_device:
            QMessageBox.warning(
                self, "No Device", "Please select a device first"
            )
            return

        effect_data = {
            "effect_type": self.effect_combo.currentText(),
            "intensity": self.intensity_slider.value(),
            "duration": self.duration_spinbox.value(),
            "color": self.current_color.name(),
            "device_id": self.target_device.get("id"),
        }

        # Add custom parameter if set
        if self.param_input.value() > 0:
            effect_data["custom_param"] = self.param_input.value()

        self.effect_sent.emit(effect_data)

    def set_target_device(self, device: Dict[str, Any]):
        """Set the target device."""
        self.target_device = device
        device_name = device.get("name", "Unknown")
        device_type = device.get("type", "").capitalize()
        self.target_label.setText(f"Target: {device_name} ({device_type})")
        self.send_button.setEnabled(True)
