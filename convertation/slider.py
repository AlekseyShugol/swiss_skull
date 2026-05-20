from PySide6.QtWidgets import *
from PySide6.QtCore import *


class LabeledSlider(QWidget):

    valueChanged = Signal(int)

    def __init__(
            self,
            title,
            min_value,
            max_value,
            value,
            suffix="",
            step=1,
            parent=None
    ):
        super().__init__(parent)

        self.suffix = suffix

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        top = QHBoxLayout()

        self.label = QLabel(title)

        self.value_label = QLabel()

        top.addWidget(self.label)
        top.addStretch()
        top.addWidget(self.value_label)

        layout.addLayout(top)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_value, max_value)
        self.slider.setValue(value)
        self.slider.setSingleStep(step)
        self.slider.setPageStep(step * 10)

        layout.addWidget(self.slider)

        self.spin = QSpinBox()
        self.spin.setRange(min_value, max_value)
        self.spin.setValue(value)
        self.spin.setSingleStep(step)

        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

        self.slider.valueChanged.connect(self.update_value)
        self.slider.valueChanged.connect(self.valueChanged.emit)

        self.update_value(value)

    def update_value(self, value):
        self.value_label.setText(f"{value}{self.suffix}")

    def value(self):
        return self.slider.value()