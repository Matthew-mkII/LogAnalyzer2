"""Bluetooth 受信ログのファイル出力"""

from datetime import datetime
from pathlib import Path

DEFAULT_COLUMNS = ("received_at", "sample_index", "raw_data", "parsed_value")


class LogWriter:
    def __init__(self, log_dir: str = "logs") -> None:
        self._log_dir = Path(log_dir)
        self._file = None
        self._path: Path | None = None
        self._columns: tuple[str, ...] = DEFAULT_COLUMNS

    def start(
        self,
        device_address: str = "",
        columns: tuple[str, ...] | list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Path:
        self._log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = self._log_dir / f"log_{timestamp}.csv"
        self._columns = tuple(columns) if columns else DEFAULT_COLUMNS
        self._file = self._path.open("w", encoding="utf-8", newline="")
        self._write_header(device_address=device_address, metadata=metadata)
        self._file.flush()
        return self._path

    def _write_header(
        self,
        device_address: str = "",
        metadata: dict[str, str] | None = None,
    ) -> None:
        if self._file is None:
            return

        started_at = datetime.now().isoformat(timespec="milliseconds")
        header_lines = [
            "# format=LogAnalyzer2",
            f"# started_at={started_at}",
        ]

        if device_address:
            header_lines.append(f"# device_address={device_address}")

        if metadata:
            for key, value in metadata.items():
                header_lines.append(f"# {key}={value}")

        header_lines.append(f"# columns={','.join(self._columns)}")
        header_lines.append(",".join(self._columns))

        self._file.write("\n".join(header_lines) + "\n")

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
        row = {
            "received_at": received_at.isoformat(timespec="milliseconds"),
            "sample_index": "" if sample_index is None else str(sample_index),
            "raw_data": raw_data.replace('"', '""'),
            "parsed_value": "" if parsed_value is None else str(parsed_value),
        }
        values = []
        for column in self._columns:
            value = row.get(column, "")
            if column == "raw_data":
                values.append(f'"{value}"')
            else:
                values.append(str(value))

        self._file.write(",".join(values) + "\n")
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
        return self._columns
