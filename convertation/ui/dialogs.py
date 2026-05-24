# ==================== ДИАЛОГИ ====================
from PySide6.QtWidgets import QMessageBox

from convertation.ui.styles import DIALOGUE_STYLE


def show_info(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(DIALOGUE_STYLE)
    msg.exec()


def show_warning(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(DIALOGUE_STYLE)
    msg.exec()


def show_error(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(DIALOGUE_STYLE)
    msg.exec()