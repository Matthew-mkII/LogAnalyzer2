import os

# ★ 完全安定設定
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing"
)
os.environ["QT_OPENGL"] = "software"
os.environ["QT_XCB_GL_INTEGRATION"] = "none"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

import asyncio
import sys

import plotly.express as px
import qasync
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

from bluetooth_manager import BluetoothManager
from log_reader import load_log_csv
from log_writer import LogWriter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LogAnalyzer2 by matthew")

        self._x_data: list[float] = []
        self._y_data: list[float] = []
        self._sample_index = 0
        self._html_path = os.path.abspath("temp.html")

        self.bt_manager = BluetoothManager()
        self._log_writer = LogWriter()

        self.browser = QWebEngineView()
        self._render_graph()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(self._create_bluetooth_panel())
        layout.addWidget(self._create_log_panel())
        layout.addWidget(self.browser, stretch=1)
        self.setCentralWidget(central)

        self._setup_bluetooth_signals()

        self._graph_timer = QTimer()
        self._graph_timer.setSingleShot(True)
        self._graph_timer.timeout.connect(self._render_graph)
        self._graph_dirty = False

    def _create_bluetooth_panel(self) -> QHBoxLayout:
        panel = QHBoxLayout()

        self.scan_btn = QPushButton("スキャン")
        self.scan_btn.clicked.connect(self._on_scan_clicked)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(280)
        self.device_combo.setPlaceholderText("デバイスを選択")

        self.connect_btn = QPushButton("接続")
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.disconnect_btn = QPushButton("切断")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)

        self.status_label = QLabel("未接続")
        self.status_label.setMinimumWidth(200)

        panel.addWidget(self.scan_btn)
        panel.addWidget(self.device_combo, stretch=1)
        panel.addWidget(self.connect_btn)
        panel.addWidget(self.disconnect_btn)
        panel.addWidget(self.status_label)

        return panel

    def _create_log_panel(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_path_label = QLabel("ログ: 未記録")
        self.log_path_label.setMinimumWidth(400)
        layout.addWidget(self.log_path_label)

        self.load_csv_btn = QPushButton("CSVからグラフ")
        self.load_csv_btn.clicked.connect(self._on_load_csv_clicked)
        layout.addWidget(self.load_csv_btn)

        return container

    def _setup_bluetooth_signals(self) -> None:
        self.bt_manager.device_discovered.connect(self._on_device_discovered)
        self.bt_manager.scan_finished.connect(self._on_scan_finished)
        self.bt_manager.connected.connect(self._on_connected)
        self.bt_manager.disconnected.connect(self._on_disconnected)
        self.bt_manager.data_received.connect(self._on_data_received)
        self.bt_manager.error_occurred.connect(self._on_bt_error)
        self.bt_manager.status_changed.connect(self.status_label.setText)

    def _on_scan_clicked(self) -> None:
        self.scan_btn.setEnabled(False)
        self.device_combo.clear()
        asyncio.create_task(self.bt_manager.scan())

    def _on_scan_finished(self) -> None:
        self.scan_btn.setEnabled(True)

    def _on_device_discovered(self, name: str, address: str) -> None:
        self.device_combo.addItem(f"{name} ({address})", address)

    def _on_connect_clicked(self) -> None:
        address = self.device_combo.currentData()
        if not address:
            QMessageBox.warning(self, "接続", "デバイスを選択してください")
            return
        self.connect_btn.setEnabled(False)
        asyncio.create_task(self.bt_manager.connect(address))

    def _on_disconnect_clicked(self) -> None:
        asyncio.create_task(self.bt_manager.disconnect())

    def _on_connected(self, address: str) -> None:
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.scan_btn.setEnabled(False)

        log_path = self._log_writer.start(address)
        self.log_path_label.setText(f"ログ記録中: {log_path}")

    def _on_disconnected(self) -> None:
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.scan_btn.setEnabled(True)

        if self._log_writer.is_active:
            log_path = self._log_writer.stop()
            if log_path:
                self.log_path_label.setText(f"ログ保存済み: {log_path}")

    def _on_bt_error(self, message: str) -> None:
        QMessageBox.warning(self, "Bluetooth", message)
        self._on_disconnected()

    def _on_load_csv_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "ログ CSV を開く",
            "logs",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        try:
            log_data = load_log_csv(path)
        except Exception as exc:
            QMessageBox.warning(self, "CSV読み込み", str(exc))
            return

        self._x_data = log_data.x
        self._y_data = log_data.y
        self._sample_index = int(max(log_data.x))
        title = f"{log_data.source.name} ({log_data.plotted_rows}/{log_data.total_rows} 件)"
        self._render_graph(title=title)
        self.log_path_label.setText(f"表示中: {log_data.source}")

    def _on_data_received(self, text: str) -> None:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            value = self._parse_value(stripped)
            sample_index = None

            if value is not None:
                self._sample_index += 1
                sample_index = self._sample_index
                self._x_data.append(self._sample_index)
                self._y_data.append(value)
                self._schedule_graph_update()

            if self._log_writer.is_active:
                self._log_writer.write(stripped, sample_index, value)

    def _parse_value(self, line: str) -> float | None:
        line = line.strip()
        if not line:
            return None

        # "timestamp,value" 形式
        if "," in line:
            parts = line.split(",")
            for part in reversed(parts):
                try:
                    return float(part.strip())
                except ValueError:
                    continue
            return None

        try:
            return float(line)
        except ValueError:
            return None

    def _schedule_graph_update(self) -> None:
        if not self._graph_dirty:
            self._graph_dirty = True
            self._graph_timer.start(200)

    def _render_graph(self, title: str | None = None) -> None:
        self._graph_dirty = False

        if self._x_data:
            fig = px.line(x=self._x_data, y=self._y_data, labels={"x": "サンプル", "y": "値"})
            if title:
                fig.update_layout(title=title)
        else:
            fig = px.line(
                x=[0],
                y=[0],
                labels={"x": "サンプル", "y": "値"},
            )
            fig.update_layout(title="データ待機中...")

        fig.write_html(self._html_path, include_plotlyjs=True)
        self.browser.load(QUrl.fromLocalFile(self._html_path))


def main() -> None:
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.resize(900, 650)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
