import torch
from PySide6.QtCore import *
import SimpleITK as sitk
import numpy as np

# Определяем устройство для вычислений: GPU (cuda), если доступно, иначе CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Класс потока для обработки данных, чтобы интерфейс (GUI) не зависал во время расчетов
class SkullStripper(QThread):
    progress = Signal(str)  # Сигнал для отправки текстовых сообщений о прогрессе в GUI
    finished = Signal(object, object)  # Сигнал окончания работы, передает обработанное изображение и маску

    def __init__(self, patient_sitk, atlas_path, mask_path):
        super().__init__()
        self.patient_raw = patient_sitk  # Исходный снимок пациента (объект SimpleITK)
        self.atlas_path = atlas_path    # Путь к эталонному изображению (атласу)
        self.mask_path = mask_path      # Путь к маске мозга для этого атласа

    def run(self):
        try:
            self.progress.emit("Этап 1: Подготовка данных...")
            # Приведение ориентации пациента к стандарту LPS (Left-Posterior-Superior) для корректной анатомии
            fixed = sitk.DICOMOrient(self.patient_raw, 'LPS')
            # Установка изотропного шага пикселей (1мм x 1мм x 1мм) для стандартизации масштаба
            spacing = [0.9, 0.9, 0.9]
            '''
            fixed.GetSize(): возвращает размеры изображения в пикселях по каждой оси
            fixed.GetSpacing(): возвращает текущий размер вокселя
            spacing: задаёт новый размер вокселя
            '''
            # Вычисление нового размера изображения в пикселях на основе нового шага (spacing)
            new_size = [int(round(sz * sp / nsp)) for sz, sp, nsp in zip(fixed.GetSize(), fixed.GetSpacing(), spacing)]
            # Ресемплирование: пересчет сетки изображения под стандарт 1мм
            fixed = sitk.Resample(fixed, new_size, sitk.Transform(), sitk.sitkLinear,
                                  fixed.GetOrigin(), spacing, fixed.GetDirection(), 0.0)
            # Приведение типа данных к Float32 для математических операций регистрации
            fixed = sitk.Cast(fixed, sitk.sitkFloat32)

            # Загрузка атласа и его маски, приведение их к той же ориентации LPS и типу Float32
            moving = sitk.Cast(sitk.ReadImage(self.atlas_path), sitk.sitkFloat32)
            moving = sitk.DICOMOrient(moving, 'LPS')
            moving_mask = sitk.Cast(
                sitk.DICOMOrient(
                    sitk.ReadImage(self.mask_path),
                    'LPS'),
                sitk.sitkFloat32
            )

            self.progress.emit("Этап 2: Аффинное совмещение (поиск углов)...")
            # Создание объекта метода регистрации (совмещения) двух изображений
            reg = sitk.ImageRegistrationMethod()
            # Настройка метрики: Взаимная информация (Mattes Mutual Information) — идеальна для разных модальностей
            reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
            # Настройка оптимизатора: Градиентный спуск для поиска минимума ошибки
            reg.SetOptimizerAsGradientDescent(learningRate=1.0, numberOfIterations=100, convergenceMinimumValue=1e-6,
                                              convergenceWindowSize=10)
            # Автоматическое масштабирование шагов оптимизатора на основе физических сдвигов
            reg.SetOptimizerScalesFromPhysicalShift()

            # Инициализация трансформации: совмещение центров масс или геометрических центров
            # (AffineTransform — вращение, сдвиг, масштаб)
            tx = sitk.CenteredTransformInitializer(fixed, moving, sitk.AffineTransform(3),
                                                   sitk.CenteredTransformInitializerFilter.GEOMETRY)
            reg.SetInitialTransform(tx) # Установка начальной позиции
            reg.SetInterpolator(sitk.sitkLinear) # Линейная интерполяция при трансформации

            # Запуск процесса регистрации: ищем матрицу, которая наложит атлас на пациента
            final_tx = reg.Execute(fixed, moving)

            self.progress.emit("Этап 3: Наложение маски на GPU...")
            # Применение найденной трансформации к маске атласа, чтобы она "наделась" на голову пациента
            mask_res = sitk.Resample(moving_mask, fixed, final_tx, sitk.sitkNearestNeighbor, 0.0)
            # Бинаризация: превращаем маску в четкие 0 (не мозг) и 1 (мозг)
            mask_res = sitk.BinaryThreshold(mask_res, lowerThreshold=0.5)

            # Преобразование объектов SimpleITK в массивы NumPy для передачи в PyTorch
            img_arr = sitk.GetArrayFromImage(fixed)
            msk_arr = sitk.GetArrayFromImage(mask_res)

            # Перенос данных на видеокарту (или CPU) для ускорения дальнейших расчетов (например, сегментации)
            img_t = torch.from_numpy(img_arr).to(device)
            msk_t = torch.from_numpy(msk_arr.astype(np.float32)).to(device)

            # Возвращаем результат обратно в главный поток интерфейса
            self.finished.emit(img_t.cpu().numpy(), msk_t.cpu().numpy())

        except Exception as e:
            self.progress.emit(f"Критическая ошибка: {str(e)}")