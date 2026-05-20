APP_STYLE = """
QMainWindow {
    background: #111111;
}

QWidget {
    background: #111111;
    color: white;
    font-size: 13px;
}

QFrame#leftPanel {
    background: #171717;
    border-right: 1px solid #2b2b2b;
}

QGroupBox {
    color: #4fc3f7;
    border: 1px solid #333;
    border-radius: 10px;
    margin-top: 10px;
    font-weight: bold;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

QPushButton {
    background: #1976d2;
    border: none;
    border-radius: 8px;
    padding: 10px;
    min-height: 38px;
    font-weight: bold;
}

QPushButton:hover {
    background: #2196f3;
}

QPushButton:pressed {
    background: #1565c0;
}

QPushButton:disabled {
    background: #444;
    color: #777;
}

QCheckBox {
    spacing: 8px;
}

QToolBar {
    background: #1b1b1b;
    border-bottom: 1px solid #333;
    spacing: 6px;
    padding: 6px;
}

QToolButton {
    background: transparent;
    border-radius: 6px;
    padding: 6px;
}

QToolButton:hover {
    background: #2b2b2b;
}

QSlider::groove:horizontal {
    border: none;
    height: 8px;
    background: #2a2a2a;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #4fc3f7;
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::sub-page:horizontal {
    background: #1976d2;
    border-radius: 4px;
}

QSpinBox {
    background: #2b2b2b;
    color: white;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 4px;
    min-height: 28px;
}

QMessageBox {
    background: #1b1b1b;
}

QMenuBar {
    background: #1b1b1b;
}

QMenu {
    background: #1b1b1b;
}
"""