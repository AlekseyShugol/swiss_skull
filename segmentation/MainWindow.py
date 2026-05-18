import os
import sys
import uuid
import SimpleITK as sitk

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QIcon, QAction, QDoubleValidator, QIntValidator

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from segmentation.SettingsDialog import SettingsDialog
from segmentation.SkullStripper import SkullStripper


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.converter_window = None
        self.img_data = None
        self.mask_data = None
        self.raw_patient = None
        self.worker = None

        # Настройки по умолчанию
        self.settings = {
            'error_value': 1e-30,
            'iterations': 1000
        }

        self.setWindowTitle("proj")
        self.setMinimumSize(1200, 900)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #E0E0E0; 
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel#StatusLabel { 
                color: #00ff41;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QSlider::handle:horizontal {
                background: #00ff41;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px; 
                text-align: center;
                height: 15px;
            }
            QProgressBar::chunk {
                background-color: #00ff41; 
            }
            QToolBar {
                background-color: #1A1A1A;
                border-bottom: 2px solid #333;
                spacing: 5px;
                padding: 5px;
            }
            QToolBar QToolButton {
                background-color: #2D2D2D;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px 15px;
                color: #E0E0E0;
                font-weight: bold;
                margin: 2px;
            }
            QToolBar QToolButton:hover {
                background-color: #3D3D3D;
                border: 1px solid #00ff41;
            }
            QToolBar QToolButton:pressed {
                background-color: #00ff41;
                color: #000;
            }
            QToolBar QToolButton:disabled {
                color: #555;
                background-color: #1A1A1A;
                border: 1px solid #222;
            }
            QMenuBar {
                background-color: #1A1A1A;
                color: #E0E0E0;
                border-bottom: 1px solid #333;
            }
            QMenuBar::item:selected {
                background-color: #333;
            }
            QMenu {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #333;
            }
            QMenu::item:selected {
                background-color: #333;
            }
            QLineEdit {
                background-color: #2D2D2D;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 8px;
                color: #E0E0E0;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00ff41;
            }
        """)

        self.init_ui()
        self.create_toolbar()
        self.create_menubar()
        self.showMaximized()

    def create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        load_action = QAction("📂 Open", self)
        load_action.setToolTip("Load DICOM series from folder (clears previous data)")
        load_action.triggered.connect(self.load_dicom)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        self.run_action = QAction("▶ RUN", self)
        self.run_action.setToolTip("Run skull stripping segmentation")
        self.run_action.setEnabled(False)
        self.run_action.triggered.connect(self.run_process)
        toolbar.addAction(self.run_action)

        toolbar.addSeparator()

        clear_action = QAction("🗑 Clear", self)
        clear_action.setToolTip("Clear all images and reset view")
        clear_action.triggered.connect(self.clear_all)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        self.save_action = QAction("💾 Save Result", self)
        self.save_action.setToolTip("Save segmentation result as DICOM series")
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self.save_dicom)
        toolbar.addAction(self.save_action)

    def create_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_dicom)
        file_menu.addAction(open_action)

        self.save_menu_action = QAction("Save Result", self)
        self.save_menu_action.setShortcut("Ctrl+S")
        self.save_menu_action.setEnabled(False)
        self.save_menu_action.triggered.connect(self.save_dicom)
        file_menu.addAction(self.save_menu_action)

        file_menu.addSeparator()

        clear_action = QAction("Clear All", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self.clear_all)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        process_menu = menubar.addMenu("Processing")

        self.segment_menu_action = QAction("Run Segmentation", self)
        self.segment_menu_action.setShortcut("Ctrl+R")
        self.segment_menu_action.setEnabled(False)
        self.segment_menu_action.triggered.connect(self.run_process)
        process_menu.addAction(self.segment_menu_action)

        self.convert_menu_action = QAction("Open 3D Converter", self)
        self.convert_menu_action.setShortcut("Ctrl+T")
        self.convert_menu_action.setEnabled(False)
        self.convert_menu_action.triggered.connect(self.init_converter)
        process_menu.addAction(self.convert_menu_action)

        settings_menu = menubar.addMenu("Settings")

        segmentation_settings_action = QAction("Segmentation Parameters", self)
        segmentation_settings_action.setShortcut("Ctrl+P")
        segmentation_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(segmentation_settings_action)

        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(self, "About proj",
                          "Medical Image Processing Tool\n\n"
                          "Features:\n"
                          "• DICOM loading and visualization\n"
                          "• Skull stripping segmentation\n"
                          "• 3D volume conversion\n"
                          "• Result export to DICOM\n\n"
                          f"Current Settings:\n"
                          f"• Iterations: {self.settings['iterations']}\n"
                          f"• Convergence: {self.settings['error_value']:.0e}")

    def open_settings(self):
        dialog = SettingsDialog(
            self,
            error_value=self.settings['error_value'],
            iteration_value=self.settings['iterations']
        )

        if dialog.exec() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.lbl_info.setText(
                f">> SETTINGS UPDATED: {self.settings['iterations']} iterations, error={self.settings['error_value']:.0e}")

    def clear_all(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.worker = None

        self.img_data = None
        self.mask_data = None
        self.raw_patient = None

        self.ax1.clear()
        self.ax2.clear()
        self.ax1.axis('off')
        self.ax2.axis('off')
        self.canvas.draw()

        self.slider.setEnabled(False)
        self.slider.setValue(0)
        self.lbl_slice.setText("Slice: 0")

        self.run_action.setEnabled(False)
        self.segment_menu_action.setEnabled(False)
        self.save_action.setEnabled(False)
        self.save_menu_action.setEnabled(False)
        self.convert_menu_action.setEnabled(False)

        self.progress_bar.hide()

        self.lbl_info.setText(">> CLEARED - SYSTEM READY")
        self.setWindowTitle("SYSTEM READY")

        if hasattr(self, 'converter_window') and self.converter_window is not None:
            try:
                self.converter_window.close()
                self.converter_window.deleteLater()
            except:
                pass
            self.converter_window = None

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        info_layout = QHBoxLayout()
        self.lbl_info = QLabel(f">> SYSTEM READY")
        self.setWindowTitle("SYSTEM READY")
        self.lbl_info.setObjectName("StatusLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        info_layout.addWidget(self.lbl_info)
        info_layout.addWidget(self.progress_bar)
        main_layout.addLayout(info_layout)

        self.fig = Figure(facecolor='#121212', tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax1 = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        for ax in [self.ax1, self.ax2]:
            ax.set_facecolor('#121212')
            ax.axis('off')

        main_layout.addWidget(self.canvas, stretch=1)

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

        self.slider.valueChanged.connect(self.update_slice_view)

    def update_slice_view(self):
        self.lbl_slice.setText(f"Slice: {self.slider.value()}")
        self.draw()

    def load_dicom(self):
        self.clear_all()

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
                self.run_action.setEnabled(True)
                self.segment_menu_action.setEnabled(True)
                self.lbl_info.setText(f">> DATA LOADED: {self.img_data.shape}")
                self.setWindowTitle(f"DATA LOADED: {self.img_data.shape}")
                self.draw()
            except Exception as e:
                self.lbl_info.setText(f">> ERROR: {str(e)}")
        else:
            self.lbl_info.setText(">> CLEARED - SYSTEM READY")

    def run_process(self):
        self.run_action.setEnabled(False)
        self.segment_menu_action.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        atlas_image = os.path.join(current_dir, "atlasImage.mha")
        atlas_mask = os.path.join(current_dir, "atlasMask.mha")

        self.worker = SkullStripper(
            self.raw_patient,
            atlas_image,
            atlas_mask,
            error_value=self.settings['error_value'],
            iteration_value=self.settings['iterations']
        )
        self.worker.progress.connect(self.lbl_info.setText)
        self.worker.iteration_update.connect(self.update_iteration_title)
        self.worker.finished.connect(self.on_done)

        self.setWindowTitle(
            f"Processing - Settings: {self.settings['iterations']} iter, err={self.settings['error_value']:.0e}")
        self.worker.start()

    def update_iteration_title(self, iteration):
        total = self.settings['iterations']
        error_val = self.settings['error_value']
        self.setWindowTitle(f"Processing - Iteration {iteration}/{total} (error={error_val:.1e})")

    def on_done(self, img, mask):
        self.img_data = img
        self.mask_data = mask
        self.progress_bar.hide()
        self.run_action.setEnabled(True)
        self.segment_menu_action.setEnabled(True)
        self.save_action.setEnabled(True)
        self.save_menu_action.setEnabled(True)
        self.convert_menu_action.setEnabled(True)
        self.lbl_info.setText(">> SEGMENTATION COMPLETE")
        self.setWindowTitle("SEGMENTATION COMPLETE")
        self.draw()

    def draw(self):
        if self.img_data is None: return
        idx = self.slider.value()

        if idx >= self.img_data.shape[0]: return

        self.ax1.clear()
        self.ax2.clear()

        vmax = self.img_data.max() * 0.6
        vmin = self.img_data.min()

        self.ax1.imshow(self.img_data[idx], cmap='gray', vmax=vmax, vmin=vmin)

        if self.mask_data is not None:
            self.ax1.contour(self.mask_data[idx], colors='#00ffff', linewidths=0.5)
            res = self.img_data[idx] * self.mask_data[idx]
            self.ax2.imshow(res, cmap='gray', vmax=vmax, vmin=vmin)

        self.ax1.axis('off')
        self.ax2.axis('off')
        self.canvas.draw()

    def save_dicom(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения серии")
        if not out_dir:
            return

        try:
            self.lbl_info.setText("Генерация совместимой DICOM серии...")

            final_array = self.img_data * self.mask_data
            final_image = sitk.GetImageFromArray(final_array)
            final_image = sitk.Cast(final_image, sitk.sitkInt16)

            study_uid = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]
            series_uid = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]
            frame_of_ref = "1.2.826.0.1.3680043.2.1125." + str(uuid.uuid4().int)[:20]

            modification_time = QDateTime.currentDateTime().toString("hhmmss")
            modification_date = QDateTime.currentDateTime().toString("yyyyMMdd")

            writer = sitk.ImageFileWriter()
            writer.KeepOriginalImageUIDOn()

            depth = final_image.GetDepth()
            spacing = final_image.GetSpacing()
            origin = final_image.GetOrigin()
            direction = final_image.GetDirection()

            iop = f"{direction[0]}\\{direction[1]}\\{direction[2]}\\{direction[3]}\\{direction[4]}\\{direction[5]}"

            for i in range(depth):
                image_slice = final_image[:, :, i]

                image_slice.SetMetaData("0020|000d", study_uid)
                image_slice.SetMetaData("0020|000e", series_uid)
                image_slice.SetMetaData("0020|0052", frame_of_ref)
                image_slice.SetMetaData("0020|0013", str(i + 1))
                current_z = origin[2] + i * spacing[2]
                image_slice.SetMetaData("0020|0032", f"{origin[0]}\\{origin[1]}\\{current_z}")
                image_slice.SetMetaData("0020|0037", iop)
                image_slice.SetMetaData("0028|0030", f"{spacing[0]}\\{spacing[1]}")
                image_slice.SetMetaData("0018|0050", f"{spacing[2]}")
                image_slice.SetMetaData("0010|0010", "Patient^SkullStripped")
                image_slice.SetMetaData("0010|0020", "ID_001")
                image_slice.SetMetaData("0008|0060", "MR")
                image_slice.SetMetaData("0008|103e", "Skull Stripped Volume")

                filename = os.path.join(out_dir, f"IM_{i + 1:04d}.dcm")
                writer.SetFileName(filename)
                writer.Execute(image_slice)

            self.lbl_info.setText(f"Успех! Серия из {depth} срезов готова.")

        except Exception as e:
            self.lbl_info.setText(f"Ошибка: {str(e)}")

    def return_mask(self):
        return self.mask_data

    def init_converter(self):
        if self.img_data is None:
            QMessageBox.warning(self, "Warning", "No image data available. Please load DICOM first.")
            return

        try:
            if hasattr(self, 'converter_window') and self.converter_window is not None:
                try:
                    self.converter_window.close()
                    self.converter_window.deleteLater()
                except:
                    pass
                self.converter_window = None

            if self.mask_data is not None:
                masked_image = self.img_data * self.mask_data
                image_to_pass = masked_image.copy()
            else:
                image_to_pass = self.img_data.copy()

            # Импортируем здесь, чтобы избежать циклических импортов
            from convertation.MainWindow import BrainCleaner3D

            self.converter_window = BrainCleaner3D(raw_img=image_to_pass)
            self.converter_window.setAttribute(Qt.WA_DeleteOnClose, True)
            self.converter_window.destroyed.connect(self.on_converter_closed)
            self.converter_window.show()
            self.converter_window.raise_()
            self.converter_window.activateWindow()

            self.lbl_info.setText(">> 3D CONVERTER OPENED")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open converter: {str(e)}")
            self.lbl_info.setText(f">> ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_converter_closed(self):
        self.converter_window = None
        self.lbl_info.setText(">> 3D CONVERTER CLOSED")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())