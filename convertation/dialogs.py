from PySide6.QtWidgets import QMessageBox


def show_info(parent, title, text):
    QMessageBox.information(parent, title, text)


def show_error(parent, title, text):
    QMessageBox.critical(parent, title, text)


def show_warning(parent, title, text):
    QMessageBox.warning(parent, title, text)