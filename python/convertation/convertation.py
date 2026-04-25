import sys
import numpy as np
import SimpleITK as sitk
import pyqtgraph as pg
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from skimage import measure, morphology
from scipy import ndimage


class BrainCleaner3D(QMainWindow):
    def __init__(self, dicom_path=None, raw_img=None):
        super().__init__()

        self.raw_img = raw_img
        self.dicom_path = dicom_path

        self.setWindowTitle("Medical 3D: Brain Cleaner Pro - Smooth Edition")
        self.setMinimumSize(1400, 900)

        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)
        self.last_mesh = None

        self.init_ui()

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

        # Добавляем чекбокс для центрирования модели
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

    def update_sigma_label(self):
        sigma = self.sigma_slider.value() / 10.0
        self.lbl_sigma.setText(f"Sigma: {sigma:.1f}")

    def update_iter_label(self):
        self.lbl_iter.setText(f"Iterations: {self.smooth_iter_slider.value()}")

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if path:
            self.load_data(path)

    def load_from_raw_image(self):
        """Загрузка данных из переданного raw_img (numpy array или SimpleITK image)"""
        try:
            if isinstance(self.raw_img, sitk.Image):
                self.spacing = self.raw_img.GetSpacing()
                self.full_volume = sitk.GetArrayFromImage(self.raw_img)
                self.setWindowTitle(f"Medical 3D: Brain Cleaner Pro [Loaded from memory]")
            elif isinstance(self.raw_img, np.ndarray):
                self.full_volume = self.raw_img
                self.spacing = (1.0, 1.0, 1.0)
                self.setWindowTitle(
                    f"Medical 3D: Brain Cleaner Pro [Loaded from array, shape={self.full_volume.shape}]")
            else:
                raise ValueError(f"Unsupported raw_img type: {type(self.raw_img)}")

            self.slice_slider.setRange(0, self.full_volume.shape[0] - 1)
            self.slice_slider.setValue(self.full_volume.shape[0] // 2)
            self.update_plots()
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

    def fix_orientation_and_center(self, mesh):
        """Исправляет ориентацию и центрирует модель для правильного экспорта"""

        # 1. Проверяем текущую ориентацию (для отладки)
        print(f"Original bounds: {mesh.bounds}")

        # 2. Правильная последовательность поворотов для медицинских данных
        # DICOM ориентация: X→Left-Right, Y→Anterior-Posterior, Z→Superior-Inferior
        # Нужно получить: X→Right, Y→Up, Z→Forward (стоя, лицом вперед)

        # Поворачиваем модель правильно
        mesh.rotate_z(90, inplace=True)  # Сначала поворачиваем вокруг Z
        mesh.rotate_x(-90, inplace=True)  # Потом наклоняем
        mesh.rotate_y(180, inplace=True)  # Разворачиваем лицом

        # 3. Центрируем модель (опционально)
        if self.check_center.isChecked():
            center = mesh.center
            mesh.points = mesh.points - center

            # Поднимаем модель, чтобы она стояла на платформе (Y=0)
            # Находим самую нижнюю точку по Y
            min_y = mesh.points[:, 1].min()
            if min_y < 0:
                mesh.points[:, 1] = mesh.points[:, 1] - min_y

            # Центрируем по X и Z
            mesh.points[:, 0] = mesh.points[:, 0]  # X оставляем центрированным
            mesh.points[:, 2] = mesh.points[:, 2]  # Z оставляем центрированным

        print(f"Fixed bounds: {mesh.bounds}")
        return mesh

    def generate_3d(self):
        if self.full_volume is None:
            return

        # Обрезка по ROI
        pos, size = self.roi.pos(), self.roi.size()
        x0, x1 = int(pos.x()), int(pos.x() + size.x())
        y0, y1 = int(pos.y()), int(pos.y() + size.y())

        x0, x1 = max(0, x0), min(self.full_volume.shape[2], x1)
        y0, y1 = max(0, y0), min(self.full_volume.shape[1], y1)

        if x0 >= x1 or y0 >= y1:
            QMessageBox.warning(self, "ROI Error", "Invalid ROI selection")
            return

        vol = self.full_volume[:, y0:y1, x0:x1]

        try:
            # 1. Порог
            threshold_value = self.thresh_slider.value()
            mask = vol > threshold_value

            if not np.any(mask):
                QMessageBox.warning(self, "Threshold", "No voxels above threshold. Try lowering HU value.")
                return

            # 2. Морфология
            try:
                mask = morphology.binary_opening(mask, morphology.ball(2))
                mask = morphology.binary_closing(mask, morphology.ball(1))
            except Exception as e:
                print(f"Morphology warning: {e}")

            if not np.any(mask):
                QMessageBox.warning(self, "Morphology", "Mask became empty after morphological operations.")
                return

            # 3. Удаление мусора
            if self.check_largest.isChecked():
                labels = measure.label(mask)
                if labels.max() == 0:
                    QMessageBox.warning(self, "Labeling", "No objects found in mask.")
                    return

                counts = np.bincount(labels.flat)
                if len(counts) <= 1:
                    QMessageBox.warning(self, "Labeling", "Only background found.")
                    return

                largest_label = np.argmax(counts[1:]) + 1
                mask = (labels == largest_label)
            else:
                min_size = self.island_slider.value()
                mask = morphology.remove_small_objects(mask, min_size=min_size)

            if not np.any(mask):
                QMessageBox.warning(self, "Cleanup", "No objects remain after cleanup. Try lowering minimum size.")
                return

            print(f"Mask shape: {mask.shape}, Non-zero voxels: {np.count_nonzero(mask)}")

            # 4. Создание плавной маски с помощью гауссовского размытия
            smooth_mask = mask.astype(np.float32)

            # Получаем параметры сглаживания
            sigma_value = self.sigma_slider.value() / 10.0

            if sigma_value > 0:
                # Гауссово размытие для сглаживания границ
                smooth_mask = ndimage.gaussian_filter(smooth_mask, sigma=sigma_value)

                # Применяем контраст для усиления границ
                smooth_mask = np.clip((smooth_mask - 0.3) / 0.5, 0, 1)
            else:
                # Без размытия, просто конвертируем
                smooth_mask = smooth_mask

            # 5. Marching Cubes
            spacing_x, spacing_y, spacing_z = self.spacing

            # Добавляем padding для избежания проблем на границах
            need_padding = (np.any(mask[0, :, :]) or np.any(mask[-1, :, :]) or
                            np.any(mask[:, 0, :]) or np.any(mask[:, -1, :]) or
                            np.any(mask[:, :, 0]) or np.any(mask[:, :, -1]))

            if need_padding:
                mask_padded = np.pad(smooth_mask, 2, mode='constant', constant_values=0)
                verts, faces, normals, values = measure.marching_cubes(
                    mask_padded,
                    level=0.5,
                    spacing=(spacing_z, spacing_y, spacing_x)
                )
                # Корректируем координаты с учетом padding
                verts = verts - np.array([spacing_z * 2, spacing_y * 2, spacing_x * 2])
            else:
                verts, faces, normals, values = measure.marching_cubes(
                    smooth_mask,
                    level=0.5,
                    spacing=(spacing_z, spacing_y, spacing_x)
                )

            if len(verts) == 0:
                QMessageBox.warning(self, "Marching Cubes", "Generated mesh has no vertices.")
                return

            # 6. Сборка меша
            faces_pv = np.hstack([np.full((len(faces), 1), 3), faces])
            mesh = pv.PolyData(verts, faces_pv)

            # 7. Сглаживание вершин (Laplacian smoothing)
            smooth_iterations = self.smooth_iter_slider.value()

            if smooth_iterations > 0:
                # Первый проход - основное сглаживание
                mesh = mesh.smooth(n_iter=smooth_iterations,
                                   relaxation_factor=0.5,
                                   feature_smoothing=False,
                                   boundary_smoothing=True,
                                   convergence=0.0)

                # Второй проход - более легкое сглаживание для финальной обработки
                if smooth_iterations > 30:
                    mesh = mesh.smooth(n_iter=int(smooth_iterations * 0.3),
                                       relaxation_factor=0.3,
                                       feature_smoothing=False,
                                       boundary_smoothing=True)

            # 8. Исправляем ориентацию и центрируем
            mesh = self.fix_orientation_and_center(mesh)

            self.last_mesh = mesh

            # 9. Визуализация с фиксированным телесным цветом
            self.plotter.clear()

            # Всегда используем однородный телесный цвет, без вычисления кривизны
            self.plotter.add_mesh(self.last_mesh,
                                  color="#E6BE8A",  # Телесный/персиковый цвет
                                  lighting=True,
                                  smooth_shading=True,  # Плавное затенение сохраняем
                                  show_edges=False,
                                  specular=0.3,  # Умеренный блеск
                                  specular_power=25,
                                  diffuse=0.7,
                                  ambient=0.3)

            # Улучшенное освещение для лучшей визуализации
            self.plotter.enable_eye_dome_lighting()

            # Добавляем дополнительные источники света для объемности
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

            print(f"Mesh generated successfully: {len(verts)} vertices, {len(faces)} faces")
            print(f"Mesh bounds: {self.last_mesh.bounds}")

        except ValueError as e:
            if "zero-size array" in str(e):
                QMessageBox.warning(self, "Empty Mask",
                                    "The mask became empty during processing.\n"
                                    "Try:\n"
                                    "- Lowering the HU threshold\n"
                                    "- Reducing minimum object size\n"
                                    "- Unchecking 'Keep ONLY Largest'")
            else:
                QMessageBox.warning(self, "3D Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "3D Error", f"Unexpected error: {str(e)}")

    def export_model(self):
        """Экспорт модели с поддержкой нескольких форматов"""
        if self.last_mesh is None:
            return

        # Предлагаем выбор формата (OBJ по умолчанию, так как он лучше)
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save 3D Model",
            "brain_model.obj",  # По умолчанию OBJ
            "OBJ Files (*.obj);;STL Files (*.stl);;PLY Files (*.ply)"
        )

        if path:
            try:
                # Для OBJ формата сохраняем с правильной ориентацией
                if path.endswith('.obj'):
                    # Сохраняем как OBJ (лучше сохраняет ориентацию)
                    self.last_mesh.save(path, binary=False)
                    QMessageBox.information(self, "Success",
                                            f"Model exported successfully as OBJ!\nSaved to: {path}\n\n"
                                            "OBJ format preserves orientation and is compatible with:\n"
                                            "- Blender\n"
                                            "- MeshLab\n"
                                            "- 3D printers\n"
                                            "- Most 3D software")
                elif path.endswith('.stl'):
                    self.last_mesh.save(path, binary=True)
                    QMessageBox.information(self, "Success",
                                            f"Model exported successfully as STL!\nSaved to: {path}")
                elif path.endswith('.ply'):
                    self.last_mesh.save(path, binary=True)
                    QMessageBox.information(self, "Success",
                                            f"Model exported successfully as PLY!\nSaved to: {path}")
                else:
                    # Если расширение не указано, добавляем OBJ
                    if '.' not in path:
                        path += '.obj'
                        self.last_mesh.save(path, binary=False)
                    else:
                        self.last_mesh.save(path)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Примеры использования:

    # 1. Без параметров - нужно будет выбрать папку вручную
    ex = BrainCleaner3D()

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

    ex.show()
    sys.exit(app.exec())