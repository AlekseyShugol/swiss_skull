import sys
import numpy as np
import SimpleITK as sitk
import pyqtgraph as pg
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from skimage import measure, morphology


class ContrastAnalyzer3D(QMainWindow):
    def __init__(self, dicom_path=None):
        super().__init__()
        self.setWindowTitle("Medical 3D: Brain Cleaner Edition")
        self.setMinimumSize(1400, 900)

        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)

        self.init_ui()

        if dicom_path:
            self.load_data(dicom_path)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # --- Левая панель (Управление) ---
        controls = QVBoxLayout()

        self.btn_load = QPushButton("📁 Open DICOM Folder")
        self.btn_load.clicked.connect(self.select_folder)
        controls.addWidget(self.btn_load)

        controls.addSpacing(15)
        controls.addWidget(QLabel("<b>HU Threshold:</b>"))
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(-1000, 2000)
        self.thresh_slider.setValue(200)
        self.thresh_slider.valueChanged.connect(self.update_plots)
        controls.addWidget(self.thresh_slider)
        self.lbl_thresh = QLabel("Value: 200 HU")
        controls.addWidget(self.lbl_thresh)

        controls.addSpacing(15)
        controls.addWidget(QLabel("<b>Island Removal (Voxel size):</b>"))
        self.island_slider = QSlider(Qt.Horizontal)
        self.island_slider.setRange(0, 10000)
        self.island_slider.setValue(1000)
        self.island_slider.valueChanged.connect(self.update_plots)
        controls.addWidget(self.island_slider)
        self.lbl_island = QLabel("Max Island: 1000")
        controls.addWidget(self.lbl_island)

        self.check_largest = QCheckBox("Keep ONLY Largest Object")
        self.check_largest.setChecked(True)
        self.check_largest.stateChanged.connect(self.update_plots)
        controls.addWidget(self.check_largest)

        controls.addSpacing(20)
        self.btn_mesh = QPushButton("⚡ REBUILD 3D MODEL")
        self.btn_mesh.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; height: 45px;")
        self.btn_mesh.clicked.connect(self.generate_3d)
        controls.addWidget(self.btn_mesh)

        controls.addStretch()
        layout.addLayout(controls, 1)

        # --- Центральная панель (2D Preview) ---
        v_layout_2d = QVBoxLayout()
        self.win = pg.GraphicsLayoutWidget()
        v_layout_2d.addWidget(self.win)

        # Слайдер срезов под 2D окном
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.valueChanged.connect(self.update_plots)
        v_layout_2d.addWidget(QLabel("Slice Selection:"))
        v_layout_2d.addWidget(self.slice_slider)

        layout.addLayout(v_layout_2d, 3)

        # Настройка pyqtgraph
        self.view = self.win.addViewBox()
        self.view.setAspectLocked(True)
        self.img_item = pg.ImageItem()
        self.view.addItem(self.img_item)
        self.mask_item = pg.ImageItem()
        self.mask_item.setOpacity(0.4)
        self.view.addItem(self.mask_item)

        self.roi = pg.RectROI([20, 20], [150, 150], pen=(0, 9))
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.view.addItem(self.roi)
        self.roi.sigRegionChanged.connect(self.update_plots)

        # --- Правая панель (Встроенное 3D окно) ---
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#121212")
        layout.addWidget(self.plotter.interactor, 4)

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
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
            QMessageBox.critical(self, "Error", f"Load failed: {e}")

    def update_plots(self):
        if self.full_volume is None: return
        z_idx = self.slice_slider.value()
        thresh = self.thresh_slider.value()
        self.lbl_thresh.setText(f"Value: {thresh} HU")
        self.lbl_island.setText(f"Max Island: {self.island_slider.value()}")

        # 2D обновление
        slice_data = np.rot90(self.full_volume[z_idx], -1)
        self.img_item.setImage(slice_data)
        contrast_mask = np.where(slice_data > thresh, 255, 0).astype(np.uint8)
        lut = np.zeros((256, 4), dtype=np.uint8)
        lut[255] = [0, 255, 65, 150]  # Ярко-зеленый контур
        self.mask_item.setImage(contrast_mask, lut=lut)

    def generate_3d(self):
        if self.full_volume is None: return

        pos, size = self.roi.pos(), self.roi.size()
        x_start, x_end = int(max(0, pos.x())), int(pos.x() + size.x())
        y_start, y_end = int(max(0, pos.y())), int(pos.y() + size.y())

        cropped = self.full_volume[:, y_start:y_end, x_start:x_end]
        if cropped.size == 0: return

        thresh = self.thresh_slider.value()
        isl_size = self.island_slider.value()

        try:
            # 1. Порог
            mask = cropped > thresh

            # 2. МОРФОЛОГИЧЕСКАЯ ОЧИСТКА (Размыкание)
            # Это удалит тонкие связи между корой и мозгом
            # ball(3) создает сферу радиусом 3 вокселя. Можно менять для усиления эффекта.
            mask = morphology.binary_opening(mask, morphology.ball(2))

            # 3. Удаление островов
            if isl_size > 0:
                mask = morphology.remove_small_objects(mask, min_size=isl_size)

            # 4. Оставляем только самый большой объект
            if self.check_largest.isChecked():
                labels = measure.label(mask)
                if labels.max() > 0:
                    counts = np.bincount(labels.flat)
                    counts[0] = 0
                    mask = (labels == np.argmax(counts))

            if not np.any(mask):
                QMessageBox.information(self, "3D", "No objects found.")
                return

            # 5. Marching Cubes
            # Убираем ds=2 (шаг) для максимальной детализации, если компьютер позволяет
            verts, faces, normals, values = measure.marching_cubes(
                mask.astype(float),
                level=0.5,
                spacing=self.spacing[::-1]
            )

            # 6. Визуализация
            faces_pv = np.hstack(np.c_[np.full(len(faces), 3), faces])
            mesh = pv.PolyData(verts, faces_pv)

            self.plotter.clear()

            # Добавляем освещение и тени для рельефности (Ambient/Diffuse)
            self.plotter.add_mesh(
                mesh,
                color="#E6BE8A",
                smooth_shading=True,
                specular=0.2,  # Блик
                ambient=0.3,  # Общий свет в тенях
                diffuse=0.7,  # Рассеянный свет
                show_edges=False  # Скрываем сетку для чистоты
            )

            # Включаем качественный свет
            self.plotter.enable_eye_dome_lighting()
            self.plotter.add_axes()
            self.plotter.reset_camera()

        except Exception as e:
            QMessageBox.warning(self, "3D Error", f"Failed: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ContrastAnalyzer3D()
    window.show()
    sys.exit(app.exec())