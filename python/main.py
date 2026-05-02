# Точка входа в программу.

import sys

from PySide6.QtWidgets import QApplication
from segmentation.MainWindow import MainWindow


def main():
    """Entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
