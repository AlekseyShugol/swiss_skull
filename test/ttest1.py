import sys
import numpy as np
import SimpleITK as sitk
import pyqtgraph as pg
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from skimage import measure, morphology


class RealTimeBrainSmoother(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Brain Sculptor: OBJ Edition")
        self.setMinimumSize(1500, 900)

        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)
        self.raw_mesh = None  # Исходная "угловатая" модель
        self.smooth_mesh = None  # Сглаженная модель

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # --- Панель управления ---
        controls = QVBoxLayout()

        self.btn_load = QPushButton("📁 Load DICOM Folder")
        self.btn_load.clicked.connect(self.select_folder)
        controls.addWidget(self.btn_load)

        controls.addSpacing(15)
        controls.addWidget(QLabel("<b>1. Segmentation Threshold (HU):</b>"))
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(-100, 7500)
        self.thresh_slider.setValue(40)
        self.thresh_slider.valueChanged.connect(self.update_plots)
        controls.addWidget(self.thresh_slider)
        self.lbl_thresh = QLabel("Value: 40 HU")
        controls.addWidget(self.lbl_thresh)

        controls.addSpacing(15)
        # РЕАЛТАЙМ СЛАЙДЕР СГЛАЖИВАНИЯ
        controls.addWidget(QLabel("<b>2. Real-Time Smoothing (Iterations):</b>"))
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(0, 100)
        self.smooth_slider.setValue(0)
        self.smooth_slider.setEnabled(False)
        self.smooth_slider.valueChanged.connect(self.apply_realtime_smooth)
        controls.addWidget(self.smooth_slider)
        self.lbl_smooth = QLabel("Smooth: 0 iterations")
        controls.addWidget(self.lbl_smooth)

        controls.addSpacing(20)
        self.btn_mesh = QPushButton("⚡ GENERATE BASE MESH")
        self.btn_mesh.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; height: 45px;")
        self.btn_mesh.clicked.connect(self.generate_base_mesh)
        controls.addWidget(self.btn_mesh)

        self.btn_export = QPushButton("💾 EXPORT OBJ")
        self.btn_export.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold; height: 45px;")
        self.btn_export.clicked.connect(self.export_obj)
        self.btn_export.setEnabled(False)
        controls.addWidget(self.btn_export)

        controls.addStretch()
        layout.addLayout(controls, 1)

        # --- 2D Preview ---
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
        self.view.addItem(self.roi)

        v_layout_2d.addWidget(self.win)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.update_plots)
        v_layout_2d.addWidget(self.slice_slider)
        layout.addLayout(v_layout_2d, 2)

        # --- 3D Viewport (PyVista) ---
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#111111")
        layout.addWidget(self.plotter.interactor, 4)

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path: self.load_data(path)

    def load_data(self, path):
        try:
            reader = sitk.ImageSeriesReader()
            names = reader.GetGDCMSeriesFileNames(path)
            reader.SetFileNames(names)
            image = reader.Execute()
            self.spacing = image.GetSpacing()
            self.full_volume = sitk.GetArrayFromImage(image)
            self.slice_slider.setRange(0, self.full_volume.shape[0] - 1)
            self.slice_slider.setValue(self.full_volume.shape[0] // 2)
            self.update_plots()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def update_plots(self):
        if self.full_volume is None: return
        z, t = self.slice_slider.value(), self.thresh_slider.value()
        self.lbl_thresh.setText(f"Value: {t} HU")
        img = np.rot90(self.full_volume[z], -1)
        self.img_item.setImage(img)
        mask = (img > t).astype(np.uint8) * 255
        self.mask_item.setImage(mask, lut=np.array([[0, 0, 0, 0], [0, 255, 150, 150]]))

    def generate_base_mesh(self):
        """Создает 'сырую' сетку один раз, чтобы потом быстро ее сглаживать"""
        if self.full_volume is None: return

        pos, size = self.roi.pos(), self.roi.size()
        vol = self.full_volume[:, int(pos.y()):int(pos.y() + size.y()), int(pos.x()):int(pos.x() + size.x())]

        try:
            # Сегментация
            mask = vol > self.thresh_slider.value()
            mask = morphology.binary_opening(mask, morphology.ball(2))

            # Оставляем только мозг
            labels = measure.label(mask)
            if labels.max() == 0: return
            mask = (labels == np.argmax(np.bincount(labels.flat)[1:]) + 1)

            # Marching Cubes
            verts, faces, _, _ = measure.marching_cubes(
                mask.astype(float), 0.5, spacing=(self.spacing[2], self.spacing[1], self.spacing[0])
            )

            faces_pv = np.hstack(np.c_[np.full(len(faces), 3), faces])
            mesh = pv.PolyData(verts, faces_pv)

            # Предварительная подготовка (Decimation)
            # Уменьшаем число полигонов на 30%, чтобы реалтайм летал
            self.raw_mesh = mesh.decimate(0.3)
            self.raw_mesh.flip_z(inplace=True)
            self.raw_mesh.rotate_x(-90, inplace=True)
            self.raw_mesh.compute_normals(inplace=True)

            self.smooth_slider.setEnabled(True)
            self.smooth_slider.setValue(0)
            self.apply_realtime_smooth()
            self.btn_export.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def apply_realtime_smooth(self):
        """Вызывается при движении слайдера сглаживания"""
        if self.raw_mesh is None: return

        iters = self.smooth_slider.value()
        self.lbl_smooth.setText(f"Smooth: {iters} iterations")

        if iters == 0:
            self.smooth_mesh = self.raw_mesh.copy()
        else:
            # Используем Taubin Smoothing (оно не уменьшает модель в размере)
            # В PyVista это реализовано через smooth_taubin
            self.smooth_mesh = self.raw_mesh.smooth_taubin(n_iter=iters, pass_band=0.1)

        # Обновляем только меш в плоттере, не пересоздавая сцену
        self.plotter.clear()
        self.plotter.add_mesh(
            self.smooth_mesh,
            color="#ffcc99",
            smooth_shading=True,
            specular=0.5,
            show_edges=False
        )
        self.plotter.enable_eye_dome_lighting()  # Добавляет четкость извилинам

    def export_obj(self):
        if self.smooth_mesh is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save OBJ", "brain_smooth.obj", "OBJ (*.obj)")
        if path:
            self.smooth_mesh.save(path)
            QMessageBox.information(self, "Success", "Smooth model exported!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = RealTimeBrainSmoother()
    ex.show()
    sys.exit(app.exec())