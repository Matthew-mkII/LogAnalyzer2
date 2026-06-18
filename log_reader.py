"""保存済みログ CSV の読み込み"""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LogData:
    x: list[float]
    y: list[float]
    source: Path
    total_rows: int
    plotted_rows: int


def load_log_csv(path: Path | str) -> LogData:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")

    x: list[float] = []
    y: list[float] = []
    total_rows = 0

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
                x.append(float(index_str))
            else:
                x.append(float(len(y) + 1))
            y.append(value)

    if not x:
        raise ValueError("グラフ用の数値データがありません")

    return LogData(
        x=x,
        y=y,
        source=path,
        total_rows=total_rows,
        plotted_rows=len(x),
    )
