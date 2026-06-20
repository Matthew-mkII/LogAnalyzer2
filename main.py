import os
import sys

_SUPPRESSED_STDERR_MESSAGES = (
    "GPUInfo not initialized on GpuInfoUpdate",
    "TSMSendMessageToUIServer",
    "IMKCFRunLoopWakeUpReliable",
)


class _FilteredStderr:
    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        if any(message in text for message in _SUPPRESSED_STDERR_MESSAGES):
            return len(text)
        return self._stream.write(text)

    def flush(self):
        self._stream.flush()

    def __getattr__(self, name):
        return getattr(self._stream, name)


sys.stderr = _FilteredStderr(sys.stderr)

# ★ 完全安定設定
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing "
    "--disable-logging --log-level=3"
)
os.environ["QT_OPENGL"] = "software"
os.environ["QT_XCB_GL_INTEGRATION"] = "none"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_API"] = "pyside6"

import asyncio
from datetime import datetime

import plotly.graph_objects as go
import qasync
from PySide6.QtCore import QTimer, QUrl, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from app_paths import logs_dir, temp_html_path
from bluetooth_manager import BluetoothManager
from log_reader import load_log_csv
from log_writer import LEGACY_VALUE_COLUMNS, LogWriter, LogWriterError, parse_legacy_row
from tcp_manager import TcpLogManager


def _qt_message_handler(mode, _context, message) -> None:
    if "GPUInfo not initialized on GpuInfoUpdate" in message:
        return
    if mode == QtMsgType.QtFatalMsg:
        sys.__stderr__.write(f"Fatal: {message}\n")
    elif mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
        sys.__stderr__.write(f"{message}\n")


