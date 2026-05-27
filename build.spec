# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

# Базовый анализ
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('convertation', 'convertation'),
        ('segmentation', 'segmentation'),
    ],
    hiddenimports=[
        # ВСТРОЕННЫЕ МОДУЛИ PYTHON
        'uuid', 'abc', 'atexit', 'base64', 'binascii', 'calendar', 'cmath',
        'collections', 'contextlib', 'copy', 'copyreg', 'datetime', 'enum',
        'functools', 'glob', 'hashlib', 'heapq', 'inspect', 'io', 'itertools',
        'json', 'logging', 'math', 'numbers', 'operator', 'os', 'pathlib',
        'pickle', 'posixpath', 'pprint', 'random', 're', 'reprlib', 'shutil',
        'signal', 'stat', 'string', 'struct', 'subprocess', 'sys', 'threading',
        'time', 'traceback', 'types', 'unittest', 'unittest.mock', 'warnings',
        'weakref', 'zipfile', 'zlib', '_collections_abc', '_weakrefset',
        
        # ====== ВСЕ БИБЛИОТЕКИ ИЗ pyproject.toml ======
        'attrs', 'certifi', 'charset_normalizer', 'colorama', 'contourpy',
        'cycler', 'cyclopts', 'docstring_parser', 'docutils', 'fontTools',
        'idna', 'imageio', 'kiwisolver', 'lazy_loader', 'markdown_it',
        'matplotlib', 'mdurl', 'networkx', 'numpy', 'packaging', 'pillow',
        'platformdirs', 'pooch', 'pygments', 'pyparsing', 'pyqtgraph',
        'PySide6', 'PySide6_addons', 'PySide6_essentials', 'python_dateutil',
        'pyvista', 'pyvistaqt', 'QtPy', 'requests', 'rich', 'rich_rst',
        'scikit_image', 'scipy', 'scipy_stubs', 'scooby', 'shiboken6',
        'simpleITK', 'six', 'tifffile', 'typing_extensions', 'urllib3', 'vtk',
        
        # ====== КОНКРЕТНЫЕ ПОДМОДУЛИ ======
        # PySide6
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtNetwork', 'PySide6.QtSvg', 'PySide6.QtPrintSupport',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebChannel', 'PySide6.QtQuick',
        'PySide6.QtQml', 'PySide6.QtQuickWidgets',
        
        # SimpleITK (ВАЖНО!)
        'SimpleITK', 'SimpleITK._SimpleITK', 'SimpleITK.extra',
        
        # VTK
        'vtk', 'vtkmodules', 'vtkmodules.all',
        'vtkmodules.vtkCommonCore', 'vtkmodules.vtkCommonDataModel',
        'vtkmodules.vtkFiltersCore', 'vtkmodules.vtkFiltersSources',
        'vtkmodules.vtkRenderingCore', 'vtkmodules.vtkRenderingOpenGL2',
        'vtkmodules.vtkRenderingVolumeOpenGL2', 'vtkmodules.vtkIOImage',
        'vtkmodules.vtkIOLegacy', 'vtkmodules.vtkInteractionStyle',
        'vtkmodules.vtkInteractionWidgets', 'vtkmodules.vtkImagingCore',
        
        # NumPy
        'numpy', 'numpy.core._multiarray_umath', 'numpy.random._generator',
        'numpy.fft', 'numpy.linalg', 'numpy.polynomial', 'numpy.ma',
        'numpy.ctypeslib', 'numpy.distutils',
        
        # SciPy
        'scipy', 'scipy.special', 'scipy.special._ufuncs', 'scipy.sparse',
        'scipy.sparse.csgraph', 'scipy.linalg', 'scipy.linalg.cython_blas',
        'scipy.linalg.cython_lapack', 'scipy.optimize', 'scipy.ndimage',
        'scipy.stats', 'scipy.interpolate', 'scipy.integrate', 'scipy.fft',
        
        # Matplotlib
        'matplotlib', 'matplotlib.backends', 'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qt5', 'matplotlib.pyplot', 'matplotlib._image',
        'matplotlib._path', 'matplotlib._tri', 'mpl_toolkits',
        
        # Scikit-image
        'skimage', 'skimage._shared', 'skimage.feature', 'skimage.filters',
        'skimage.graph', 'skimage.measure', 'skimage.morphology',
        'skimage.restoration', 'skimage.transform', 'skimage.segmentation',
        'skimage.color', 'skimage.exposure', 'skimage.io',
        
        # PyVista
        'pyvista', 'pyvista.plotting', 'pyvista.plotting.renderer',
        'pyvista.plotting.plotter', 'pyvista.core', 'pyvista.core._vtk_core',
        'pyvista.core.filters', 'pyvista.utilities', 'pyvistaqt',
        
        # PyQtGraph
        'pyqtgraph', 'pyqtgraph.graphicsItems', 'pyqtgraph.widgets',
        'pyqtgraph.opengl', 'pyqtgraph.parametertree', 'pyqtgraph.exporters',
        
        # ImageIO
        'imageio', 'imageio.plugins', 'imageio.core', 'imageio.v2', 'imageio.v3',
        
        # Pillow
        'PIL', 'PIL.Image', 'PIL.ImageQt', 'PIL.ImageTk', 'PIL._imaging',
        'PIL._imagingft', 'PIL._imagingtk', 'PIL._webp', 'PIL._avif',
        
        # Tifffile
        'tifffile', 'tifffile._imagecodecs',
        
        # Другие
        'cycler', 'kiwisolver', 'kiwisolver._cext', 'pyparsing',
        'packaging', 'packaging.specifiers', 'packaging.version',
        'packaging.requirements', 'markdown_it', 'markdown_it.main',
        'rich', 'rich.console', 'rich.traceback', 'rich.table',
        'pygments', 'pygments.lexers', 'pygments.styles',
        'docutils', 'docutils.parsers.rst', 'docutils.writers.html4css1',
        'dateutil', 'dateutil.parser', 'dateutil.tz',
        'requests', 'urllib3', 'urllib3.poolmanager', 'certifi',
        'charset_normalizer', 'idna', 'colorama', 'platformdirs', 'pooch',
        'scooby', 'cyclopts', 'docstring_parser', 'typing_extensions', 'six',
        'lazy_loader', 'fontTools', 'fontTools.ttLib', 'networkx',
        'contourpy', 'contourpy._contourpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'tcl', 'test', 'tests', 'unittest.__pycache__'],
    noarchive=False,
)

