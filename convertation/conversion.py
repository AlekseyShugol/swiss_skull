import sys
import numpy as np
import SimpleITK as sitk
import pyvista as pv
from skimage import measure, morphology
from scipy import ndimage


# ==================== ЛОГИКА (ЧИСТАЯ, БЕЗ UI) ====================
class BrainCleanerLogic:
    """Чистая логика обработки медицинских 3D-данных."""

    def __init__(self):
        self.full_volume = None
        self.spacing = (1.0, 1.0, 1.0)
        self.last_mesh = None

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

        # Сначала центрируем (если нужно)
        if center_model:
            center = mesh.center
            mesh.points = mesh.points - center

        # Затем меняем оси местами
        points = mesh.points.copy()
        mesh.points[:, 0] = points[:, 2]  # X <- Z (left-right)
        mesh.points[:, 1] = points[:, 0]  # Y <- X (superior-inferior, вверх)
        mesh.points[:, 2] = points[:, 1]  # Z <- Y (anterior-posterior, вперёд)

        # Поднимаем модель, чтобы она стояла на "полу" (Y=0)
        min_y = mesh.points[:, 1].min()
        if min_y < 0:
            mesh.points[:, 1] = mesh.points[:, 1] - min_y

        # Центрируем по X и Z
        mesh.points[:, 0] = mesh.points[:, 0] - mesh.points[:, 0].mean()
        mesh.points[:, 2] = mesh.points[:, 2] - mesh.points[:, 2].mean()

        print(f"Fixed bounds: {mesh.bounds}")
        return mesh

    def generate_mesh(self, roi_pos, roi_size, threshold_value, min_island_size,
                      keep_largest, sigma_value, smooth_iterations, center_model):
        """Основной метод генерации 3D-модели."""
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

        # 1. Порог
        mask = vol > threshold_value
        if not np.any(mask):
            raise ValueError("No voxels above threshold")

        # 2. Морфология
        try:
            mask = morphology.binary_opening(mask, morphology.ball(2))
            mask = morphology.binary_closing(mask, morphology.ball(1))
        except Exception as e:
            print(f"Morphology warning: {e}")

        if not np.any(mask):
            raise ValueError("Mask became empty after morphological operations")

        # 3. Удаление мусора
        if keep_largest:
            labels = measure.label(mask)
            if labels.max() == 0:
                raise ValueError("No objects found in mask")
            counts = np.bincount(labels.flat)
            if len(counts) <= 1:
                raise ValueError("Only background found")
            largest_label = np.argmax(counts[1:]) + 1
            mask = (labels == largest_label)
        else:
            mask = morphology.remove_small_objects(mask, min_size=min_island_size)

        if not np.any(mask):
            raise ValueError("No objects remain after cleanup")

        # 4. Создание плавной маски
        smooth_mask = mask.astype(np.float32)
        if sigma_value > 0:
            smooth_mask = ndimage.gaussian_filter(smooth_mask, sigma=sigma_value)
            smooth_mask = np.clip((smooth_mask - 0.3) / 0.5, 0, 1)

        # 5. Marching Cubes
        spacing_x, spacing_y, spacing_z = self.spacing

        need_padding = (np.any(mask[0, :, :]) or np.any(mask[-1, :, :]) or
                        np.any(mask[:, 0, :]) or np.any(mask[:, -1, :]) or
                        np.any(mask[:, :, 0]) or np.any(mask[:, :, -1]))

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
            raise ValueError("Generated mesh has no vertices")

        # 6. Сборка меша
        faces_pv = np.hstack([np.full((len(faces), 1), 3), faces])
        mesh = pv.PolyData(verts, faces_pv)

        # 7. Сглаживание
        if smooth_iterations > 0:
            mesh = mesh.smooth(n_iter=smooth_iterations, relaxation_factor=0.5,
                               feature_smoothing=False, boundary_smoothing=True, convergence=0.0)
            if smooth_iterations > 30:
                mesh = mesh.smooth(n_iter=int(smooth_iterations * 0.3), relaxation_factor=0.3,
                                   feature_smoothing=False, boundary_smoothing=True)

        # 8. Ориентация и центрирование
        mesh = self.fix_orientation_and_center(mesh, center_model)

        self.last_mesh = mesh
        return mesh

    def export_model(self, path):
        """Экспорт модели в файл."""
        if self.last_mesh is None:
            raise ValueError("No mesh to export")

        if path.endswith('.obj'):
            self.last_mesh.save(path, binary=False)
        elif path.endswith('.stl') or path.endswith('.ply'):
            self.last_mesh.save(path, binary=True)
        else:
            if '.' not in path:
                path += '.obj'
                self.last_mesh.save(path, binary=False)
            else:
                self.last_mesh.save(path)