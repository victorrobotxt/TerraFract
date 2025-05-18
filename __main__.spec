# terrafract.spec
# -*- mode: python -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# make sure PyInstaller sees your terrafract package
pathex = [ os.getcwd() ]

# 1) entry‐point: the __main__.py inside terrafract/
entry_script = os.path.join("terrafract", "__main__.py")

# 2) grab ALL of PySide6 (QtCore, QtWidgets, etc.)
hiddenimports = collect_submodules("PySide6")

# 3) grab the Qt plugins (platforms/imageformats...)
datas = collect_data_files("PySide6", includes=["plugins/*"])

a = Analysis(
    [ entry_script ],
    pathex=pathex,
    binaries=[],
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
    name="TerraFract",
    debug=False,
    strip=False,
    upx=True,
    console=False,   # GUI app
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="TerraFract",
)
