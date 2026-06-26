#!/usr/bin/env python3
"""ログ行フォーマットのみの動作確認（BLE なし）

    python samples/format_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from log_format import format_log_line

full_line = format_log_line(
    time_ms=315,
    values={
        "turn": -45.0,
        "speed": 10.0,
        "battery": 7971,
        "gyro": 44.0,
        "roll": 2.5,
        "yaw": -12.0,
        "pitch": 1.25,
    },
)
print("完全行:")
print(full_line, end="")

partial_line = format_log_line(values={"gyro": 23.5, "yaw": 10.0})
print("列不足行:")
print(partial_line, end="")
