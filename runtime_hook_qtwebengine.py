"""PyInstaller 実行時: Qt WebEngine プロセスのパスを設定"""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    root = Path(sys._MEIPASS)
    for name in ("QtWebEngineProcess.exe", "QtWebEngineProcess"):
        candidate = root / "PySide6" / name
        if candidate.is_file():
            os.environ["QTWEBENGINEPROCESS_PATH"] = str(candidate)
            break
