"""BLE (Bluetooth Low Energy) 接続管理"""

from PyQt6.QtCore import QObject, pyqtSignal
from bleak import BleakClient, BleakScanner

# Nordic UART Service（多くのログ機器で使われるシリアル通信プロファイル）
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class BluetoothManager(QObject):
    device_discovered = pyqtSignal(str, str)  # name, address
    scan_finished = pyqtSignal()
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._client: BleakClient | None = None
        self._notify_char_uuid: str | None = None

    async def scan(self, timeout: float = 5.0) -> None:
        self.status_changed.emit("スキャン中...")
        try:
            devices = await BleakScanner.discover(timeout=timeout)
            for device in devices:
                name = device.name or "不明"
                self.device_discovered.emit(name, device.address)
            self.status_changed.emit(f"{len(devices)} 台を検出しました")
        except Exception as exc:
            self.error_occurred.emit(f"スキャンエラー: {exc}")
        finally:
            self.scan_finished.emit()

    async def connect(self, address: str) -> None:
        if self._client and self._client.is_connected:
            self.error_occurred.emit("既に接続されています")
            return

        self.status_changed.emit("接続中...")
        try:
            client = BleakClient(address, disconnected_callback=self._on_disconnected)
            await client.connect()
            self._client = client

            notify_uuid = await self._find_notify_characteristic(client)
            if notify_uuid is None:
                await client.disconnect()
                self._client = None
                self.error_occurred.emit("通知可能なキャラクタリスティックが見つかりません")
                return

            self._notify_char_uuid = notify_uuid
            await client.start_notify(notify_uuid, self._on_notify)

            self.status_changed.emit(f"接続済み: {address}")
            self.connected.emit(address)
        except Exception as exc:
            self._client = None
            self.error_occurred.emit(f"接続エラー: {exc}")

    async def disconnect(self) -> None:
        if self._client is None:
            return

        self.status_changed.emit("切断中...")
        try:
            if self._notify_char_uuid and self._client.is_connected:
                await self._client.stop_notify(self._notify_char_uuid)
            await self._client.disconnect()
        except Exception as exc:
            self.error_occurred.emit(f"切断エラー: {exc}")
        finally:
            self._client = None
            self._notify_char_uuid = None
            self.status_changed.emit("未接続")
            self.disconnected.emit()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def _on_notify(self, _sender: int, data: bytearray) -> None:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            self.data_received.emit(text)

    def _on_disconnected(self, _client: BleakClient) -> None:
        self._client = None
        self._notify_char_uuid = None
        self.status_changed.emit("未接続")
        self.disconnected.emit()

    async def _find_notify_characteristic(self, client: BleakClient) -> str | None:
        for service in client.services:
            if str(service.uuid).lower() == NUS_SERVICE_UUID.lower():
                for char in service.characteristics:
                    if "notify" in char.properties:
                        return str(char.uuid)

        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    return str(char.uuid)

        return None
