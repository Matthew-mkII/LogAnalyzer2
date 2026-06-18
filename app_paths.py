"""開発環境・PyInstaller 実行ファイル化後の共通パス"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_base_dir() -> Path:
    """ログ CSV や temp.html を置く書き込み可能な基準ディレクトリ。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def logs_dir() -> Path:
    path = app_base_dir() / "logs"
    path.mkdir(exist_ok=True)
    return path


def temp_html_path() -> Path:
    return app_base_dir() / "temp.html"
