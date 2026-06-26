"""LogAnalyzer2 向けログ行のフォーマット"""

from __future__ import annotations

VALUE_COLUMNS = (
    "turn",
    "speed",
    "battery",
    "angleL",
    "angleR",
    "bright",
    "Kp",
    "Ki",
    "Kd",
    "roll",
    "yaw",
    "pitch",
)


def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}"


def format_log_line(
    *,
    time_ms: float | None = None,
    values: dict[str, float | None] | None = None,
) -> str:
    """1 レコード分のログ行を生成する（末尾に改行付き）。

    time_ms を指定すると「time + 12 データ列」の 13 列形式になる。
    省略すると「12 データ列」のみ（LogAnalyzer2 側で受信時刻から time を補完）。
    """
    row_values = values or {}
    fields: list[str] = []

    if time_ms is not None:
        fields.append(format_number(time_ms))

    for column in VALUE_COLUMNS:
        value = row_values.get(column)
        fields.append("" if value is None else format_number(value))

    return ",".join(fields) + "\n"


def iter_notify_chunks(data: bytes, chunk_size: int = 20) -> list[bytes]:
    """BLE notify 用にバイト列を分割する（MTU を考慮）。"""
    if not data:
        return []
    return [data[index : index + chunk_size] for index in range(0, len(data), chunk_size)]