# Функция для добавления данных из пакета
def add_package_resources(package_name):
    try:
        # Добавляем файлы данных
        datas = collect_data_files(package_name, include_py_files=True)
        for src, dest in datas:
            a.datas.append((src, dest, 'DATA'))
        
        # Добавляем динамические библиотеки
        libs = collect_dynamic_libs(package_name)
        for src, dest in libs:
            a.binaries.append((src, dest, 'BINARY'))
            
        print(f"✓ Ресурсы добавлены: {package_name}")
        return True
    except Exception as e:
        print(f"⚠ Ошибка с {package_name}: {e}")
        return False

# Добавляем ВСЕ пакеты с их ресурсами
all_packages = [
    'PySide6', 'shiboken6', 'vtkmodules', 'numpy', 'scipy', 'skimage',
    'matplotlib', 'pyvista', 'pyvistaqt', 'pyqtgraph', 'SimpleITK',
    'PIL', 'tifffile', 'imageio', 'networkx', 'fontTools', 'contourpy',
    'cycler', 'kiwisolver', 'packaging', 'pyparsing', 'markdown_it',
    'mdurl', 'rich', 'rich_rst', 'pygments', 'docutils', 'dateutil',
    'certifi', 'charset_normalizer', 'idna', 'requests', 'urllib3',
    'colorama', 'platformdirs', 'pooch', 'scooby', 'cyclopts',
    'docstring_parser', 'attrs', 'typing_extensions', 'six', 'lazy_loader',
]

for package in all_packages:
    add_package_resources(package)
    try:
        modules = collect_submodules(package)
        a.hiddenimports.extend(modules)
    except:
        pass

# Удаляем дубликаты
a.hiddenimports = list(set(a.hiddenimports))
a.datas = list(set(a.datas))
a.binaries = list(set(a.binaries))

print(f"\n📊 ИТОГО:")
print(f"  - Скрытых импортов: {len(a.hiddenimports)}")
print(f"  - Файлов данных: {len(a.datas)}")
print(f"  - Бинарных файлов: {len(a.binaries)}")

# Создаем PYZ архив
pyz = PYZ(a.pure)

# Конфигурация для одного EXE файла
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SwissSkullUtil_v3.0.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

print("\n✅ Сборка завершена!")