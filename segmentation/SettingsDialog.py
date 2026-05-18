from PySide6.QtWidgets import *
from PySide6.QtGui import QIntValidator, QDoubleValidator


class SettingsDialog(QDialog):
    def __init__(self, parent=None, error_value=1e-9, iteration_value=100):
        super().__init__(parent)
        self.setWindowTitle("Настройки сегментации")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Настройка итераций
        iter_layout = QVBoxLayout()
        iter_label = QLabel("Количество итераций:")
        iter_label.setStyleSheet("font-weight: bold; margin-top: 10px;")

        self.iter_input = QLineEdit()
        self.iter_input.setText(str(iteration_value))

        # Валидатор для итераций: положительные целые числа от 1 до max_int-1
        iter_validator = QIntValidator(1, 2147483646)
        self.iter_input.setValidator(iter_validator)

        iter_info = QLabel("Диапазон: от 1 до 2 147 483 646")
        iter_info.setStyleSheet("color: #808080; font-size: 10px;")

        iter_layout.addWidget(iter_label)
        iter_layout.addWidget(self.iter_input)
        iter_layout.addWidget(iter_info)
        layout.addLayout(iter_layout)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Настройка ошибки
        error_layout = QVBoxLayout()
        error_label = QLabel("Цена ошибки:")
        error_label.setStyleSheet("font-weight: bold; margin-top: 10px;")

        self.error_input = QLineEdit()

        # Форматирование для научной нотации
        if error_value < 0.001:
            self.error_input.setText(f"{error_value:.0e}")
        else:
            self.error_input.setText(str(error_value))

        # Валидатор для ошибки: положительные числа от 0.1 до 1e-2147483646
        error_validator = QDoubleValidator()
        error_validator.setBottom(0.1)
        error_validator.setTop(1e-2147483646)
        error_validator.setNotation(QDoubleValidator.ScientificNotation)
        self.error_input.setValidator(error_validator)

        error_info = QLabel("Диапазон: от 0.1 до 1e-2 147 483 646")
        error_info.setStyleSheet("color: #808080; font-size: 10px;")

        error_layout.addWidget(error_label)
        error_layout.addWidget(self.error_input)
        error_layout.addWidget(error_info)
        layout.addLayout(error_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Отмена")

        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Стилизация
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLineEdit {
                background-color: #3D3D3D;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                color: #00ff41;
                font-family: monospace;
            }
            QLineEdit:focus {
                border: 1px solid #00ff41;
            }
            QPushButton {
                background-color: #3D3D3D;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px 15px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #4D4D4D;
                border: 1px solid #00ff41;
            }
            QPushButton:pressed {
                background-color: #00ff41;
                color: #000000;
            }
        """)

    def validate_and_accept(self):
        """Проверка валидности введенных данных"""
        # Проверка итераций
        iter_text = self.iter_input.text()
        if not iter_text:
            QMessageBox.warning(self, "Ошибка", "Введите количество итераций")
            return

        try:
            iterations = int(iter_text)
            if iterations < 1 or iterations > 2147483646:
                QMessageBox.warning(self, "Ошибка",
                                    "Количество итераций должно быть от 1 до 2 147 483 646")
                return
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение итераций")
            return

        # Проверка ошибки
        error_text = self.error_input.text()
        if not error_text:
            QMessageBox.warning(self, "Ошибка", "Введите значение ошибки")
            return

        try:
            # Поддержка научной нотации
            error_value = float(error_text)
            if error_value > 0.1:
                QMessageBox.warning(self, "Ошибка",
                                    "Цена ошибки должна быть <= 0.1")
                return
            if error_value < 1e-2147483646:
                QMessageBox.warning(self, "Ошибка",
                                    "Цена ошибки слишком мала (должна быть <= 1e-2147483646)")
                return
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение ошибки")
            return

        self.accept()

    def get_settings(self):
        """Возвращает настройки из диалога"""
        try:
            iterations = int(self.iter_input.text())
        except:
            iterations = 100

        try:
            error_value = float(self.error_input.text())
        except:
            error_value = 1e-9

        return {
            'error_value': error_value,
            'iterations': iterations
        }