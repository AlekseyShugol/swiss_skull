import os
import json
import numpy as np
import pyqtgraph as pg
import pyvista as pv

from pyvistaqt import QtInteractor

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from convertation.conversion import BrainCleanerLogic


# ==================== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ====================

class LabeledSlider(QWidget):
    """Слайдер с меткой и полем ввода."""

    value_changed = Signal(int)

    def __init__(self, label, min_val, max_val, default_val, suffix="", step=1):
        super().__init__()

        self.suffix = suffix

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(f"{label}: {default_val}{suffix}")
        self.title_label.setStyleSheet("color: #AAA; font-size: 11px;")
        layout.addWidget(self.title_label)

        h_layout = QHBoxLayout()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #00E5FF;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #00E5FF;
                border-radius: 3px;
            }
        """)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setSuffix(suffix)
        self.spinbox.setFixedWidth(100)
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background: #222;
                color: #FFF;
                border: 1px solid #444;
                padding: 4px;
                border-radius: 3px;
            }
        """)

        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.spinbox)
        layout.addLayout(h_layout)

        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)

    def _on_slider_changed(self, value):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)
        self.title_label.setText(f"{self.title_label.text().split(':')[0]}: {value}{self.suffix}")
        self.value_changed.emit(value)

    def _on_spinbox_changed(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.title_label.setText(f"{self.title_label.text().split(':')[0]}: {value}{self.suffix}")
        self.value_changed.emit(value)

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)


class MainToolBar(QToolBar):
    """Главная панель инструментов."""

    def __init__(self, parent):
        super().__init__("Main Toolbar", parent)
        self.setMovable(False)
        self.setStyleSheet("""
            QToolBar {
                background: #1A1A1A;
                border-bottom: 2px solid #333;
                padding: 4px;
                spacing: 8px;
            }
        """)

        self.add_action("📁", "Open DICOM (Ctrl+O)", parent.select_folder)
        self.add_action("🔄", "Rebuild Selected (Ctrl+R)", parent.generate_selected_models)
        self.add_action("💾", "Export Selected (Ctrl+S)", parent.export_selected_models)
        self.addSeparator()
        self.add_action("🗑", "Clear Scene (Ctrl+L)", parent.clear_scene)
        self.addSeparator()
        self.add_action("📋", "View Metadata (Ctrl+M)", parent.show_metadata)
        self.addSeparator()
        self.add_action("❓", "Help (F1)", parent.show_shortcuts_help)

    def add_action(self, icon, tooltip, callback):
        action = QAction(icon, self)
        action.setToolTip(tooltip)
        action.triggered.connect(callback)
        self.addAction(action)


# ==================== СТИЛИ ====================

APP_STYLE = """
QMainWindow {
    background: #0D1117;
}

QGroupBox {
    color: #00E5FF;
    font-weight: bold;
    font-size: 13px;
    border: 2px solid #333;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background: #161B22;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #00E5FF;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2D3A4A, stop:1 #1A2332);
    color: #FFF;
    border: 1px solid #444;
    padding: 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D5A7A, stop:1 #2D3A4A);
    border: 1px solid #00E5FF;
}

QPushButton:pressed {
    background: #00E5FF;
    color: #000;
}

QPushButton:disabled {
    background: #222;
    color: #666;
    border: 1px solid #333;
}

QCheckBox {
    color: #CCC;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #555;
    border-radius: 3px;
    background: #222;
}

QCheckBox::indicator:checked {
    background: #00E5FF;
    border-color: #00E5FF;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #333;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background: #00E5FF;
    border-radius: 8px;
}

QSlider::sub-page:horizontal {
    background: #00E5FF;
    border-radius: 3px;
}

QLabel {
    color: #AAA;
    font-size: 12px;
}

QTextEdit {
    background: #0D1117;
    color: #CCC;
    border: 1px solid #333;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

#leftPanel {
    background: #0D1117;
    border-right: 2px solid #222;
}
"""


# ==================== ДИАЛОГИ ====================

