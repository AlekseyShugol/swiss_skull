DIALOGUE_STYLE = '''
 QMessageBox {
            background: #161B22;
            color: #FFF;
        }
        QLabel {
            color: #CCC;
            font-size: 13px;
        }
'''

APP_STYLE = """
QMainWindow {
    background: #0D1117;
}

QGroupBox {
    color: #00E5FF;
    font-weight: bold;
    font-size: 13px;
    border: 2px solid #333;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background: #161B22;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #00E5FF;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2D3A4A, stop:1 #1A2332);
    color: #FFF;
    border: 1px solid #444;
    padding: 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D5A7A, stop:1 #2D3A4A);
    border: 1px solid #00E5FF;
}

QPushButton:pressed {
    background: #00E5FF;
    color: #000;
}

QPushButton:disabled {
    background: #222;
    color: #666;
    border: 1px solid #333;
}

QCheckBox {
    color: #CCC;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #555;
    border-radius: 3px;
    background: #222;
}

QCheckBox::indicator:checked {
    background: #00E5FF;
    border-color: #00E5FF;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #333;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background: #00E5FF;
    border-radius: 8px;
}

QSlider::sub-page:horizontal {
    background: #00E5FF;
    border-radius: 3px;
}

QLabel {
    color: #AAA;
    font-size: 12px;
}

QTextEdit {
    background: #0D1117;
    color: #CCC;
    border: 1px solid #333;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

#leftPanel {
    background: #0D1117;
    border-right: 2px solid #222;
}
"""