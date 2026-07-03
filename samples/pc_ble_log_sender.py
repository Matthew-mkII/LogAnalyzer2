#!/usr/bin/env python3
"""LogAnalyzer2 向け BLE ログ送信サンプル（PC + bless）

Pybricks ハブではなく、PC が仮想デバイス LogSensor として送信するテスト用です。
Pybricks ハブから送る場合は `samples/pybricks_line_tracer_log_sender.py` 等を参照してください。

使い方:
    pip install -r samples/requirements-sender.txt
    python samples/pc_ble_log_sender.py
"""

from __future__ import annotations

import asyncio
import logging
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from log_format import format_log_line, iter_notify_chunks

try:
    from bless import (
        BlessServer,
        GATTAttributePermissions,
        GATTCharacteristicProperties,
    )
except ImportError as exc:
    raise SystemExit(
        "bless が必要です:\n"
        "  pip install -r samples/requirements-sender.txt"
    ) from exc

NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

DEVICE_NAME = "LogSensor"
SEND_INTERVAL_SEC = 0.1
MTU_CHUNK_SIZE = 20

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class PcBleLogSender:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._server = BlessServer(name=DEVICE_NAME, loop=loop)
        self._server.read_request_func = self._read_request
        self._start_monotonic = time.monotonic()
        self._sample_index = 0
        self._sending = False

    def _read_request(self, characteristic, **_kwargs) -> bytearray:
        return bytearray(characteristic.value or b"")

    async def start(self) -> None:
        await self._server.add_new_service(NUS_SERVICE_UUID)
        await self._server.add_new_characteristic(
            NUS_SERVICE_UUID,
            NUS_TX_CHAR_UUID,
            GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify,
            None,
            GATTAttributePermissions.readable,
        )
        await self._server.start()
        logger.info("アドバタイズ開始: %s", DEVICE_NAME)

    async def wait_for_subscriber(self) -> None:
        while not await self._server.is_connected():
            await asyncio.sleep(0.1)
        logger.info("クライアントが接続しました。ログ送信を開始します。")
        self._start_monotonic = time.monotonic()
        self._sample_index = 0
        self._sending = True

    async def send_loop(self) -> None:
        while True:
            if self._sending and await self._server.is_connected():
                elapsed_ms = (time.monotonic() - self._start_monotonic) * 1000
                t = self._sample_index / 10.0
                roll = 10.0 * math.sin(t)
                yaw = 20.0 + 5.0 * math.cos(t)
                pitch = 5.0 * math.sin(t * 0.5)
                line = format_log_line(
                    time_ms=elapsed_ms,
                    values={
                        "turn": -45.0,
                        "speed": 10.0,
                        "battery": 8000.0 - self._sample_index,
                        "angleL": 0.0,
                        "angleR": 0.0,
                        "hue": 120.0 + 10.0 * math.sin(t),
                        "saturation": 80.0,
                        "value": 0.5 + 0.1 * math.cos(t),
                        "roll": roll,
                        "yaw": yaw,
                        "pitch": pitch,
                    },
                )
                await self._notify_line(line)
                self._sample_index += 1
            await asyncio.sleep(SEND_INTERVAL_SEC)

    async def _notify_line(self, line: str) -> None:
        payload = line.encode("utf-8")
        characteristic = self._server.get_characteristic(NUS_TX_CHAR_UUID)
        for chunk in iter_notify_chunks(payload, MTU_CHUNK_SIZE):
            characteristic.value = bytearray(chunk)
            self._server.update_value(NUS_SERVICE_UUID, NUS_TX_CHAR_UUID)
            await asyncio.sleep(0.005)


async def main() -> None:
    loop = asyncio.get_running_loop()
    sender = PcBleLogSender(loop)
    await sender.start()
    await sender.wait_for_subscriber()
    await sender.send_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("終了します。")
