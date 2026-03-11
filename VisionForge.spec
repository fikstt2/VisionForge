# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = os.path.abspath(".")

# -------------------------
# DATA FILES
# -------------------------

datas = []

datas += collect_data_files("matplotlib")
datas += collect_data_files("PIL")
datas += collect_data_files("ultralytics")

# добавляем torch/lib вручную
import torch
torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")

if os.path.exists(torch_lib):
    for f in os.listdir(torch_lib):
        datas.append((os.path.join(torch_lib, f), "torch/lib"))

# -------------------------
# HIDDEN IMPORTS
# -------------------------

hiddenimports = []

hiddenimports += collect_submodules("torch")
hiddenimports += collect_submodules("torchvision")
hiddenimports += collect_submodules("ultralytics")
hiddenimports += collect_submodules("cv2")

hiddenimports += [
    "matplotlib.backends.backend_qt5agg",
]

# -------------------------
# ANALYSIS
# -------------------------

a = Analysis(
    ["ui/launcher.py"],
    pathex=[project_root],

    binaries=[],
    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[],

    hooksconfig={
        "matplotlib": {"backends": "Qt5Agg"}
    },

    excludes=[
        "tkinter",
        "test",
        "distutils",
        "setuptools",
        "IPython",
        "jupyter",
        "notebook"
    ],

    noarchive=False
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],

    name="VisionForge",

    debug=False,
    bootloader_ignore_signals=False,

    strip=False,
    upx=False,

    console=True,

    icon="icon.ico" if os.path.exists("icon.ico") else None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,

    strip=False,
    upx=False,

    name="VisionForge"
)