# terrafract.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

# 1) Gather all of PySide6 (code + plugins)
datas, binaries, hiddenimports = collect_all('PySide6')
# 2) Also include NumPy/SciPy shared libs
binaries += collect_dynamic_libs('numpy') + collect_dynamic_libs('scipy')

a = Analysis(
    ['terrafract/__main__.py'],
    pathex=[os.path.abspath('.')], 
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TerraFract',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='TerraFract',
)
