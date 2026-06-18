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


def _to_elapsed_ms(timestamps: list[datetime]) -> list[float]:
    start = timestamps[0]
    return [(timestamp - start).total_seconds() * 1000 for timestamp in timestamps]


def load_log_csv(path: Path | str) -> LogData:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")

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
    )
