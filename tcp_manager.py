"""TCP 経由のログ受信（同一 Mac 上の log-sender 向け）"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, Signal

CONNECT_TIMEOUT_SEC = 10.0
MAX_RECEIVE_BUFFER = 65536


class TcpLogManager(QObject):
    connected = Signal(str)
    disconnected = Signal()
    data_received = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._read_task: asyncio.Task[None] | None = None
        self._receive_buffer = ""
        self._endpoint = ""

    async def connect(self, host: str, port: int) -> None:
        if self.is_connected:
            self.error_occurred.emit("既に TCP 接続されています")
            return

        self.status_changed.emit("TCP 接続中...")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=CONNECT_TIMEOUT_SEC,
            )
        except Exception as exc:
            self.error_occurred.emit(
                f"TCP 接続エラー: {type(exc).__name__}: {exc}\n"
                f"ヒント: log-sender --demo --tcp {port} が起動しているか確認してください。"
            )
            return

        self._reader = reader
        self._writer = writer
        self._endpoint = f"{host}:{port}"
        self._receive_buffer = ""
        self._read_task = asyncio.create_task(self._read_loop())

        self.status_changed.emit(f"TCP 接続済み: {self._endpoint}")
        self.connected.emit(self._endpoint)

    async def disconnect(self) -> None:
        if self._read_task is not None:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None

        self._reader = None
        self._flush_receive_buffer()
        self.status_changed.emit("未接続")
        self.disconnected.emit()

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while True:
                chunk = await self._reader.read(4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                if text:
                    self._append_receive_data(text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.error_occurred.emit(f"TCP 受信エラー: {exc}")
        finally:
            if self.is_connected or self._writer is not None:
                await self.disconnect()

    def _flush_receive_buffer(self) -> None:
        remainder = self._receive_buffer.strip()
        self._receive_buffer = ""
        if remainder:
            self.data_received.emit(remainder)

    def _append_receive_data(self, text: str) -> None:
        self._receive_buffer += text
        if len(self._receive_buffer) > MAX_RECEIVE_BUFFER:
            self._receive_buffer = ""
            self.error_occurred.emit(
                f"受信バッファが上限 ({MAX_RECEIVE_BUFFER} バイト) を超えました"
            )
            return

        while True:
            for separator in ("\r\n", "\n", "\r"):
                if separator in self._receive_buffer:
                    line, self._receive_buffer = self._receive_buffer.split(separator, 1)
                    line = line.strip()
                    if line:
                        self.data_received.emit(line)
                    break
            else:
                break
