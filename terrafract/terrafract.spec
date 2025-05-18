# -*- mode: python -*-
import sys
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs
)

block_cipher = None

# entry‐point: your package’s __main__.py
entry_script = "__main__.py"

# 1) Pull in PySide6 plugins and matplotlib data,
#    but let the hooks do the matplotlib part for you.
datas = (
    collect_data_files("PySide6", includes=["plugins/*"])
    # you can drop your manual collect_data_files("matplotlib",…) here
)

# 2) Hidden imports so nothing gets missed
hiddenimports = (
    collect_submodules("PySide6")
  + ["noise._perlin"]
  + ["matplotlib.backends.backend_qtagg", "matplotlib.backends.backend_agg"]
)

# 3) **Collect the actual .pyd/.dll** for NumPy & SciPy
binaries = (
    collect_dynamic_libs("numpy")
  + collect_dynamic_libs("scipy")
)

# 4) Exclude tests & stuff you never use
excludes = [
    "pytest", "test_terrafract", "tomlkit",
    "numpy.tests", "PySide6.scripts.project_lib"
]

a = Analysis(
    [entry_script],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,
    name="TerraFract",
    debug=False,
    strip=False,
    upx=True,
    console=False,   # GUI app
)
