from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QVBoxLayout, QPushButton, QCheckBox, QSlider, QSplitter
from pyvistaqt import QtInteractor

from convertation.ui.slider import LabeledSlider
from logger.logger import log

import pyqtgraph as pg


class MainWindowPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        log.action("MainWindowPanel", "Initializing UI panel")

        central = self
        root = QHBoxLayout(central)

        # LEFT PANEL
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(360)

        left_layout = QVBoxLayout(left_panel)

        # FILE GROUP
        file_group = self.make_group("DATA")
        self.btn_load = QPushButton("📁 Open DICOM Folder")
        self.btn_load.clicked.connect(self.select_folder)
        file_group.layout().addWidget(self.btn_load)
        left_layout.addWidget(file_group)

        # BUILD SELECTION
        build_group = self.make_group("BUILD SELECTION")

        self.check_brain = QCheckBox("🧠 Brain (brain.obj)")
        self.check_tumor = QCheckBox("🔴 Tumor (tumor.obj)")
        self.check_skull = QCheckBox("💀 Skull (skull.obj)")
        self.check_arteria = QCheckBox("🩸 Arteria (arteria.obj)")

        self.check_brain.setChecked(True)
        self.check_tumor.setChecked(False)
        self.check_skull.setChecked(False)
        self.check_arteria.setChecked(False)

        build_group.layout().addWidget(self.check_brain)
        build_group.layout().addWidget(self.check_tumor)
        build_group.layout().addWidget(self.check_skull)
        build_group.layout().addWidget(self.check_arteria)

        left_layout.addWidget(build_group)

        # PROCESSING
        processing_group = self.make_group("PROCESSING")

        self.thresh_slider = LabeledSlider("HU Threshold", -500, 7500, 0, " HU", 1)
        self.island_slider = LabeledSlider("Min Object Size", 100, 50000, 10000, "", 100)
        self.sigma_slider = LabeledSlider("Gaussian Sigma", 0, 30, 0, "", 1)
        self.smooth_iter_slider = LabeledSlider("Smooth Iterations", 0, 200, 50, "", 1)

        # Подключаем сигналы слайдеров
        self.thresh_slider.value_changed.connect(self.on_threshold_changed)
        self.island_slider.value_changed.connect(self.on_island_size_changed)
        self.sigma_slider.value_changed.connect(self.on_sigma_changed)
        self.smooth_iter_slider.value_changed.connect(self.on_smooth_iter_changed)

        processing_group.layout().addWidget(self.thresh_slider)
        processing_group.layout().addWidget(self.island_slider)
        processing_group.layout().addWidget(self.sigma_slider)
        processing_group.layout().addWidget(self.smooth_iter_slider)

        left_layout.addWidget(processing_group)

        # OPTIONS
        options_group = self.make_group("OPTIONS")
        self.check_largest = QCheckBox("Keep only largest object")
        self.check_largest.setChecked(True)
        options_group.layout().addWidget(self.check_largest)
        left_layout.addWidget(options_group)

        # ACTIONS
        action_group = self.make_group("ACTIONS")

        self.btn_mesh = QPushButton("⚡ Build Selected Models")
        self.btn_mesh.clicked.connect(self.on_build_clicked)

        self.btn_export = QPushButton("💾 Export Selected Models")
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_export.setEnabled(False)

        self.btn_metadata = QPushButton("📋 View Metadata")
        self.btn_metadata.clicked.connect(self.on_metadata_clicked)

        action_group.layout().addWidget(self.btn_mesh)
        action_group.layout().addWidget(self.btn_export)
        action_group.layout().addWidget(self.btn_metadata)

        left_layout.addWidget(action_group)
        left_layout.addStretch()

        root.addWidget(left_panel)

        # SPLITTER
        splitter = QSplitter(Qt.Horizontal)

        # 2D PREVIEW
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        self.win = pg.GraphicsLayoutWidget()
        self.win.setBackground("#111111")

        self.view = self.win.addViewBox()
        self.view.setAspectLocked(True)

        self.img_item = pg.ImageItem()
        self.view.addItem(self.img_item)

        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.35)
        self.view.addItem(self.mask_item)

        self.roi = pg.RectROI(
            [50, 50], [150, 150],
            movable=True, resizable=True, removable=False,
            pen=pg.mkPen("#00E5FF", width=2)
        )
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.view.addItem(self.roi)

        preview_layout.addWidget(self.win)

        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.on_slice_changed)
        preview_layout.addWidget(self.slice_slider)

        splitter.addWidget(preview_widget)

        # 3D VIEW
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#111111")
        splitter.addWidget(self.plotter.interactor)
        splitter.setSizes([700, 1200])

        root.addWidget(splitter)

        log.info("MainWindowPanel initialized successfully")

    def make_group(self, title):
        """Вспомогательный метод для создания группы"""
        group = QFrame()
        group.setFrameStyle(QFrame.Box)
        layout = QVBoxLayout(group)
        label = QtWidgets.QLabel(title)
        label.setStyleSheet("font-weight: bold; color: #00E5FF;")
        layout.addWidget(label)
        return group

    # Обработчики сигналов
    def on_threshold_changed(self, value):
        log.debug(f"Threshold changed to {value}")
        if hasattr(self.parent(), 'update_plots'):
            self.parent().update_plots()

    def on_island_size_changed(self, value):
        log.debug(f"Island size changed to {value}")

    def on_sigma_changed(self, value):
        log.debug(f"Sigma changed to {value / 10.0}")

    def on_smooth_iter_changed(self, value):
        log.debug(f"Smooth iterations changed to {value}")

    def on_slice_changed(self, value):
        log.debug(f"Slice changed to {value}")
        if hasattr(self.parent(), 'update_plots'):
            self.parent().update_plots()

    def on_build_clicked(self):
        log.action("Build models button clicked")
        if hasattr(self.parent(), 'generate_selected_models'):
            self.parent().generate_selected_models()

    def on_export_clicked(self):
        log.action("Export models button clicked")
        if hasattr(self.parent(), 'export_selected_models'):
            self.parent().export_selected_models()

    def on_metadata_clicked(self):
        log.action("Metadata button clicked")
        if hasattr(self.parent(), 'show_metadata'):
            self.parent().show_metadata()

    def select_folder(self):
        log.action("Select folder called")
        if hasattr(self.parent(), 'select_folder'):
            self.parent().select_folder()