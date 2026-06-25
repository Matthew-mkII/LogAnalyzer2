#!/usr/bin/env python3
"""ログ行フォーマットのみの動作確認（BLE なし）

    python samples/format_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from log_format import format_log_line

# time + 10 列（LogAnalyzer2 推奨形式）
full_line = format_log_line(
    time_ms=315,
    values={
        "turn": -45.0,
        "speed": 10.0,
        "battery": 7971,
        "gyro": 44.0,
    },
)
print("完全行:")
print(full_line, end="")

# 列不足（不足分は LogAnalyzer2 側で null 扱い）
partial_line = format_log_line(values={"gyro": 23.5})
print("列不足行:")
print(partial_line, end="")
