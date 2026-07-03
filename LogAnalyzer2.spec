# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for LogAnalyzer2
#
# ビルド:
#   Windows: build_windows.bat  または  pyinstaller --distpath dist/LogAnalyzer2 LogAnalyzer2.spec
#   macOS:   build_macos.sh      または  pyinstaller --distpath dist/LogAnalyzer2 LogAnalyzer2.spec
#
# 出力:
#   Windows: dist/LogAnalyzer2/win/LogAnalyzer2.exe
#   macOS:   dist/LogAnalyzer2/mac/LogAnalyzer2

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

spec_dir = os.path.dirname(os.path.abspath(SPEC))
distpath = os.path.join(spec_dir, "dist", "LogAnalyzer2")
bundle_subdir = "win" if sys.platform == "win32" else "mac"

block_cipher = None

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pyside6_binaries,
    datas=pyside6_datas + [(os.path.join(spec_dir, "plotly.min.js"), ".")],
    hiddenimports=[
        "qasync",
        "plotly",
        "plotly.graph_objects",
        "plotly.io",
        "plotly.validators",
        "kaleido",
        "choreographer",
        *pyside6_hiddenimports,
        *collect_submodules("bleak"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["runtime_hook_qtwebengine.py"],
    excludes=["PyQt6", "PyQt5", "tkinter", "matplotlib", "IPython"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LogAnalyzer2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=bundle_subdir,
)
