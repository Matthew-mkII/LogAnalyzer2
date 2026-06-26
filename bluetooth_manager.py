"""BLE (Bluetooth Low Energy) 接続管理"""

import asyncio

from PySide6.QtCore import QObject, Signal
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

# Nordic UART Service（多くのログ機器で使われるシリアル通信プロファイル）
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Pybricks GATT（ハブの stdout イベント受信用）
PYBRICKS_COMMAND_EVENT_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"
PYBRICKS_EVENT_WRITE_STDOUT = 0x01

CONNECT_TIMEOUT_SEC = 30.0
MAX_RECEIVE_BUFFER = 65536


def _discovered_device_sort_key(device) -> tuple[int, str, str]:
    name = (device.name or "").strip()
    if name:
        return (0, name.lower(), device.address)
    return (1, device.address, "")


class BluetoothManager(QObject):
    device_discovered = Signal(str, str)  # name, address
    scan_finished = Signal()
    connected = Signal(str)
    disconnected = Signal()
    data_received = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._client: BleakClient | None = None
        self._notify_char_uuid: str | None = None
        self._pybricks_notify_uuid: str | None = None
        self._receive_buffer = ""
        self._discovered_devices: dict[str, BLEDevice] = {}
        self._operation_lock = asyncio.Lock()

    async def scan(self, timeout: float = 5.0) -> None:
        async with self._operation_lock:
            if self.is_connected:
                self.error_occurred.emit("接続中はスキャンできません")
                self.scan_finished.emit()
                return

            self._discovered_devices.clear()
            self.status_changed.emit("スキャン中...")
            try:
                devices = await BleakScanner.discover(timeout=timeout)
                for device in sorted(devices, key=_discovered_device_sort_key):
                    self._discovered_devices[device.address] = device
                    name = device.name or "不明"
                    self.device_discovered.emit(name, device.address)
                self.status_changed.emit(f"{len(devices)} 台を検出しました")
            except Exception as exc:
                self.error_occurred.emit(f"スキャンエラー: {exc}")
            finally:
                self.scan_finished.emit()

    async def connect(self, address: str) -> None:
        async with self._operation_lock:
            if self._client and self._client.is_connected:
                self.error_occurred.emit("既に接続されています")
                return

            device = self._discovered_devices.get(address)
            if device is None:
                self.error_occurred.emit(
                    "デバイス情報が見つかりません。スキャンし直してから接続してください。"
                )
                return

            self.status_changed.emit("接続中...")
            try:
                client = BleakClient(
                    device,
                    disconnected_callback=self._on_disconnected,
                    timeout=CONNECT_TIMEOUT_SEC,
                )
                await client.connect(timeout=CONNECT_TIMEOUT_SEC)
                self._client = client

                notify_uuid = self._find_notify_characteristic(client)
                pybricks_uuid = self._find_pybricks_event_characteristic(client)
                if notify_uuid is None and pybricks_uuid is None:
                    await client.disconnect()
                    self._client = None
                    self.error_occurred.emit(
                        "通知可能なキャラクタリスティックが見つかりません。"
                        " 送信プログラムが起動しているか確認してください。"
                    )
                    return

                self._reset_receive_buffer()
                self._notify_char_uuid = notify_uuid
                self._pybricks_notify_uuid = pybricks_uuid

                if notify_uuid is not None:
                    await client.start_notify(notify_uuid, self._on_notify)
                if pybricks_uuid is not None:
                    await client.start_notify(pybricks_uuid, self._on_pybricks_notify)

                self.status_changed.emit(f"接続済み: {device.name or address}")
                self.connected.emit(address)
            except Exception as exc:
                self._client = None
                self.error_occurred.emit(
                    f"接続エラー: {type(exc).__name__}: {exc}\n"
                    "ヒント: 送信プログラムを起動し、スキャン直後に接続してください。"
                )

    async def disconnect(self) -> None:
        async with self._operation_lock:
            if self._client is None:
                return

            self.status_changed.emit("切断中...")
            try:
                if self._client.is_connected:
                    if self._notify_char_uuid:
                        await self._client.stop_notify(self._notify_char_uuid)
                    if self._pybricks_notify_uuid:
                        await self._client.stop_notify(self._pybricks_notify_uuid)
                await self._client.disconnect()
            except Exception as exc:
                self.error_occurred.emit(f"切断エラー: {exc}")
            finally:
                self._flush_receive_buffer()
                self._client = None
                self._notify_char_uuid = None
                self._pybricks_notify_uuid = None
                self.status_changed.emit("未接続")
                self.disconnected.emit()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def _reset_receive_buffer(self) -> None:
        self._receive_buffer = ""

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

    def _on_notify(self, _sender: int, data: bytearray) -> None:
        text = data.decode("utf-8", errors="replace")
        if text:
            self._append_receive_data(text)

    def _on_pybricks_notify(self, _sender: int, data: bytearray) -> None:
        if len(data) < 2 or data[0] != PYBRICKS_EVENT_WRITE_STDOUT:
            return

        text = bytes(data[1:]).decode("utf-8", errors="replace")
        if text:
            self._append_receive_data(text)

    def _on_disconnected(self, _client: BleakClient) -> None:
        self._flush_receive_buffer()
        self._client = None
        self._notify_char_uuid = None
        self._pybricks_notify_uuid = None
        self.status_changed.emit("未接続")
        self.disconnected.emit()

    def _find_notify_characteristic(self, client: BleakClient) -> str | None:
        for service in client.services:
            if str(service.uuid).lower() != NUS_SERVICE_UUID.lower():
                continue
            for char in service.characteristics:
                if str(char.uuid).lower() == NUS_TX_CHAR_UUID.lower():
                    if "notify" in char.properties:
                        return str(char.uuid)

        for service in client.services:
            if str(service.uuid).lower() == NUS_SERVICE_UUID.lower():
                for char in service.characteristics:
                    if "notify" in char.properties:
                        return str(char.uuid)

        return None

    @staticmethod
    def _find_pybricks_event_characteristic(client: BleakClient) -> str | None:
        target = PYBRICKS_COMMAND_EVENT_UUID.lower()
        for service in client.services:
            for char in service.characteristics:
                if str(char.uuid).lower() == target and "notify" in char.properties:
                    return str(char.uuid)
        return None
