"""PyInstaller 実行時: Qt WebEngine プロセスのパスを設定"""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    root = Path(sys._MEIPASS)
    framework_root = root / "PySide6" / "Qt" / "lib" / "QtWebEngineCore.framework"
    candidates = [
        root / "PySide6" / "QtWebEngineProcess.exe",
        root / "PySide6" / "QtWebEngineProcess",
        framework_root
        / "Helpers"
        / "QtWebEngineProcess.app"
        / "Contents"
        / "MacOS"
        / "QtWebEngineProcess",
        framework_root
        / "Versions"
        / "A"
        / "Helpers"
        / "QtWebEngineProcess.app"
        / "Contents"
        / "MacOS"
        / "QtWebEngineProcess",
        framework_root
        / "Versions"
        / "Current"
        / "Helpers"
        / "QtWebEngineProcess.app"
        / "Contents"
        / "MacOS"
        / "QtWebEngineProcess",
    ]
    for candidate in candidates:
        if candidate.is_file():
            os.environ["QTWEBENGINEPROCESS_PATH"] = str(candidate)
            break
