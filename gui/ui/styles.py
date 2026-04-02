"""
Premium Dark Mode Styles (QSS) for PlaySEM GUI.
"""

DARK_THEME = """
/* Global Styles */
QWidget {
    background-color: #1A1C1E;
    color: #E2E2E6;
    font-family: 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
}

/* Group Boxes */
QGroupBox {
    border: 1px solid #44474E;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #A8C7FA;
}

/* Push Buttons */
QPushButton {
    background-color: #333538;
    border: 1px solid #44474E;
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #44474E;
    border-color: #A8C7FA;
}

QPushButton:pressed {
    background-color: #1A1C1E;
}

QPushButton:disabled {
    color: #5E5E62;
    background-color: #2A2C2F;
}

/* Primary Action Button */
QPushButton#primaryButton {
    background-color: #004A77;
    color: #D1E4FF;
    border: none;
    font-weight: bold;
}

QPushButton#primaryButton:hover {
    background-color: #00639B;
}

/* Stop/Danger Button */
QPushButton#dangerButton {
    background-color: #8C1D18;
    color: #F9DEDC;
    border: none;
}

QPushButton#dangerButton:hover {
    background-color: #B3261E;
}

/* Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2D2F33;
    border: 1px solid #44474E;
    border-radius: 4px;
    padding: 4px 8px;
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #A8C7FA;
}

/* List Widget */
QListWidget {
    background-color: #222427;
    border: 1px solid #44474E;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #333538;
}

QListWidget::item:selected {
    background-color: #004A77;
    color: #D1E4FF;
}

QListWidget::item:hover {
    background-color: #333538;
}

/* Console/Log View */
QTextEdit#consoleView {
    background-color: #000000;
    color: #00FF41; /* Classic Matrix/Terminal Green */
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #44474E;
    border-radius: 4px;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #44474E;
    height: 6px;
    background: #333538;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #A8C7FA;
    border: 1px solid #44474E;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

/* Status Bar */
QStatusBar {
    background-color: #2D2F33;
    border-top: 1px solid #44474E;
}
"""
