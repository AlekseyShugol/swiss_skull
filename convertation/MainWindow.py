import os
import json
import sys
import numpy as np
import pyvista as pv

from PySide6.QtWidgets import QMainWindow, QGroupBox, QFileDialog, QDialog, QVBoxLayout, QTextEdit, QPushButton, \
    QMessageBox
from PySide6.QtGui import QShortcut, QKeySequence

from convertation.MeshConverter import MeshConverter
from convertation.ui.dialogs import show_info, show_error, show_warning
from convertation.ui.main_window_panel import MainWindowPanel
from convertation.ui.styles import APP_STYLE
from convertation.ui.toolbar import MainToolBar
from logger.logger import log


class MainWindow(QMainWindow):

    def __init__(self, dicom_path=None, raw_img=None):
        super().__init__()

        log.separator()
        log.action("Application Start", "MainWindow initializing")
        log.info(f"Version: Medical 3D • Brain Cleaner Pro")
        log.info(f"Python version: {sys.version}")

        self.processor = MeshConverter()
        log.info("MeshConverter initialized")

        self.setWindowTitle("Medical 3D • Brain Cleaner Pro")
        self.resize(1800, 1000)

        self.setStyleSheet(APP_STYLE)

        self.init_ui()

        self.toolbar = MainToolBar(self)
        self.addToolBar(self.toolbar)
        log.info("Toolbar added")

        self.create_shortcuts()
        log.info("Shortcuts created")

        self.showMaximized()

        if raw_img is not None:
            log.action("Loading raw image data")
            self._load_raw(raw_img)

        elif dicom_path is not None:
            log.action(f"Loading DICOM from path: {dicom_path}")
            self._load_dicom(dicom_path)

        log.info("MainWindow initialization complete")

    def init_ui(self):
        self.window = MainWindowPanel(self)
        self.setCentralWidget(self.window)

        # Сохраняем ссылки на виджеты из панели для удобства
        self.plotter = self.window.plotter
        self.btn_export = self.window.btn_export
        self.slice_slider = self.window.slice_slider
        self.thresh_slider = self.window.thresh_slider
        self.island_slider = self.window.island_slider
        self.sigma_slider = self.window.sigma_slider
        self.smooth_iter_slider = self.window.smooth_iter_slider
        self.check_largest = self.window.check_largest
        self.check_brain = self.window.check_brain
        self.check_tumor = self.window.check_tumor
        self.check_skull = self.window.check_skull
        self.check_arteria = self.window.check_arteria
        self.roi = self.window.roi

    def make_group(self, title):
        group = QGroupBox(title)
        return group

    def create_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self.select_folder)
        QShortcut(QKeySequence("Ctrl+R"), self, self.generate_selected_models)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_selected_models)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_scene)
        QShortcut(QKeySequence("Ctrl+M"), self, self.show_metadata)
        log.debug("Shortcuts: Ctrl+O, Ctrl+R, Ctrl+S, Ctrl+L, Ctrl+M")

    def clear_scene(self):
        log.action("Clear scene")
        try:
            self.plotter.clear()
            self.btn_export.setEnabled(False)
            log.info("Scene cleared successfully")
        except Exception as e:
            log.error(f"Failed to clear scene: {str(e)}")
            show_error(self, "Error", f"Failed to clear scene: {str(e)}")

    def _load_raw(self, raw_img):
        try:
            log.info(f"Loading raw image of type: {type(raw_img)}")
            shape = self.processor.load_from_raw_image(raw_img)
            log.info(f"Raw image loaded. Shape: {shape}, Spacing: {self.processor.spacing}")

            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()

            log.action("Raw image loaded successfully", f"Shape: {shape}")
            show_info(self, "Success", f"Volume loaded:\n{shape}")
        except Exception as e:
            log.error(f"Failed to load raw image: {str(e)}", include_traceback=True)
            show_error(self, "Error", str(e))

    def _load_dicom(self, path):
        try:
            log.info(f"Loading DICOM from: {path}")
            shape = self.processor.load_from_dicom(path)
            log.info(f"DICOM loaded. Shape: {shape}, Spacing: {self.processor.spacing}")

            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()

            log.action("DICOM loaded successfully", f"Path: {path}, Shape: {shape}")
            show_info(self, "Success", f"DICOM loaded:\n{shape}")
        except Exception as e:
            log.error(f"Failed to load DICOM from {path}: {str(e)}", include_traceback=True)
            show_error(self, "Error", str(e))

    def select_folder(self):
        log.action("Opening directory selection dialog")
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if path:
            log.info(f"User selected directory: {path}")
            self._load_dicom(path)
        else:
            log.info("User cancelled directory selection")

    def update_plots(self):
        try:
            z = self.slice_slider.value()
            threshold = self.thresh_slider.value()
            log.debug(f"Updating plots: slice={z}, threshold={threshold}")

            img, mask = self.processor.get_slice(z, threshold)
            if img is None:
                log.warning("get_slice returned None for img")
                return

            self.window.img_item.setImage(img)
            if mask is not None:
                self.window.mask_item.setImage(
                    mask,
                    lut=np.array([[0, 0, 0, 0], [0, 255, 0, 120]])
                )
        except Exception as e:
            log.error(f"Error updating plots: {str(e)}", include_traceback=True)

    def get_selected_models(self):
        """Возвращает список отмеченных галочками моделей."""
        selected = []
        if self.check_brain.isChecked():
            selected.append('brain')
        if self.check_tumor.isChecked():
            selected.append('tumor')
        if self.check_skull.isChecked():
            selected.append('skull')
        if self.check_arteria.isChecked():
            selected.append('arteria')

        log.debug(f"Selected models: {selected}")
        return selected

    def generate_selected_models(self):
        """Строит ТОЛЬКО отмеченные галочками модели."""
        log.separator()
        log.action("Generate selected models started")

        if self.processor.full_volume is None:
            log.warning("No volume data loaded - cannot generate models")
            show_warning(self, "Error", "No volume data loaded")
            return

        selected = self.get_selected_models()

        if not selected:
            log.warning("No models selected for generation")
            show_warning(self, "Error", "No models selected! Check at least one box in BUILD SELECTION.")
            return

        pos = self.roi.pos()
        size = self.roi.size()
        roi_pos = (pos.x(), pos.y())
        roi_size = (size.x(), size.y())

        log.info(f"ROI position: {roi_pos}, size: {roi_size}")
        log.info(f"Parameters: threshold={self.thresh_slider.value()}, "
                 f"min_island={self.island_slider.value()}, "
                 f"keep_largest={self.check_largest.isChecked()}, "
                 f"sigma={self.sigma_slider.value() / 10.0}, "
                 f"smooth_iter={self.smooth_iter_slider.value()}")

        try:
            models = self.processor.build_selected_models(
                selected_types=selected,
                roi_pos=roi_pos,
                roi_size=roi_size,
                threshold_value=self.thresh_slider.value(),
                min_island_size=self.island_slider.value(),
                keep_largest=self.check_largest.isChecked(),
                sigma_value=self.sigma_slider.value() / 10.0,
                smooth_iterations=self.smooth_iter_slider.value(),
                center_model=True
            )

            log.info(f"Models built: {list(models.keys())}")

            self.plotter.clear()

            colors = {
                'brain': '#E6BE8A',
                'tumor': '#FF4444',
                'skull': '#CCCCCC',
                'arteria': '#FF6666'
            }

            models_found = []
            for model_name in selected:
                mesh = models.get(model_name)
                if mesh is not None:
                    log.info(f"Adding {model_name} to 3D view (vertices: {mesh.n_points})")
                    self.plotter.add_mesh(
                        mesh,
                        color=colors.get(model_name, '#888888'),
                        lighting=True,
                        smooth_shading=True,
                        show_edges=False,
                        specular=0.3,
                        specular_power=25,
                        diffuse=0.7,
                        ambient=0.3,
                        label=model_name
                    )
                    models_found.append(model_name)
                else:
                    log.warning(f"{model_name} mesh is None - not added to view")

            if not models_found:
                log.warning(f"No models generated from selection: {selected}")
                show_warning(self, "Warning",
                             f"No models generated from selection: {', '.join(selected)}\n"
                             f"Try adjusting the threshold (current: {self.thresh_slider.value()} HU)\n"
                             f"Or change ROI position/size.")
                return

            self.plotter.enable_eye_dome_lighting()

            light1 = pv.Light(position=(5, 5, 10), light_type='scene light')
            light1.intensity = 0.8
            self.plotter.add_light(light1)

            light2 = pv.Light(position=(-5, -5, 5), light_type='scene light')
            light2.intensity = 0.5
            self.plotter.add_light(light2)

            self.plotter.reset_camera()

            self.btn_export.setEnabled(True)
            log.info(f"Export button enabled, models in view: {models_found}")

            # Показываем информацию
            msg = f"Built: {', '.join(models_found)}\n\n"
            for model_name in models_found:
                meta = self.processor.model_metadata.get(model_name, {})
                if meta.get('status') == 'ready':
                    msg += f"--- {model_name} ---\n"
                    msg += f"  Vertices: {meta.get('vertices', 'N/A')}\n"
                    scale = meta.get('scale', {})
                    msg += f"  Size: {scale.get('x', 0):.1f} × "
                    msg += f"{scale.get('y', 0):.1f} × "
                    msg += f"{scale.get('z', 0):.1f} mm\n"
                    if 'relative_to_brain' in meta and model_name != 'brain':
                        dist = meta['relative_to_brain'].get('distance_mm', 0)
                        msg += f"  Distance from brain center: {dist:.1f} mm\n"
                    msg += "\n"

            log.action("Models generated successfully", f"Models: {models_found}")
            show_info(self, "Models Built", msg)

        except Exception as e:
            log.error(f"Build error: {str(e)}", include_traceback=True)
            show_warning(self, "Build Error", str(e))

    def export_selected_models(self):
        """Экспортирует отмеченные галочками модели."""
        log.separator()
        log.action("Export selected models started")

        selected = self.get_selected_models()

        # Проверяем, какие модели реально существуют
        export_list = []
        for m in selected:
            if self.processor.models.get(m) is not None:
                export_list.append(m)
                log.debug(f"Model {m} available for export")
            else:
                log.warning(f"Model {m} is None - cannot export")

        if not export_list:
            available = [k for k, v in self.processor.models.items() if v is not None]
            log.warning(f"No models to export. Selected: {selected}, Available: {available}")

            msg = "No models to export!\n\n"
            msg += f"Selected: {', '.join(selected)}\n"
            msg += f"Available: {', '.join(available) if available else 'NONE'}\n\n"

            if not available:
                msg += "Build models first!\n"
                msg += "1. Check boxes in BUILD SELECTION\n"
                msg += "2. Adjust threshold for your data (КТ/МРТ)\n"
                msg += "3. Click 'Build Selected Models'"
            else:
                msg += "Check boxes for available models."

            show_warning(self, "Export Error", msg)
            return

        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory")

        if directory:
            log.info(f"Export directory selected: {directory}")
            try:
                exported = self.processor.export_all_models(directory, export_list)
                log.info(f"Exported files: {exported}")

                if not exported:
                    log.warning("No files were exported")
                    show_warning(self, "Export Error", "No files were exported.")
                    return

                export_list_str = []
                for model_type, path in exported.items():
                    if model_type != 'metadata':
                        export_list_str.append(f"✓ {model_type} → {os.path.basename(path)}")
                        log.debug(f"Exported {model_type} to {path}")

                if 'metadata' in exported:
                    export_list_str.append(f"✓ metadata → model_data.json")
                    log.debug(f"Exported metadata to {exported['metadata']}")

                log.action("Export completed successfully", f"Directory: {directory}, Files: {len(exported)}")
                show_info(self, "Export Success",
                          f"Exported to:\n{directory}\n\n" + "\n".join(export_list_str))

            except Exception as e:
                log.error(f"Export error: {str(e)}", include_traceback=True)
                show_error(self, "Export Error", str(e))
        else:
            log.info("User cancelled export directory selection")

    def show_metadata(self):
        """Показывает текущие метаданные всех построенных моделей."""
        log.action("View metadata")

        metadata = self.processor.model_metadata

        display_data = {
            'models': {}
        }

        for model_type in ['brain', 'tumor', 'skull', 'arteria']:
            if model_type in metadata and metadata[model_type]:
                display_data['models'][model_type] = metadata[model_type]
            else:
                display_data['models'][model_type] = {'status': 'not_built'}

        json_str = json.dumps(display_data, indent=2, ensure_ascii=False)
        log.debug(f"Metadata content: {json_str[:200]}...")  # Логируем только начало

        dialog = QDialog(self)
        dialog.setWindowTitle("Model Metadata")
        dialog.resize(600, 700)
        dialog.setStyleSheet("""
            QDialog {
                background: #161B22;
            }
        """)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(json_str)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()
        log.info("Metadata dialog closed")

    def show_shortcuts_help(self):
        log.action("Show shortcuts help")
        text = (
            "SHORTCUTS\n\n"
            "Ctrl + O  → Open DICOM\n"
            "Ctrl + R  → Build Selected Models\n"
            "Ctrl + S  → Export Selected\n"
            "Ctrl + L  → Clear Scene\n"
            "Ctrl + M  → View Metadata"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", text)