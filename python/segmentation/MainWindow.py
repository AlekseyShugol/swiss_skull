import os
import uuid
import SimpleITK as sitk

from PySide6.QtWidgets import *
from PySide6.QtCore import *

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Импортируем ваши зависимости (убедитесь, что файлы рядом)
from python.segmentation.SkullStripper import SkullStripper


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- КРИТИЧЕСКИ ВАЖНО: Инициализация переменных до вызова интерфейса ---
        self.img_data = None
        self.mask_data = None
        self.raw_patient = None
        self.worker = None

        self.setWindowTitle("SwissSkullStripper GPU — Research Edition")
        self.setMinimumSize(1200, 900)

        # Стилизация (Тёмная тема)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI', sans-serif; }
            QFrame#ControlPanel { background-color: #1E1E1E; border-radius: 8px; border: 1px solid #333; }
            QPushButton { 
                background-color: #2D2D2D; border: 1px solid #444; border-radius: 4px; 
                padding: 10px 20px; font-weight: bold; min-width: 150px; 
            }
            QPushButton:hover { background-color: #3D3D3D; border: 1px solid #00ff41; }
            QPushButton:pressed { background-color: #00ff41; color: #000; }
            QPushButton:disabled { color: #555; background-color: #1A1A1A; border: 1px solid #222; }
            QLabel#StatusLabel { color: #00ff41; font-family: 'Consolas', monospace; font-size: 11px; }
            QSlider::handle:horizontal { background: #00ff41; width: 18px; margin: -5px 0; border-radius: 9px; }
            QProgressBar { border: 1px solid #333; border-radius: 5px; text-align: center; height: 15px; }
            QProgressBar::chunk { background-color: #00ff41; }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Панель кнопок
        self.controls = QFrame()
        self.controls.setObjectName("ControlPanel")
        ctrl_layout = QHBoxLayout(self.controls)

        self.btn_load = QPushButton("📁 LOAD DICOM")
        self.btn_run = QPushButton("⚡ RUN PROCESSING")
        self.btn_save = QPushButton("💾 SAVE RESULT")

        self.btn_run.setEnabled(False)
        self.btn_save.setEnabled(False)

        ctrl_layout.addWidget(self.btn_load)
        ctrl_layout.addWidget(self.btn_run)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_save)
        main_layout.addWidget(self.controls)

        # Статус-бар
        info_layout = QHBoxLayout()
        self.lbl_info = QLabel(f">> SYSTEM READY")
        self.lbl_info.setObjectName("StatusLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        info_layout.addWidget(self.lbl_info)
        info_layout.addWidget(self.progress_bar)
        main_layout.addLayout(info_layout)

        # Визуализация
        self.fig = Figure(facecolor='#121212', tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        for ax in [self.ax1, self.ax2]:
            ax.set_facecolor('#121212')
            ax.axis('off')

        main_layout.addWidget(self.canvas, stretch=1)

        # Слайдер
        slider_container = QHBoxLayout()
        self.lbl_slice = QLabel("Slice: 0")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        slider_container.addWidget(self.lbl_slice)
        slider_container.addWidget(self.slider)
        main_layout.addLayout(slider_container)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Связи
        self.btn_load.clicked.connect(self.load_dicom)
        self.btn_run.clicked.connect(self.run_process)
        self.btn_save.clicked.connect(self.save_dicom)
        self.slider.valueChanged.connect(self.update_slice_view)

    def update_slice_view(self):
        self.lbl_slice.setText(f"Slice: {self.slider.value()}")
        self.draw()

    def load_dicom(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку с DICOM")
        if path:
            try:
                reader = sitk.ImageSeriesReader()
                names = reader.GetGDCMSeriesFileNames(path)
                reader.SetFileNames(names)
                self.raw_patient = reader.Execute()

                preview = sitk.DICOMOrient(self.raw_patient, 'LPS')
                self.img_data = sitk.GetArrayFromImage(preview)

                self.slider.setEnabled(True)
                self.slider.setRange(0, self.img_data.shape[0] - 1)
                self.slider.setValue(self.img_data.shape[0] // 2)
                self.btn_run.setEnabled(True)
                self.lbl_info.setText(f">> DATA LOADED: {self.img_data.shape}")
                self.draw()
            except Exception as e:
                self.lbl_info.setText(f">> ERROR: {str(e)}")

    def run_process(self):
        self.btn_run.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(current_dir)
        atlas_image = os.path.join(current_dir, "atlasImage.mha")
        atlas_mask = os.path.join(current_dir, "atlasMask.mha")
        self.worker = SkullStripper(self.raw_patient, atlas_image, atlas_mask)
        self.worker.progress.connect(self.lbl_info.setText)
        self.worker.finished.connect(self.on_done)
        self.worker.start()

    def on_done(self, img, mask):
        self.img_data = img
        self.mask_data = mask
        self.progress_bar.hide()
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.lbl_info.setText(">> SEGMENTATION COMPLETE")
        self.draw()

    def draw(self):
        if self.img_data is None: return
        idx = self.slider.value()

        # Предотвращение выхода за границы массива
        if idx >= self.img_data.shape[0]: return

        self.ax1.clear();
        self.ax2.clear()

        vmax = self.img_data.max() * 0.6
        vmin = self.img_data.min()

        self.ax1.imshow(self.img_data[idx], cmap='gray', vmax=vmax, vmin=vmin)

        # Проверка наличия маски (теперь переменная точно существует)
        if self.mask_data is not None:
            self.ax1.contour(self.mask_data[idx], colors='#00ffff', linewidths=0.5)
            res = self.img_data[idx] * self.mask_data[idx]
            self.ax2.imshow(res, cmap='gray', vmax=vmax, vmin=vmin)

        self.ax1.axis('off');
        self.ax2.axis('off')
        self.canvas.draw()

    def save_dicom(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения серии")
        if not out_dir:
            return

        try:
            self.lbl_info.setText("Генерация совместимой DICOM серии...")

            # Применяем маску и приводим к int16
            final_array = self.img_data * self.mask_data
            final_image = sitk.GetImageFromArray(final_array)
            final_image = sitk.Cast(final_image, sitk.sitkInt16)

            # Генерируем уникальные UID для этой сессии
            # Важно: Study UID должен быть общим для всех, если это один "визит" пациента
            # Series UID — общий для всех файлов в этой папке
            study_uid = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]
            series_uid = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]
            frame_of_ref = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]

            modification_time = QDateTime.currentDateTime().toString("hhmmss")
            modification_date = QDateTime.currentDateTime().toString("yyyyMMdd")

            # Настройки записи
            writer = sitk.ImageFileWriter()
            writer.KeepOriginalImageUIDOn()

            depth = final_image.GetDepth()
            spacing = final_image.GetSpacing()
            origin = final_image.GetOrigin()
            direction = final_image.GetDirection()

            # Преобразуем направление (direction) в формат DICOM (0020,0037)
            # Это 6 чисел: косинусы ориентации строк и столбцов
            iop = f"{direction[0]}\\{direction[1]}\\{direction[2]}\\{direction[3]}\\{direction[4]}\\{direction[5]}"

            for i in range(depth):
                image_slice = final_image[:, :, i]

                # --- КРИТИЧЕСКИЕ ТЕГИ ДЛЯ ГРУППИРОВКИ ---
                image_slice.SetMetaData("0020|000d", study_uid)  # Study Instance UID
                image_slice.SetMetaData("0020|000e", series_uid)  # Series Instance UID
                image_slice.SetMetaData("0020|0052", frame_of_ref)  # Frame of Reference UID

                # --- ТЕГИ ПОРЯДКА И ПОЗИЦИИ ---
                image_slice.SetMetaData("0020|0013", str(i + 1))  # Instance Number
                # Вычисляем Z позицию для каждого среза
                current_z = origin[2] + i * spacing[2]
                image_slice.SetMetaData("0020|0032", f"{origin[0]}\\{origin[1]}\\{current_z}")  # Image Position
                image_slice.SetMetaData("0020|0037", iop)  # Image Orientation (Patient)
                image_slice.SetMetaData("0028|0030", f"{spacing[0]}\\{spacing[1]}")  # Pixel Spacing
                image_slice.SetMetaData("0018|0050", f"{spacing[2]}")  # Slice Thickness

                # --- ИНФОРМАЦИЯ О ПАЦИЕНТЕ (заглушки) ---
                image_slice.SetMetaData("0010|0010", "Patient^SkullStripped")  # Name
                image_slice.SetMetaData("0010|0020", "ID_001")  # Patient ID
                image_slice.SetMetaData("0008|0060", "MR")  # Modality
                image_slice.SetMetaData("0008|103e", "Skull Stripped Volume")  # Series Description

                filename = os.path.join(out_dir, f"IM_{i + 1:04d}.dcm")
                writer.SetFileName(filename)
                writer.Execute(image_slice)

            self.lbl_info.setText(f"Успех! Серия из {depth} срезов готова для Radiant.")

        except Exception as e:
            self.lbl_info.setText(f"Ошибка: {str(e)}")

