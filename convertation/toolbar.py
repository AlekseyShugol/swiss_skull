from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *


class MainToolBar(QToolBar):

    def __init__(self, parent):
        super().__init__("Toolbar", parent)

        self.setMovable(False)
        self.setIconSize(QSize(20, 20))

        self.parent_window = parent

        self.build_toolbar()

    def build_toolbar(self):

        # OPEN
        act_open = QAction("Open", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(
            self.parent_window.select_folder
        )

        # BUILD
        act_build = QAction("Build", self)
        act_build.setShortcut("Ctrl+R")
        act_build.triggered.connect(
            self.parent_window.generate_3d
        )

        # CLEAR
        act_clear = QAction("Clear", self)
        act_clear.setShortcut("Ctrl+L")
        act_clear.triggered.connect(
            self.parent_window.clear_scene
        )

        # UNDO
        act_undo = QAction("Undo", self)
        act_undo.setShortcut("Ctrl+Z")

        # REDO
        act_redo = QAction("Redo", self)
        act_redo.setShortcut("Ctrl+Y")

        # EXPORT
        act_export = QAction("Export", self)
        act_export.setShortcut("Ctrl+S")
        act_export.triggered.connect(
            self.parent_window.export_model
        )

        # HELP
        act_help = QAction("Help", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(
            self.parent_window.show_shortcuts_help
        )

        self.addAction(act_open)
        self.addSeparator()

        self.addAction(act_build)
        self.addAction(act_clear)

        self.addSeparator()

        self.addAction(act_undo)
        self.addAction(act_redo)

        self.addSeparator()

        self.addAction(act_export)

        self.addSeparator()

        self.addAction(act_help)