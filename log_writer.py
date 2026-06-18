"""Bluetooth 受信ログのファイル出力（レガシー CSV 形式）"""

from datetime import datetime
from pathlib import Path

LEGACY_VALUE_COLUMNS = (
    "turn",
    "speed",
    "battery",
    "angleL",
    "angleR",
    "bright",
    "gyro",
    "Kp",
    "Ki",
    "Kd",
)

LEGACY_ROW_COLUMN_COUNT = len(LEGACY_VALUE_COLUMNS)


def _parse_optional_float(raw: str) -> float | None:
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def parse_legacy_row(line: str) -> tuple[float | None, dict[str, float | None]]:
    """Bluetooth 受信行をレガシー CSV のデータ列として解釈する。

    列数不足・数値変換不可の項目は None として扱う。

    Returns:
        (device_time_ms, values)
        device_time_ms は先頭に time 列が含まれる場合のみ設定される。
    """
    stripped = line.strip()
    if not stripped:
        return None, {column: None for column in LEGACY_VALUE_COLUMNS}

    parts = [part.strip() for part in stripped.split(",")]

    if len(parts) >= LEGACY_ROW_COLUMN_COUNT + 1:
        device_time = _parse_optional_float(parts[0])
        value_parts = parts[1 : LEGACY_ROW_COLUMN_COUNT + 1]
    else:
        device_time = None
        value_parts = parts[:LEGACY_ROW_COLUMN_COUNT]

    while len(value_parts) < LEGACY_ROW_COLUMN_COUNT:
        value_parts.append("")

    values = {
        column: _parse_optional_float(raw_value)
        for column, raw_value in zip(LEGACY_VALUE_COLUMNS, value_parts, strict=True)
    }
    return device_time, values


class LogWriter:
    def __init__(self, log_dir: str = "logs") -> None:
        self._log_dir = Path(log_dir)
        self._file = None
        self._path: Path | None = None

    def start(self) -> Path:
        self._log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = self._log_dir / f"log_{timestamp}.csv"
        self._file = self._path.open("w", encoding="utf-8", newline="")
        self._write_header()
        self._file.flush()
        return self._path

    def _write_header(self) -> None:
        if self._file is None:
            return

        column_names = ", ".join(["time", *LEGACY_VALUE_COLUMNS])
        self._file.write("# THRESHOLD= 0.000000\n")
        self._file.write("# Speed = 0.000000; Proportional = 0.000000; Integral = 0.000000\n")
        self._file.write(f"# {column_names}\n")

    @staticmethod
    def _format_time(time_ms: float) -> str:
        if float(time_ms).is_integer():
            return str(int(time_ms))
        return f"{time_ms:.6f}"

    @staticmethod
    def _format_value(value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:.6f}"

    def write(self, elapsed_ms: float, values: dict[str, float | None] | None = None) -> None:
        if self._file is None:
            return

        row_values = values or {}
        fields = [self._format_time(elapsed_ms)]
        for column in LEGACY_VALUE_COLUMNS:
            fields.append(self._format_value(row_values.get(column)))

        self._file.write(",".join(fields) + "\n")
        self._file.flush()

    def stop(self) -> Path | None:
        path = self._path
        if self._file is not None:
            self._file.close()
            self._file = None
        self._path = None
        return path

    @property
    def is_active(self) -> bool:
        return self._file is not None

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def columns(self) -> tuple[str, ...]:
        return ("time", *LEGACY_VALUE_COLUMNS)
