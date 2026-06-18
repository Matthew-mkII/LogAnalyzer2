"""保存済みログ CSV の読み込み"""

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class LogData:
    x: list[float]
    y: list[float]
    source: Path
    total_rows: int
    plotted_rows: int
    last_sample_index: int
    y_column: str = ""
    available_columns: list[str] | None = None


def inspect_log_csv(path: Path | str) -> tuple[str, list[str]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")

    legacy_columns: list[str] | None = None

    with path.open(encoding="utf-8", newline="") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("#"):
                header = _parse_legacy_header_line(stripped)
                if header and header[0] == "time":
                    legacy_columns = header[1:]
                continue

            if stripped.startswith("received_at,"):
                return "app", []

            if legacy_columns is not None:
                return "legacy", legacy_columns

            raise ValueError("未対応の CSV 形式です")

    raise ValueError("CSV にデータ行がありません")


def load_log_csv(path: Path | str, y_column: str | None = None) -> LogData:
    path = Path(path)
    log_format, columns = inspect_log_csv(path)
    if log_format == "app":
        return _load_app_log(path)
    return _load_legacy_log(path, columns, y_column=y_column)


def _parse_legacy_header_line(line: str) -> list[str] | None:
    stripped = line.strip().lstrip("#").strip()
    if not stripped:
        return None
    return [column.strip() for column in stripped.split(",")]


def _load_legacy_log(
    path: Path,
    value_columns: list[str],
    y_column: str | None = None,
) -> LogData:
    if not value_columns:
        raise ValueError("レガシー CSV に数値列がありません")

    selected_column = y_column or ("gyro" if "gyro" in value_columns else value_columns[0])
    if selected_column not in value_columns:
        raise ValueError(f"列 '{selected_column}' は CSV に存在しません")

    times: list[float] = []
    values: list[float] = []
    total_rows = 0
    column_index = value_columns.index(selected_column) + 1

    with path.open(encoding="utf-8", newline="") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            total_rows += 1
            parts = [part.strip() for part in stripped.split(",")]
            if len(parts) <= column_index:
                continue

            try:
                time_ms = float(parts[0])
                value = float(parts[column_index])
            except ValueError:
                continue

            times.append(time_ms)
            values.append(value)

    if not times:
        raise ValueError("グラフ用の数値データがありません")

    time_start = min(times)
    x = [time_ms - time_start for time_ms in times]

    return LogData(
        x=x,
        y=values,
        source=path,
        total_rows=total_rows,
        plotted_rows=len(values),
        last_sample_index=len(values),
        y_column=selected_column,
        available_columns=value_columns,
    )


def _to_elapsed_ms(timestamps: list[datetime]) -> list[float]:
    start = timestamps[0]
    return [(timestamp - start).total_seconds() * 1000 for timestamp in timestamps]


def _load_app_log(path: Path) -> LogData:
    timestamps: list[datetime] = []
    y: list[float] = []
    total_rows = 0
    last_sample_index = 0
    fallback_base: datetime | None = None

    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV にヘッダー行がありません")

        for row in reader:
            total_rows += 1
            parsed = row.get("parsed_value", "").strip()
            if not parsed:
                continue

            try:
                value = float(parsed)
            except ValueError:
                continue

            index_str = row.get("sample_index", "").strip()
            if index_str:
                last_sample_index = max(last_sample_index, int(float(index_str)))

            received_str = row.get("received_at", "").strip()
            if received_str:
                timestamps.append(datetime.fromisoformat(received_str))
            elif timestamps:
                timestamps.append(timestamps[-1] + timedelta(milliseconds=1000))
            else:
                if fallback_base is None:
                    fallback_base = datetime.now()
                timestamps.append(fallback_base)

            y.append(value)

    if not timestamps:
        raise ValueError("グラフ用の数値データがありません")

    return LogData(
        x=_to_elapsed_ms(timestamps),
        y=y,
        source=path,
        total_rows=total_rows,
        plotted_rows=len(y),
        last_sample_index=last_sample_index,
        y_column="parsed_value",
    )
