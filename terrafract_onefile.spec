# terrafract_onefile.spec
# -*- mode: python -*-

import os, sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE

# 1. Pull in every PySide6 submodule (QtWidgets, QtCore, etc.)
hiddenimports = collect_submodules('PySide6') \
               + ['noise._perlin', 'noise._simplex', 'noise._openSimplex2']

# 2. Copy the entire Qt plugins folder (platforms, imageformats, etc.)
datas = collect_data_files('PySide6', includes=['plugins/*'])

# 3. Manually include your python3x DLL
#    sys.base_prefix points at your Python install (where python310.dll lives).
python_dll = os.path.join(
    sys.base_prefix,
    f"python{sys.version_info.major}{sys.version_info.minor}.dll"
)
binaries = [(python_dll, ".")]

a = Analysis(
    ['terrafract/__main__.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,    # archive the pure Python into the EXE
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    name='TerraFract',
    onefile=True,       # single‐file bundle
    windowed=True,      # no console window
)
