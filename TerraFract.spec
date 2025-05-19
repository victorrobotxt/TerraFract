# terrafract_onefile.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)

block_cipher = None
proj = os.path.abspath(".")

entry_script = os.path.join("terrafract", "__main__.py")

# 1) Qt plugins + matplotlib data
datas  = collect_data_files("PySide6", includes=["plugins/*"])
datas += collect_data_files("matplotlib", includes=["mpl-data/*"])

# 2) Any hidden‐imported bits
hiddenimports  = collect_submodules("PySide6")
hiddenimports += collect_submodules("numba")
hiddenimports += ["noise._perlin","noise._simplex","noise._openSimplex2"]

# 3) Native DLLs for numpy/scipy/numba
binaries  = collect_dynamic_libs("numpy")
binaries += collect_dynamic_libs("scipy")
binaries += collect_dynamic_libs("numba")

# 4) Shrink it by excluding unused backends & test libs
excludes = [
    "PyQt5","PyQt6","PySide2",
    "tkinter","pytest","tests",
    "tomlkit","PySide6.scripts.project_lib",
]

# ── Build graph ───────────────────────────────────────
a = Analysis(
    [entry_script],
    pathex=[proj],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── One-file EXE (no COLLECT) ─────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="TerraFract",
    debug=False,
    strip=False,
    upx=True,
    console=False,            # GUI app
    icon=os.path.join(proj, "terrafract.ico"),
)
