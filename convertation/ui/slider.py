from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class LabeledSlider(QWidget):
    """Слайдер с меткой и полем ввода."""

    value_changed = Signal(int)

    def __init__(self, label, min_val, max_val, default_val, suffix="", step=1):
        super().__init__()

        self.suffix = suffix

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(f"{label}: {default_val}{suffix}")
        self.title_label.setStyleSheet("color: #AAA; font-size: 11px;")
        layout.addWidget(self.title_label)

        h_layout = QHBoxLayout()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet("""
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
        """)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setSuffix(suffix)
        self.spinbox.setFixedWidth(100)
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background: #222;
                color: #FFF;
                border: 1px solid #444;
                padding: 4px;
                border-radius: 3px;
            }
        """)

        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.spinbox)
        layout.addLayout(h_layout)

        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)

    def _on_slider_changed(self, value):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)
        self.title_label.setText(f"{self.title_label.text().split(':')[0]}: {value}{self.suffix}")
        self.value_changed.emit(value)

    def _on_spinbox_changed(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.title_label.setText(f"{self.title_label.text().split(':')[0]}: {value}{self.suffix}")
        self.value_changed.emit(value)

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)