def show_info(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet("""
        QMessageBox {
            background: #161B22;
            color: #FFF;
        }
        QLabel {
            color: #CCC;
            font-size: 13px;
        }
    """)
    msg.exec()


def show_warning(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet("""
        QMessageBox {
            background: #161B22;
            color: #FFF;
        }
        QLabel {
            color: #CCC;
            font-size: 13px;
        }
    """)
    msg.exec()


def show_error(parent, title, message):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet("""
        QMessageBox {
            background: #161B22;
            color: #FFF;
        }
        QLabel {
            color: #CCC;
            font-size: 13px;
        }
    """)
    msg.exec()


# ==================== ГЛАВНОЕ ОКНО ====================

class BrainCleaner3D(QMainWindow):

    def __init__(self, dicom_path=None, raw_img=None):
        super().__init__()

        self.processor = BrainCleanerLogic()

        self.setWindowTitle("Medical 3D • Brain Cleaner Pro")
        self.resize(1800, 1000)

        self.setStyleSheet(APP_STYLE)

        self.init_ui()

        self.toolbar = MainToolBar(self)
        self.addToolBar(self.toolbar)

        self.create_shortcuts()

        self.showMaximized()

        if raw_img is not None:
            self._load_raw(raw_img)

        elif dicom_path is not None:
            self._load_dicom(dicom_path)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

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

        self.thresh_slider = LabeledSlider("HU Threshold", -500, 7500, 40, " HU", 10)
        self.island_slider = LabeledSlider("Min Object Size", 100, 50000, 10000, "", 100)
        self.sigma_slider = LabeledSlider("Gaussian Sigma", 0, 30, 12, "", 1)
        self.smooth_iter_slider = LabeledSlider("Smooth Iterations", 0, 200, 50, "", 1)

        self.thresh_slider.value_changed.connect(self.update_plots)
        self.island_slider.value_changed.connect(self.update_plots)

        for slider in [self.thresh_slider, self.island_slider,
                       self.sigma_slider, self.smooth_iter_slider]:
            processing_group.layout().addWidget(slider)

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
        self.btn_mesh.clicked.connect(self.generate_selected_models)

        self.btn_export = QPushButton("💾 Export Selected Models")
        self.btn_export.clicked.connect(self.export_selected_models)
        self.btn_export.setEnabled(False)

        self.btn_metadata = QPushButton("📋 View Metadata")
        self.btn_metadata.clicked.connect(self.show_metadata)

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
        self.slice_slider.valueChanged.connect(self.update_plots)
        preview_layout.addWidget(self.slice_slider)

        splitter.addWidget(preview_widget)

        # 3D VIEW
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#111111")
        splitter.addWidget(self.plotter.interactor)
        splitter.setSizes([700, 1200])

        root.addWidget(splitter)

    def make_group(self, title):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        return group

    def create_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self.select_folder)
        QShortcut(QKeySequence("Ctrl+R"), self, self.generate_selected_models)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_selected_models)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_scene)
        QShortcut(QKeySequence("Ctrl+M"), self, self.show_metadata)

    def clear_scene(self):
        self.plotter.clear()
        self.btn_export.setEnabled(False)

    def _load_raw(self, raw_img):
        try:
            shape = self.processor.load_from_raw_image(raw_img)
            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()
            show_info(self, "Success", f"Volume loaded:\n{shape}")
        except Exception as e:
            show_error(self, "Error", str(e))

    def _load_dicom(self, path):
        try:
            shape = self.processor.load_from_dicom(path)
            self.slice_slider.setRange(0, shape[0] - 1)
            self.slice_slider.setValue(shape[0] // 2)
            self.update_plots()
            show_info(self, "Success", f"DICOM loaded:\n{shape}")
        except Exception as e:
            show_error(self, "Error", str(e))

    def select_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if path:
            self._load_dicom(path)

    def update_plots(self):
        z = self.slice_slider.value()
        img, mask = self.processor.get_slice(z, self.thresh_slider.value())
        if img is None:
            return
        self.img_item.setImage(img)
        if mask is not None:
            self.mask_item.setImage(
                mask,
                lut=np.array([[0, 0, 0, 0], [0, 255, 0, 120]])
            )

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
        return selected

    def generate_selected_models(self):
        """Строит ТОЛЬКО отмеченные галочками модели."""
        if self.processor.full_volume is None:
            show_warning(self, "Error", "No volume data loaded")
            return

        selected = self.get_selected_models()

        if not selected:
            show_warning(self, "Error", "No models selected! Check at least one box in BUILD SELECTION.")
            return

        pos = self.roi.pos()
        size = self.roi.size()
        roi_pos = (pos.x(), pos.y())
        roi_size = (size.x(), size.y())

        try:
            # build_selected_models возвращает self.models (словарь)
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

            self.plotter.clear()

            colors = {
                'brain': '#E6BE8A',
                'tumor': '#FF4444',
                'skull': '#CCCCCC',
                'arteria': '#FF6666'
            }

            models_found = []
            for model_name in selected:
                mesh = models[model_name]  # models это словарь, используем []
                if mesh is not None:
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

            if not models_found:
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

            show_info(self, "Models Built", msg)

        except Exception as e:
            show_warning(self, "Build Error", str(e))
            import traceback
            traceback.print_exc()

    def export_selected_models(self):
        """Экспортирует отмеченные галочками модели."""
        selected = self.get_selected_models()

        export_list = [m for m in selected if self.processor.models.get(m) is not None]

        if not export_list:
            available = [k for k, v in self.processor.models.items() if v is not None]
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
            try:
                exported = self.processor.export_all_models(directory, export_list)

                if not exported:
                    show_warning(self, "Export Error", "No files were exported.")
                    return

                export_list_str = []
                for model_type, path in exported.items():
                    if model_type != 'metadata':
                        export_list_str.append(f"✓ {model_type} → {os.path.basename(path)}")

                if 'metadata' in exported:
                    export_list_str.append(f"✓ metadata → model_data.json")

                show_info(self, "Export Success",
                          f"Exported to:\n{directory}\n\n" + "\n".join(export_list_str))

            except Exception as e:
                show_error(self, "Export Error", str(e))
                import traceback
                traceback.print_exc()

    def show_metadata(self):
        """Показывает текущие метаданные всех построенных моделей."""
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

    def show_shortcuts_help(self):
        text = (
            "SHORTCUTS\n\n"
            "Ctrl + O  → Open DICOM\n"
            "Ctrl + R  → Build Selected Models\n"
            "Ctrl + S  → Export Selected\n"
            "Ctrl + L  → Clear Scene\n"
            "Ctrl + M  → View Metadata"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", text)