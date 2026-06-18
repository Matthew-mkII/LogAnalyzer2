"""Bluetooth 受信ログのファイル出力"""

from datetime import datetime
from pathlib import Path


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
        self._file.write("received_at,sample_index,raw_data,parsed_value\n")
        self._file.flush()
        return self._path

    def write(
        self,
        raw_data: str,
        sample_index: int | None,
        parsed_value: float | None,
        received_at: datetime | None = None,
    ) -> None:
        if self._file is None:
            return

        received_at = received_at or datetime.now()
        received_at_str = received_at.isoformat(timespec="milliseconds")
        escaped = raw_data.replace('"', '""')
        index = "" if sample_index is None else str(sample_index)
        value = "" if parsed_value is None else str(parsed_value)
        self._file.write(f'{received_at_str},{index},"{escaped}",{value}\n')
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
