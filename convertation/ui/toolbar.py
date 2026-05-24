from PySide6.QtWidgets import *
from PySide6.QtGui import *

class MainToolBar(QToolBar):
    """Главная панель инструментов."""

    def __init__(self, parent):
        super().__init__("Main Toolbar", parent)
        self.setMovable(False)
        self.setStyleSheet("""
            QToolBar {
                background: #1A1A1A;
                border-bottom: 2px solid #333;
                padding: 4px;
                spacing: 8px;
            }
        """)

        self.add_action("📁", "Open DICOM (Ctrl+O)", parent.select_folder)
        self.add_action("🔄", "Rebuild Selected (Ctrl+R)", parent.generate_selected_models)
        self.add_action("💾", "Export Selected (Ctrl+S)", parent.export_selected_models)
        self.addSeparator()
        self.add_action("🗑", "Clear Scene (Ctrl+L)", parent.clear_scene)
        self.addSeparator()
        self.add_action("📋", "View Metadata (Ctrl+M)", parent.show_metadata)
        self.addSeparator()
        self.add_action("❓", "Help (F1)", parent.show_shortcuts_help)

    def add_action(self, icon, tooltip, callback):
        action = QAction(icon, self)
        action.setToolTip(tooltip)
        action.triggered.connect(callback)
        self.addAction(action)