qInstallMessageHandler(_qt_message_handler)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LogAnalyzer2 by matthew")

        self._x_data: list[float] = []
        self._series_data: dict[str, list[float | None]] = {}
        self._enabled_series: set[str] = set()
        self._series_checkboxes: dict[str, QCheckBox] = {}
        self._graph_title: str | None = None
        self._sample_index = 0
        self._session_start: datetime | None = None
        self._graph_io_error_shown = False
        self._csv_view_active = False
        self._pre_csv_log_label = "ログ: 未記録"
        self._html_path = str(temp_html_path())

        self.bt_manager = BluetoothManager()
        self.tcp_manager = TcpLogManager()
        self._active_transport: str | None = None
        self._log_writer = LogWriter(str(logs_dir()))

        self.browser = QWebEngineView()
        self._render_graph()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(self._create_bluetooth_panel())
        layout.addLayout(self._create_tcp_panel())
        layout.addWidget(self._create_log_panel())
        layout.addWidget(self._create_series_panel())
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

        self.disconnect_btn = QPushButton("切断（ログ書き込み）")
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

    def _create_tcp_panel(self) -> QHBoxLayout:
        panel = QHBoxLayout()

        panel.addWidget(QLabel("TCP:"))

        self.tcp_host_input = QLineEdit("127.0.0.1")
        self.tcp_host_input.setMinimumWidth(120)
        panel.addWidget(self.tcp_host_input)

        panel.addWidget(QLabel("ポート"))

        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(8765)
        panel.addWidget(self.tcp_port_input)

        self.tcp_connect_btn = QPushButton("TCP接続")
        self.tcp_connect_btn.clicked.connect(self._on_tcp_connect_clicked)
        panel.addWidget(self.tcp_connect_btn)

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

        self.reset_view_btn = QPushButton("初期状態に戻す")
        self.reset_view_btn.clicked.connect(self._on_reset_view_clicked)
        self.reset_view_btn.setEnabled(False)
        layout.addWidget(self.reset_view_btn)

        return container

    def _create_series_panel(self) -> QScrollArea:
        self.series_panel = QScrollArea()
        self.series_panel.setWidgetResizable(True)
        self.series_panel.setMaximumHeight(48)

        series_container = QWidget()
        self.series_layout = QHBoxLayout(series_container)
        self.series_layout.setContentsMargins(0, 0, 0, 0)
        self.series_panel.setWidget(series_container)
        self.series_panel.hide()
        return self.series_panel

    def _clear_series_panel(self) -> None:
        for checkbox in self._series_checkboxes.values():
            checkbox.deleteLater()
        self._series_checkboxes.clear()

        while self.series_layout.count():
            item = self.series_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._enabled_series.clear()
        self.series_panel.hide()

    def _setup_series_panel(self, series_names: list[str]) -> None:
        self._clear_series_panel()
        if not series_names:
            return

        default_enabled = {"gyro"} if "gyro" in series_names else {series_names[0]}

        for name in series_names:
            checkbox = QCheckBox(name)
            checkbox.setChecked(name in default_enabled)
            checkbox.stateChanged.connect(self._on_series_toggled)
            self._series_checkboxes[name] = checkbox
            self.series_layout.addWidget(checkbox)

        self._enabled_series = {
            name for name, checkbox in self._series_checkboxes.items() if checkbox.isChecked()
        }
        self.series_panel.show()

    def _on_series_toggled(self) -> None:
        self._enabled_series = {
            name for name, checkbox in self._series_checkboxes.items() if checkbox.isChecked()
        }
        self._render_graph(title=self._graph_title)

    def _setup_bluetooth_signals(self) -> None:
        self.bt_manager.device_discovered.connect(self._on_device_discovered)
        self.bt_manager.scan_finished.connect(self._on_scan_finished)
        self.bt_manager.connected.connect(self._on_transport_connected)
        self.bt_manager.disconnected.connect(self._on_transport_disconnected)
        self.bt_manager.data_received.connect(self._on_data_received)
        self.bt_manager.error_occurred.connect(self._on_transport_error)
        self.bt_manager.status_changed.connect(self.status_label.setText)

        self.tcp_manager.connected.connect(self._on_transport_connected)
        self.tcp_manager.disconnected.connect(self._on_transport_disconnected)
        self.tcp_manager.data_received.connect(self._on_data_received)
        self.tcp_manager.error_occurred.connect(self._on_transport_error)
        self.tcp_manager.status_changed.connect(self.status_label.setText)

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
        self._set_transport_controls_enabled(False)
        self._active_transport = "ble"
        asyncio.create_task(self.bt_manager.connect(address))

    def _on_tcp_connect_clicked(self) -> None:
        host = self.tcp_host_input.text().strip() or "127.0.0.1"
        port = self.tcp_port_input.value()
        self._set_transport_controls_enabled(False)
        self._active_transport = "tcp"
        asyncio.create_task(self.tcp_manager.connect(host, port))

    def _on_disconnect_clicked(self) -> None:
        if self._active_transport == "tcp":
            asyncio.create_task(self.tcp_manager.disconnect())
        else:
            asyncio.create_task(self.bt_manager.disconnect())

    def _on_transport_connected(self, _endpoint: str) -> None:
        self.disconnect_btn.setEnabled(True)

        self._session_start = None
        self._x_data = []
        self._series_data = {}
        self._enabled_series = set()
        self._graph_title = None
        self._sample_index = 0
        self._graph_io_error_shown = False
        self._csv_view_active = False
        self.reset_view_btn.setEnabled(False)
        self._clear_series_panel()
        self._render_graph()

        try:
            log_path = self._log_writer.start()
        except LogWriterError as exc:
            QMessageBox.warning(self, "ログ保存", str(exc))
            self._on_disconnect_clicked()
            return

        self.log_path_label.setText(f"ログ記録中: {log_path}")

    def _set_transport_controls_enabled(self, enabled: bool) -> None:
        self.connect_btn.setEnabled(enabled)
        self.tcp_connect_btn.setEnabled(enabled)
        self.scan_btn.setEnabled(enabled)
        self.tcp_host_input.setEnabled(enabled)
        self.tcp_port_input.setEnabled(enabled)

    def _on_transport_disconnected(self) -> None:
        self._active_transport = None
        self._set_transport_controls_enabled(True)
        self.disconnect_btn.setEnabled(False)

        if self._log_writer.is_active:
            try:
                log_path = self._log_writer.stop()
            except LogWriterError as exc:
                QMessageBox.warning(self, "ログ保存", str(exc))
                self.log_path_label.setText("ログ: 保存エラー")
                return

            if log_path:
                self.log_path_label.setText(f"ログ保存済み: {log_path}")

    def _handle_log_write_error(self, exc: LogWriterError) -> None:
        QMessageBox.warning(self, "ログ保存", str(exc))
        if self._log_writer.is_active:
            try:
                self._log_writer.stop()
            except LogWriterError:
                pass
        self.log_path_label.setText("ログ: 記録エラー（書き込み停止）")

    def _on_transport_error(self, message: str) -> None:
        title = "TCP" if self._active_transport == "tcp" else "Bluetooth"
        QMessageBox.warning(self, title, message)
        self._active_transport = None
        self._set_transport_controls_enabled(True)
        self.disconnect_btn.setEnabled(False)

    def _on_load_csv_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "ログ CSV を開く",
            str(logs_dir()),
            "CSV Files (*.csv)",
        )
        if not path:
            return

        try:
            log_data = load_log_csv(path)
        except Exception as exc:
            QMessageBox.warning(self, "CSV読み込み", str(exc))
            return

        self._pre_csv_log_label = self.log_path_label.text()
        self._x_data = log_data.x
        self._series_data = log_data.series
        self._sample_index = log_data.last_sample_index
        self._session_start = None
        self._graph_title = (
            f"{log_data.source.name} ({log_data.plotted_rows}/{log_data.total_rows} 件)"
        )
        self._setup_series_panel(list(log_data.series.keys()))
        self._render_graph(title=self._graph_title)
        self.log_path_label.setText(f"表示中: {log_data.source}")
        self._csv_view_active = True
        self.reset_view_btn.setEnabled(True)

    def _on_reset_view_clicked(self) -> None:
        if not self._csv_view_active:
            return
        self._reset_graph_view()

    def _reset_graph_view(self) -> None:
        self._graph_timer.stop()
        self._graph_dirty = False
        self._x_data = []
        self._series_data = {}
        self._enabled_series = set()
        self._graph_title = None
        self._sample_index = 0
        if not self._is_transport_connected():
            self._session_start = None
        self._clear_series_panel()
        self._render_graph()
        self.log_path_label.setText(self._pre_csv_log_label)
        self._csv_view_active = False
        self.reset_view_btn.setEnabled(False)

    def _is_transport_connected(self) -> bool:
        return self.bt_manager.is_connected or self.tcp_manager.is_connected

    def _ensure_realtime_series(self) -> None:
        if self._series_data:
            return

        self._series_data = {column: [] for column in LEGACY_VALUE_COLUMNS}
        self._setup_series_panel(list(LEGACY_VALUE_COLUMNS))

    def _on_data_received(self, text: str) -> None:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            received_at = datetime.now()
            device_time, row_values = parse_legacy_row(stripped)

            if self._session_start is None:
                self._session_start = received_at

            if device_time is not None:
                elapsed_ms = device_time
            else:
                elapsed_ms = (received_at - self._session_start).total_seconds() * 1000

            self._sample_index += 1
            self._ensure_realtime_series()
            self._x_data.append(elapsed_ms)
            for column in LEGACY_VALUE_COLUMNS:
                self._series_data[column].append(row_values[column])
            self._schedule_graph_update()

            if self._log_writer.is_active:
                try:
                    self._log_writer.write(elapsed_ms, row_values)
                except LogWriterError as exc:
                    self._handle_log_write_error(exc)
                    return

    def _schedule_graph_update(self) -> None:
        if not self._graph_dirty:
            self._graph_dirty = True
            self._graph_timer.start(200)

    def _normalize_x_axis(self, x_data: list[float]) -> list[float]:
        if not x_data:
            return []
        x_min = min(x_data)
        return [x - x_min for x in x_data]

    def _apply_graph_layout(self, fig: go.Figure, title: str | None = None) -> None:
        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            xaxis_title="経過時間 (ms)",
            yaxis_title="値",
        )
        if title:
            fig.update_layout(title=title)

    def _render_graph(self, title: str | None = None) -> None:
        self._graph_dirty = False
        if title is not None:
            self._graph_title = title

        active_series = {
            name: values
            for name, values in self._series_data.items()
            if name in self._enabled_series
        }

        if self._x_data and active_series:
            x_plot = self._normalize_x_axis(self._x_data)
            x_max = max(x_plot)
            if x_max <= 0:
                x_max = 1

            fig = go.Figure()
            for name, y_values in active_series.items():
                count = min(len(x_plot), len(y_values))
                fig.add_trace(
                    go.Scatter(
                        x=x_plot[:count],
                        y=y_values[:count],
                        mode="lines",
                        name=name,
                    )
                )

            fig.update_xaxes(range=[0, x_max * 1.05], autorange=False)
            self._apply_graph_layout(fig, title=title or self._graph_title)
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0], y=[0], mode="lines", name="データなし"))
            fig.update_xaxes(range=[0, 1], autorange=False)
            self._apply_graph_layout(fig, title=title or self._graph_title or "データ待機中...")

        try:
            fig.write_html(self._html_path, include_plotlyjs=True)
            self.browser.load(QUrl.fromLocalFile(self._html_path))
            self._graph_io_error_shown = False
        except OSError as exc:
            if not self._graph_io_error_shown:
                self._graph_io_error_shown = True
                QMessageBox.warning(
                    self,
                    "グラフ表示",
                    f"グラフファイルを書き込めません: {exc}",
                )


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
    import multiprocessing

    multiprocessing.freeze_support()
    main()
