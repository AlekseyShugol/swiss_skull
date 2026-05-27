import numpy as np
import SimpleITK as sitk
import pyvista as pv
from skimage import measure, morphology
from scipy import ndimage
import json
import os

from convertation.mesh_data.model_metadata import DATA


class MeshConverter:
    """логика обработки медицинских 3D-данных."""

    def __init__(self):
        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)
        self.last_mesh = None

        # Хранилище для 4-х моделей
        self.models = {
            'brain': None,
            'tumor': None,
            'skull': None,
            'arteria': None
        }

        # Метаданные для JSON
        self.model_metadata = DATA

    def load_from_raw_image(self, raw_img):
        """Загрузка данных из переданного raw_img (numpy array или SimpleITK image)."""
        if isinstance(raw_img, sitk.Image):
            self.spacing = raw_img.GetSpacing()
            self.full_volume = sitk.GetArrayFromImage(raw_img)
        elif isinstance(raw_img, np.ndarray):
            self.full_volume = raw_img
            self.spacing = (1.0, 1.0, 1.0)
        else:
            raise ValueError(f"Unsupported raw_img type: {type(raw_img)}")
        return self.full_volume.shape

    def load_from_dicom(self, path):
        """Загрузка DICOM серии."""
        reader = sitk.ImageSeriesReader()
        names = reader.GetGDCMSeriesFileNames(path)
        reader.SetFileNames(names)
        image = reader.Execute()
        self.spacing = image.GetSpacing()
        self.full_volume = sitk.GetArrayFromImage(image)
        return self.full_volume.shape

    def get_slice(self, z, threshold=None):
        """Возвращает срез и маску для отображения."""
        if self.full_volume is None:
            return None, None

        img = np.rot90(self.full_volume[z], -1)

        if threshold is not None:
            mask = (img > threshold).astype(np.uint8) * 255
        else:
            mask = None

        return img, mask

    def fix_orientation_and_center(self, mesh, center_model=True):
        """Исправляет ориентацию и центрирует модель."""

        original_bounds = mesh.bounds
        print(f"Original bounds: {original_bounds}")

        if center_model:
            center = mesh.center
            mesh.points = mesh.points - center

        points = mesh.points.copy()
        mesh.points[:, 0] = points[:, 2]  # X <- Z (left-right)
        mesh.points[:, 1] = points[:, 0]  # Y <- X (superior-inferior, вверх)
        mesh.points[:, 2] = points[:, 1]  # Z <- Y (anterior-posterior, вперёд)

        min_y = mesh.points[:, 1].min()
        if min_y < 0:
            mesh.points[:, 1] = mesh.points[:, 1] - min_y

        mesh.points[:, 0] = mesh.points[:, 0] - mesh.points[:, 0].mean()
        mesh.points[:, 2] = mesh.points[:, 2] - mesh.points[:, 2].mean()

        print(f"Fixed bounds: {mesh.bounds}")
        return mesh

    def _generate_single_mesh(self, mask, sigma_value, smooth_iterations, center_model):
        """Вспомогательный метод для создания меша из маски."""
        if not np.any(mask):
            return None

        try:
            # Морфологическая обработка
            processed_mask = morphology.binary_opening(mask, morphology.ball(2))
            processed_mask = morphology.binary_closing(processed_mask, morphology.ball(1))

            if not np.any(processed_mask):
                return None

            # Сглаживание маски
            smooth_mask = processed_mask.astype(np.float32)
            if sigma_value > 0:
                smooth_mask = ndimage.gaussian_filter(smooth_mask, sigma=sigma_value)
                smooth_mask = np.clip((smooth_mask - 0.3) / 0.5, 0, 1)

            # Marching Cubes
            spacing_x, spacing_y, spacing_z = self.spacing

            need_padding = (
                    np.any(processed_mask[0, :, :])     or
                    np.any(processed_mask[-1, :, :])    or
                    np.any(processed_mask[:, 0, :])     or
                    np.any(processed_mask[:, -1, :])    or
                    np.any(processed_mask[:, :, 0])     or 
                    np.any(processed_mask[:, :, -1])
            )

            if need_padding:
                mask_padded = np.pad(smooth_mask, 2, mode='constant', constant_values=0)
                verts, faces, normals, values = measure.marching_cubes(
                    mask_padded, level=0.5, spacing=(spacing_z, spacing_y, spacing_x)
                )
                verts = verts - np.array([spacing_z * 2, spacing_y * 2, spacing_x * 2])
            else:
                verts, faces, normals, values = measure.marching_cubes(
                    smooth_mask, level=0.5, spacing=(spacing_z, spacing_y, spacing_x)
                )

            if len(verts) == 0:
                return None

            # Сборка меша
            faces_pv = np.hstack([np.full((len(faces), 1), 3), faces])
            mesh = pv.PolyData(verts, faces_pv)

            # Сглаживание
            if smooth_iterations > 0:
                mesh = mesh.smooth(n_iter=smooth_iterations, relaxation_factor=0.5,
                                   feature_smoothing=False, boundary_smoothing=True, convergence=0.0)
                if smooth_iterations > 30:
                    mesh = mesh.smooth(n_iter=int(smooth_iterations * 0.3), relaxation_factor=0.3,
                                       feature_smoothing=False, boundary_smoothing=True)

            # Ориентация и центрирование
            mesh = self.fix_orientation_and_center(mesh, center_model)

            return mesh

        except Exception as e:
            print(f"Error generating mesh: {e}")
            return None

    def build_single_model(self, model_type, roi_pos, roi_size, threshold_value, min_island_size, keep_largest, sigma_value, smooth_iterations, center_model):
        """
        Строит ОДНУ модель указанного типа из выделенной ROI.
        Использует ТОЛЬКО порог пользователя.
        """
        if self.full_volume is None:
            raise ValueError("No volume data loaded")

        # Обрезка по ROI
        x0, x1 = int(roi_pos[0]), int(roi_pos[0] + roi_size[0])
        y0, y1 = int(roi_pos[1]), int(roi_pos[1] + roi_size[1])

        x0, x1 = max(0, x0), min(self.full_volume.shape[2], x1)
        y0, y1 = max(0, y0), min(self.full_volume.shape[1], y1)

        if x0 >= x1 or y0 >= y1:
            raise ValueError("Invalid ROI selection")

        vol = self.full_volume[:, y0:y1, x0:x1]

        print(f"\nBuilding model: {model_type}")
        print(f"Volume shape: {vol.shape}, Threshold: {threshold_value}")
        print(f"Volume min: {vol.min()}, max: {vol.max()}, mean: {vol.mean():.2f}")

        # СОЗДАЁМ МАСКУ ТОЛЬКО ПО ПОРОГУ ПОЛЬЗОВАТЕЛЯ
        # Пользователь сам выбирает что выделять через ROI и порог
        if model_type == 'skull':
            # Для черепа: высокие значения HU (>200 для КТ)
            # Но пользователь может настроить порог под МРТ
            mask = vol > max(200, threshold_value)
        elif model_type == 'arteria':
            # Для сосудов: средние значения
            mask = (vol > threshold_value) & (vol < threshold_value + 100)
        else:
            # Для мозга и опухоли: используем порог пользователя напрямую
            # Для мозга на МРТ может быть низкий порог (20-40)
            # Для КТ мозга может быть 20-80
            # Для опухоли порог выше
            mask = vol > threshold_value

        print(f"Mask voxels before cleanup: {np.sum(mask)}")

        if not np.any(mask):
            print(f"No voxels found for {model_type} with threshold {threshold_value}")
            return None

        # Удаление мусора
        if keep_largest:
            labels = measure.label(mask)
            if labels.max() > 0:
                counts = np.bincount(labels.flat)
                if len(counts) > 1:
                    largest_label = np.argmax(counts[1:]) + 1
                    mask = (labels == largest_label)
        else:
            mask = morphology.remove_small_objects(mask, min_size=min_island_size)

        print(f"Mask voxels after cleanup: {np.sum(mask)}")

        if not np.any(mask):
            print(f"No objects remain after cleanup for {model_type}")
            return None

        # Генерируем меш
        mesh = self._generate_single_mesh(mask, sigma_value, smooth_iterations, center_model)

        if mesh is not None:
            print(f"✓ {model_type} mesh generated: {mesh.n_points} vertices")
            # Обновляем метаданные
            center = mesh.center
            # Преобразуем tuple в список, если нужно
            if isinstance(center, tuple):
                center_list = list(center)
            else:
                center_list = center.tolist() if hasattr(center, 'tolist') else list(center)

            self.model_metadata[model_type] = {
                'status': 'ready',
                'vertices': mesh.n_points,
                'scale': {
                    'x': mesh.bounds[1] - mesh.bounds[0],
                    'y': mesh.bounds[3] - mesh.bounds[2],
                    'z': mesh.bounds[5] - mesh.bounds[4]
                },
                'position': center_list
            }
        else:
            print(f"✗ {model_type} mesh generation failed")
            self.model_metadata[model_type] = {'status': 'failed'}

        return mesh

    def build_selected_models(self, selected_types, roi_pos, roi_size, threshold_value, min_island_size, keep_largest, sigma_value, smooth_iterations, center_model):
        """
        Строит только выбранные пользователем модели.
        selected_types: список ['brain', 'tumor', 'skull', 'arteria']
        Возвращает словарь моделей.
        """
        print(f"\n{'=' * 60}")
        print(f"Building selected models: {selected_types}")
        print(f"{'=' * 60}")

        for model_type in selected_types:
            mesh = self.build_single_model(
                model_type, roi_pos, roi_size, threshold_value,
                min_island_size, keep_largest, sigma_value,
                smooth_iterations, center_model
            )
            self.models[model_type] = mesh

        # Рассчитываем позицию опухоли относительно мозга
        if 'tumor' in selected_types or 'brain' in selected_types:
            self.calculate_tumor_position()

        # Возвращаем словарь моделей (только построенные, но с ключами)
        return {k: v for k, v in self.models.items() if k in selected_types}

    def calculate_tumor_position(self):
        """Расчет позиции опухоли относительно мозга."""
        if self.models.get('brain') is not None and self.models.get('tumor') is not None:
            # Получаем центры и преобразуем в numpy массивы
            brain_center = np.array(self.models['brain'].center)
            tumor_center = np.array(self.models['tumor'].center)

            # Вычитаем массивы
            relative_position = tumor_center - brain_center

            # Расстояние
            distance = np.linalg.norm(relative_position)

            brain_bounds = self.models['brain'].bounds
            brain_size = {
                'x': brain_bounds[1] - brain_bounds[0],
                'y': brain_bounds[3] - brain_bounds[2],
                'z': brain_bounds[5] - brain_bounds[4]
            }

            tumor_bounds = self.models['tumor'].bounds
            tumor_size = {
                'x': tumor_bounds[1] - tumor_bounds[0],
                'y': tumor_bounds[3] - tumor_bounds[2],
                'z': tumor_bounds[5] - tumor_bounds[4]
            }

            # Обновляем метаданные
            if 'tumor' in self.model_metadata:
                self.model_metadata['tumor'].update({
                    'position_relative_to_brain': relative_position.tolist(),
                    'distance_from_brain_center_mm': float(distance),
                    'scale': tumor_size,
                    'status': 'ready'
                })
            else:
                self.model_metadata['tumor'] = {
                    'position_relative_to_brain': relative_position.tolist(),
                    'distance_from_brain_center_mm': float(distance),
                    'scale': tumor_size,
                    'status': 'ready'
                }

            if 'brain' in self.model_metadata:
                self.model_metadata['brain'].update({
                    'position': [0, 0, 0],
                    'scale': brain_size,
                    'status': 'ready'
                })

            print(f"Tumor position relative to brain: {relative_position}")
            print(f"Distance from brain center: {distance:.2f} mm")
        else:
            if self.models.get('brain') is not None:
                brain_bounds = self.models['brain'].bounds
                brain_size = {
                    'x': brain_bounds[1] - brain_bounds[0],
                    'y': brain_bounds[3] - brain_bounds[2],
                    'z': brain_bounds[5] - brain_bounds[4]
                }
                if 'brain' in self.model_metadata:
                    self.model_metadata['brain'].update({
                        'position': [0, 0, 0],
                        'scale': brain_size,
                        'status': 'ready'
                    })

            if self.models.get('tumor') is None and 'tumor' in self.model_metadata:
                self.model_metadata['tumor']['status'] = 'not_found'

    def export_model(self, path, model_type='brain'):
        """Экспорт конкретной модели в файл."""
        print(f"Attempting to export {model_type} model...")

        if model_type not in self.models:
            raise ValueError(f"Unknown model type: {model_type}")

        if self.models[model_type] is None:
            raise ValueError(f"No {model_type} mesh to export. Model is None.")

        mesh = self.models[model_type]
        print(f"Exporting {model_type} mesh with {mesh.n_points} vertices to {path}")

        if path.endswith('.obj'):
            mesh.save(path, binary=False)
        elif path.endswith('.stl') or path.endswith('.ply'):
            mesh.save(path, binary=True)
        else:
            if '.' not in path:
                path += '.obj'
                mesh.save(path, binary=False)
            else:
                mesh.save(path)

        print(f"Successfully exported to {path}")
        return path

    def export_all_models(self, directory, selected_models=None, export_json=True):
        """Экспорт выбранных моделей с правильными именами."""
        exported_files = {}

        model_filenames = {
            'brain': 'brain.obj',
            'tumor': 'tumor.obj',
            'skull': 'skull.obj',
            'arteria': 'arteria.obj'
        }

        if selected_models is None:
            selected_models = list(model_filenames.keys())

        print(f"Exporting models: {selected_models}")

        for model_type in selected_models:
            if model_type in self.models and self.models[model_type] is not None:
                filepath = os.path.join(directory, model_filenames[model_type])
                try:
                    self.export_model(filepath, model_type)
                    exported_files[model_type] = filepath
                    print(f"✓ Exported {model_type} to {filepath}")
                except Exception as e:
                    print(f"✗ Failed to export {model_type}: {e}")
            else:
                print(f"✗ No {model_type} model to export")

        # Экспорт JSON с метаданными
        if export_json and len(exported_files) > 0:
            json_path = os.path.join(directory, 'model_data.json')
            self.export_metadata_json(json_path)
            exported_files['metadata'] = json_path

        return exported_files

    def export_metadata_json(self, json_path):
        """Экспорт JSON с пропорциями и позициями моделей."""
        metadata = {
            'models': self.model_metadata,
            'coordinate_system': 'unity',
            'units': 'millimeters',
            'description': {
                'brain': 'Основная модель мозга, центр координат (0,0,0)',
                'tumor': 'Опухоль, позиция относительно центра мозга',
                'skull': 'Череп (в разработке)',
                'arteria': 'Артерии (в разработке)'
            }
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"Metadata exported to {json_path}")
        return json_path