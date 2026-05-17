
import numpy as np
import pyqtgraph as pg
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import *
from PySide6.QtCore import *

from convertation.conversion import BrainCleanerLogic


# ==================== UI (ТОЛЬКО ИНТЕРФЕЙС) ====================
class BrainCleaner3D(QMainWindow):
    """Графический интерфейс (сохраняет оригинальное имя класса для обратной совместимости)."""

    def __init__(self, dicom_path=None, raw_img=None):
        super().__init__()

        self.processor = BrainCleanerLogic()  # Логика вынесена в отдельный класс

        self.setWindowTitle("Medical 3D: Brain Cleaner Pro - Smooth Edition")
        self.setMinimumSize(1400, 900)

        self.init_ui()

        # Загрузка данных, если переданы параметры
        if raw_img is not None:
            self._load_raw(raw_img)
        elif dicom_path is not None:
            self._load_dicom(dicom_path)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Левая панель
        controls = QVBoxLayout()

        self.btn_load = QPushButton("📁 Open DICOM Folder")
        self.btn_load.clicked.connect(self.select_folder)
        controls.addWidget(self.btn_load)

        controls.addSpacing(10)
        controls.addWidget(QLabel("<b>HU Threshold:</b>"))
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(-500, 7500)
        self.thresh_slider.setValue(40)
        self.thresh_slider.valueChanged.connect(self.update_plots)
        controls.addWidget(self.thresh_slider)
        self.lbl_thresh = QLabel("Value: 40 HU")
        controls.addWidget(self.lbl_thresh)

        controls.addSpacing(10)
        controls.addWidget(QLabel("<b>Min Object Size:</b>"))
        self.island_slider = QSlider(Qt.Horizontal)
        self.island_slider.setRange(100, 50000)
        self.island_slider.setValue(10000)
        self.island_slider.valueChanged.connect(self.update_plots)
        controls.addWidget(self.island_slider)
        self.lbl_island = QLabel("Size: 10000")
        controls.addWidget(self.lbl_island)

        self.check_largest = QCheckBox("Keep ONLY Largest (Brain)")
        self.check_largest.setChecked(True)
        controls.addWidget(self.check_largest)

        controls.addSpacing(10)
        controls.addWidget(QLabel("<b>Gaussian Smooth Sigma:</b>"))
        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(0, 30)
        self.sigma_slider.setValue(12)
        self.sigma_slider.valueChanged.connect(self.update_sigma_label)
        controls.addWidget(self.sigma_slider)
        self.lbl_sigma = QLabel("Sigma: 1.2")
        controls.addWidget(self.lbl_sigma)

        controls.addSpacing(10)
        controls.addWidget(QLabel("<b>Mesh Smooth Iterations:</b>"))
        self.smooth_iter_slider = QSlider(Qt.Horizontal)
        self.smooth_iter_slider.setRange(0, 200)
        self.smooth_iter_slider.setValue(50)
        self.smooth_iter_slider.valueChanged.connect(self.update_iter_label)
        controls.addWidget(self.smooth_iter_slider)
        self.lbl_iter = QLabel("Iterations: 50")
        controls.addWidget(self.lbl_iter)

        controls.addSpacing(10)
        self.check_center = QCheckBox("Center model at origin (recommended for 3D printing)")
        self.check_center.setChecked(True)
        controls.addWidget(self.check_center)

        controls.addSpacing(20)
        self.btn_mesh = QPushButton("⚡ REBUILD 3D MODEL")
        self.btn_mesh.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; height: 45px;")
        self.btn_mesh.clicked.connect(self.generate_3d)
        controls.addWidget(self.btn_mesh)

        self.btn_export = QPushButton("💾 EXPORT MODEL")
        self.btn_export.setStyleSheet("background-color: #28a745; color: white; height: 40px;")
        self.btn_export.clicked.connect(self.export_model)
        self.btn_export.setEnabled(False)
        controls.addWidget(self.btn_export)

        controls.addStretch()
        layout.addLayout(controls, 1)

        # 2D Preview
        v_layout_2d = QVBoxLayout()
        self.win = pg.GraphicsLayoutWidget()
        self.view = self.win.addViewBox()
        self.view.setAspectLocked(True)
        self.img_item = pg.ImageItem()
        self.view.addItem(self.img_item)
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.3)
        self.view.addItem(self.mask_item)

        self.roi = pg.RectROI([50, 50], [150, 150], pen=(0, 9))
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.view.addItem(self.roi)

        v_layout_2d.addWidget(self.win)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.update_plots)
        v_layout_2d.addWidget(self.slice_slider)
        layout.addLayout(v_layout_2d, 3)

        # 3D Window
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#1a1a1a")
        layout.addWidget(self.plotter.interactor, 4)

    def _load_raw(self, raw_img):
        try:
            shape = self.processor.load_from_raw_image(raw_img)
            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()
            self.setWindowTitle(f"Medical 3D: Brain Cleaner Pro [Loaded from memory]")
            self.btn_load.setText("📁 Load Another DICOM")
            QMessageBox.information(self, "Success", f"Data loaded from memory!\nVolume shape: {shape}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from raw_img: {e}")

    def _load_dicom(self, path):
        try:
            shape = self.processor.load_from_dicom(path)
            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()
            self.setWindowTitle(f"Medical 3D: Brain Cleaner Pro [{path}]")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load failed: {e}")

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if path:
            self._load_dicom(path)

    def update_plots(self):
        z = self.slice_slider.value()
        t = self.thresh_slider.value()
        self.lbl_thresh.setText(f"Value: {t} HU")
        self.lbl_island.setText(f"Size: {self.island_slider.value()}")

        img, mask = self.processor.get_slice(z, t)
        if img is None:
            return

        self.img_item.setImage(img)
        if mask is not None:
            self.mask_item.setImage(mask, lut=np.array([[0, 0, 0, 0], [0, 255, 0, 100]]))

    def update_sigma_label(self):
        sigma = self.sigma_slider.value() / 10.0
        self.lbl_sigma.setText(f"Sigma: {sigma:.1f}")

    def update_iter_label(self):
        self.lbl_iter.setText(f"Iterations: {self.smooth_iter_slider.value()}")

    def generate_3d(self):
        if self.processor.full_volume is None:
            return

        pos = self.roi.pos()
        size = self.roi.size()
        roi_pos = (pos.x(), pos.y())
        roi_size = (size.x(), size.y())

        try:
            mesh = self.processor.generate_mesh(
                roi_pos=roi_pos,
                roi_size=roi_size,
                threshold_value=self.thresh_slider.value(),
                min_island_size=self.island_slider.value(),
                keep_largest=self.check_largest.isChecked(),
                sigma_value=self.sigma_slider.value() / 10.0,
                smooth_iterations=self.smooth_iter_slider.value(),
                center_model=self.check_center.isChecked()
            )

            # Визуализация
            self.plotter.clear()
            self.plotter.add_mesh(
                mesh,
                color="#E6BE8A",
                lighting=True,
                smooth_shading=True,
                show_edges=False,
                specular=0.3,
                specular_power=25,
                diffuse=0.7,
                ambient=0.3
            )

            self.plotter.enable_eye_dome_lighting()
            light1 = pv.Light(position=(5, 5, 10), light_type='scene light')
            light1.intensity = 0.8
            self.plotter.add_light(light1)
            light2 = pv.Light(position=(-5, -5, 5), light_type='scene light')
            light2.intensity = 0.5
            self.plotter.add_light(light2)
            light3 = pv.Light(position=(0, 10, 0), light_type='scene light')
            light3.intensity = 0.3
            self.plotter.add_light(light3)

            self.plotter.reset_camera()
            self.btn_export.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "3D Error", str(e))

    def export_model(self):
        if self.processor.last_mesh is None:
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save 3D Model",
            "brain_model.obj",
            "OBJ Files (*.obj);;STL Files (*.stl);;PLY Files (*.ply)"
        )

        if path:
            try:
                self.processor.export_model(path)
                QMessageBox.information(self, "Success", f"Model exported successfully!\nSaved to: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")


