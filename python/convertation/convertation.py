import sys
import numpy as np
import SimpleITK as sitk
import pyqtgraph as pg
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from skimage import measure, morphology


class BrainCleaner3D(QMainWindow):
    def __init__(self, dicom_path=None, raw_img=None):
        super().__init__()

        self.raw_img = raw_img  # Сохраняем переданное изображение
        self.dicom_path = dicom_path  # Сохраняем путь (на будущее)

        self.setWindowTitle("Medical 3D: Brain Cleaner Pro")
        self.setMinimumSize(1400, 900)

        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)
        self.last_mesh = None

        self.init_ui()

        # Автоматическая загрузка данных, если передан raw_img
        if self.raw_img is not None:
            self.load_from_raw_image()
        elif self.dicom_path is not None:
            self.load_data(self.dicom_path)

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
        self.thresh_slider.setValue(40)  # Стандарт для мягких тканей мозга
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

        controls.addSpacing(20)
        self.btn_mesh = QPushButton("⚡ REBUILD 3D MODEL")
        self.btn_mesh.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; height: 45px;")
        self.btn_mesh.clicked.connect(self.generate_3d)
        controls.addWidget(self.btn_mesh)

        self.btn_export = QPushButton("💾 EXPORT STL")
        self.btn_export.setStyleSheet("background-color: #28a745; color: white; height: 40px;")
        self.btn_export.clicked.connect(self.export_stl)
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

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if path:
            self.load_data(path)

    def load_from_raw_image(self):
        """Загрузка данных из переданного raw_img (numpy array или SimpleITK image)"""
        try:
            # Проверяем тип переданных данных
            if isinstance(self.raw_img, sitk.Image):
                # Если это SimpleITK изображение
                self.spacing = self.raw_img.GetSpacing()
                self.full_volume = sitk.GetArrayFromImage(self.raw_img)
                self.setWindowTitle(f"Medical 3D: Brain Cleaner Pro [Loaded from memory]")
            elif isinstance(self.raw_img, np.ndarray):
                # Если это numpy массив
                self.full_volume = self.raw_img
                self.spacing = (1.0, 1.0, 1.0)  # Стандартный spacing для numpy массива
                self.setWindowTitle(
                    f"Medical 3D: Brain Cleaner Pro [Loaded from array, shape={self.full_volume.shape}]")
            else:
                raise ValueError(f"Unsupported raw_img type: {type(self.raw_img)}")

            # Настройка слайдера
            self.slice_slider.setRange(0, self.full_volume.shape[0] - 1)
            self.slice_slider.setValue(self.full_volume.shape[0] // 2)

            # Обновляем отображение
            self.update_plots()

            # Делаем кнопку загрузки менее заметной, но оставляем активной
            self.btn_load.setText("📁 Load Another DICOM")

            QMessageBox.information(self, "Success",
                                    f"Data loaded from memory!\nVolume shape: {self.full_volume.shape}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from raw_img: {e}")

    def load_data(self, path):
        try:
            reader = sitk.ImageSeriesReader()
            names = reader.GetGDCMSeriesFileNames(path)
            reader.SetFileNames(names)
            image = reader.Execute()
            # Важно: SimpleITK отдает (X, Y, Z), а numpy массив [Z, Y, X]
            self.spacing = image.GetSpacing()
            self.full_volume = sitk.GetArrayFromImage(image)
            self.slice_slider.setRange(0, self.full_volume.shape[0] - 1)
            self.slice_slider.setValue(self.full_volume.shape[0] // 2)
            self.update_plots()
            self.setWindowTitle(f"Medical 3D: Brain Cleaner Pro [{path}]")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load failed: {e}")

    def update_plots(self):
        if self.full_volume is None: return
        z = self.slice_slider.value()
        t = self.thresh_slider.value()
        self.lbl_thresh.setText(f"Value: {t} HU")
        self.lbl_island.setText(f"Size: {self.island_slider.value()}")

        img = np.rot90(self.full_volume[z], -1)
        self.img_item.setImage(img)
        mask = (img > t).astype(np.uint8) * 255
        self.mask_item.setImage(mask, lut=np.array([[0, 0, 0, 0], [0, 255, 0, 100]]))

    def generate_3d(self):
        if self.full_volume is None: return

        # Обрезка по ROI
        pos, size = self.roi.pos(), self.roi.size()
        x0, x1 = int(pos.x()), int(pos.x() + size.x())
        y0, y1 = int(pos.y()), int(pos.y() + size.y())

        # Кропаем воксели [Z, Y, X]
        # Внимание: инверсия Y из-за особенностей отображения pyqtgraph
        vol = self.full_volume[:, y0:y1, x0:x1]

        try:
            # 1. Порог
            mask = vol > self.thresh_slider.value()

            # 2. Морфология БЕЗ СГЛАЖИВАНИЯ ГЕОМЕТРИИ
            # Opening — отделяет кору (удаляет тонкие связи)
            mask = morphology.binary_opening(mask, morphology.ball(2))
            # Closing — закрывает мелкие дыры внутри мозга, чтобы STL не был "битым"
            mask = morphology.binary_closing(mask, morphology.ball(1))

            # 3. Удаление мусора
            if self.check_largest.isChecked():
                labels = measure.label(mask)
                if labels.max() > 0:
                    mask = (labels == np.argmax(np.bincount(labels.flat)[1:]) + 1)
            else:
                mask = morphology.remove_small_objects(mask, min_size=self.island_slider.value())

            if not np.any(mask): return

            # 4. Marching Cubes
            # Используем физический spacing из DICOM
            verts, faces, normals, values = measure.marching_cubes(
                mask.astype(float),
                level=0.5,
                spacing=(self.spacing[2], self.spacing[1], self.spacing[0])
            )

            # 5. Сборка меша
            faces_pv = np.hstack(np.c_[np.full(len(faces), 3), faces])
            self.last_mesh = pv.PolyData(verts, faces_pv)

            # ИСПРАВЛЕНИЕ КООРДИНАТ:
            # В STL часто нужно, чтобы Z смотрел вверх, а DICOM может быть инвертирован
            # Также исправляем ориентацию (вращаем, если модель лежит на боку)
            self.last_mesh.rotate_z(180, inplace=True)

            # Визуализация
            self.plotter.clear()
            # Используем Eye Dome Lighting для рельефа БЕЗ сглаживания сетки
            self.plotter.add_mesh(self.last_mesh, color="#E6BE8A", show_edges=False)
            self.plotter.enable_eye_dome_lighting()
            self.plotter.reset_camera()
            self.btn_export.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "3D Error", str(e))

    def export_stl(self):
        if self.last_mesh is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save STL", "brain.stl", "STL (*.stl)")
        if path:
            # Сохраняем "сырую" геометрию, как просил
            self.last_mesh.save(path)
            QMessageBox.information(self, "OK", "Export Complete")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Примеры использования:

    # 1. Без параметров - нужно будет выбрать папку вручную
    # ex = BrainCleaner3D()

    # 2. С передачей numpy массива
    # import nibabel as nib
    # nifti_img = nib.load("brain.nii.gz")
    # raw_data = nifti_img.get_fdata()
    # ex = BrainCleaner3D(raw_img=raw_data)

    # 3. С передачей SimpleITK изображения
    # import SimpleITK as sitk
    # sitk_img = sitk.ReadImage("brain.mha")
    # ex = BrainCleaner3D(raw_img=sitk_img)

    # 4. С передачей пути к DICOM
    # ex = BrainCleaner3D(dicom_path="/path/to/dicom/folder")

    ex = BrainCleaner3D()  # Стандартный запуск
    ex.show()
    sys.exit(app.exec())