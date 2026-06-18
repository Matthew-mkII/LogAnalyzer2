# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for LogAnalyzer2
#
# Windows で exe を生成:
#   pyinstaller LogAnalyzer2.spec
#
# 出力: dist/LogAnalyzer2/LogAnalyzer2.exe （フォルダ配布形式）

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pyside6_binaries,
    datas=pyside6_datas,
    hiddenimports=[
        "qasync",
        "plotly",
        "plotly.graph_objects",
        "plotly.io",
        "plotly.validators",
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
    name="LogAnalyzer2",
)
