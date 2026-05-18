from PySide6.QtCore import QThread, Signal
import SimpleITK as sitk
import numpy as np

class SkullStripper(QThread):
    progress = Signal(str)
    iteration_update = Signal(int)
    finished = Signal(object, object)

    def __init__(self, patient_sitk, atlas_path, mask_path, error_value=1e-20, iteration_value=1000):
        super().__init__()
        self.patient_raw = patient_sitk
        self.atlas_path = atlas_path
        self.mask_path = mask_path
        self._error_value = error_value
        self._iteration_value = iteration_value

    def run(self):
        try:
            self.progress.emit("Этап 1: Подготовка данных...")

            fixed = sitk.DICOMOrient(self.patient_raw, 'LPS')
            spacing = [1, 1, 1]
            new_size = [int(round(sz * sp / nsp)) for sz, sp, nsp in zip(fixed.GetSize(), fixed.GetSpacing(), spacing)]
            fixed = sitk.Resample(fixed, new_size, sitk.Transform(), sitk.sitkLinear,
                                  fixed.GetOrigin(), spacing, fixed.GetDirection(), 0.0)
            fixed = sitk.Cast(fixed, sitk.sitkFloat32)

            moving = sitk.Cast(sitk.ReadImage(self.atlas_path), sitk.sitkFloat32)
            moving = sitk.DICOMOrient(moving, 'LPS')
            moving_mask = sitk.Cast(
                sitk.DICOMOrient(
                    sitk.ReadImage(self.mask_path),
                    'LPS'),
                sitk.sitkFloat32
            )

            self.progress.emit("Этап 2: Аффинное совмещение (поиск углов)...")
            reg = sitk.ImageRegistrationMethod()
            reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
            reg.SetOptimizerAsGradientDescent(
                learningRate=1.0,
                numberOfIterations=self._iteration_value,
                convergenceMinimumValue=self._error_value,
                convergenceWindowSize=20
            )

            def iteration_callback():
                try:
                    current_iteration = reg.GetOptimizerIteration()
                    self.iteration_update.emit(current_iteration + 1)
                except:
                    pass

            reg.AddCommand(sitk.sitkIterationEvent, iteration_callback)
            reg.SetOptimizerScalesFromPhysicalShift()
            tx = sitk.CenteredTransformInitializer(
                fixed,
                moving,
                sitk.AffineTransform(3),
                sitk.CenteredTransformInitializerFilter.GEOMETRY
            )
            reg.SetInitialTransform(tx)
            reg.SetInterpolator(sitk.sitkLinear)
            final_tx = reg.Execute(fixed, moving)

            self.progress.emit("Этап 3: Наложение маски...")
            mask_res = sitk.Resample(moving_mask, fixed, final_tx, sitk.sitkNearestNeighbor, 0.0)
            mask_res = sitk.BinaryThreshold(mask_res, lowerThreshold=0.5)

            img_arr = sitk.GetArrayFromImage(fixed)
            msk_arr = sitk.GetArrayFromImage(mask_res)

            self.finished.emit(img_arr, msk_arr)

        except Exception as e:
            self.progress.emit(f"Критическая ошибка: {str(e)}")