from PySide6.QtCore import QThread, Signal
import SimpleITK as sitk
from logger.logger import log

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
        self._numberOfHistogramBins = 50

    def run(self):
        try:
            self.progress.emit("Этап 1: Подготовка данных...")
            log.info("call func run")
            log.separator()
            log.info("stage 1: preparing")

            fixed = sitk.DICOMOrient(self.patient_raw, 'LPS')
            log.info(f"stage 1: fixed: {fixed}")
            spacing = [1, 1, 1]
            new_size = [int(round(sz * sp / nsp)) for sz, sp, nsp in zip(fixed.GetSize(), fixed.GetSpacing(), spacing)]
            log.info(f"stage 1: new_size: {new_size}")
            fixed = sitk.Resample(fixed, new_size, sitk.Transform(), sitk.sitkLinear,
                                  fixed.GetOrigin(), spacing, fixed.GetDirection(), 0.0)
            log.info(f"stage 1: fixed: {fixed}")
            fixed = sitk.Cast(fixed, sitk.sitkFloat32)
            log.info(f"stage 1: fixed: {fixed}")

            moving = sitk.Cast(sitk.ReadImage(self.atlas_path), sitk.sitkFloat32)
            log.info(f"stage 1: moving: {moving}")
            moving = sitk.DICOMOrient(moving, 'LPS')
            log.info(f"stage 1: moving: {moving}")
            moving_mask = sitk.Cast(
                sitk.DICOMOrient(
                    sitk.ReadImage(self.mask_path),
                    'LPS'),
                sitk.sitkFloat32
            )
            log.info(f"stage 1: moving mask: {moving_mask}")

            self.progress.emit("Этап 2: Аффинное совмещение (поиск углов)...")
            log.separator()
            log.info("stage 2: affine mathing")
            reg = sitk.ImageRegistrationMethod()
            log.info(f"stage 2: affine mathing. reg: {reg}")
            reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=self._numberOfHistogramBins)
            log.info(f"stage 2: affine mathing.numberOfHistogramBins: {self._numberOfHistogramBins}")
            log.info(f"stage 2: affine mathing. reg: {reg}")
            reg.SetOptimizerAsGradientDescent(
                learningRate=1.0,
                numberOfIterations=self._iteration_value,
                convergenceMinimumValue=self._error_value,
                convergenceWindowSize=20
            )

            def iteration_callback():
                log.info("iteration callback function called")
                try:
                    current_iteration = reg.GetOptimizerIteration()
                    log.info(f"iteration callback function returned: {current_iteration}")
                    self.iteration_update.emit(current_iteration + 1)
                except:
                    log.info("iteration callback function did not return an integer")
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
            log.separator()
            log.info("stage 3: masking")
            mask_res = sitk.Resample(moving_mask, fixed, final_tx, sitk.sitkNearestNeighbor, 0.0)
            log.info(f"stage 3: mask_res: {mask_res}")
            mask_res = sitk.BinaryThreshold(mask_res, lowerThreshold=0.5)
            log.info(f"stage 3: mask_res: {mask_res}")

            img_arr = sitk.GetArrayFromImage(fixed)
            msk_arr = sitk.GetArrayFromImage(mask_res)

            self.finished.emit(img_arr, msk_arr)
            log.separator()

        except Exception as e:
            log.error(e)
            self.progress.emit(f"Критическая ошибка: {str(e)}")