# SPDX-License-Identifier: MIT
"""LogAnalyzer2 向けログ送信（Pybricks）

対象: SPIKE Prime / Robot Inventor / Technic Hub 等（Pybricks firmware 3.3+）

センサー:
  - カラーセンサー（外付け）→ angleL=h, angleR=s, bright=v（HSV 生値）
  - IMU 姿勢角 → roll / yaw / pitch（角度 deg）

配線:
  SPIKE カラーセンサーを COLOR_SENSOR_PORT に接続してください。
  ジャイロは SPIKE Prime ラージハブに内蔵されているため、追加配線は不要です。
  Pybricks では hub.imu 経由で読み取ります。

使い方:
  1. 下の COLOR_SENSOR_PORT を環境に合わせて変更
  2. Pybricks Code で本ファイルをハブに書き込む
  3. Pybricks Code から切断する（他アプリと同時接続不可）
  4. LogAnalyzer2 でスキャン → ハブ名を選択 → 接続
  5. ハブのボタンでプログラムを開始
  6. グラフ表示と logs/*.csv への記録を確認

送信方法:
  usys.stdout へログ行を書き込む（Pybricks BLE stdout イベント）。
  LogAnalyzer2 は Pybricks stdout と NUS の両方を受信できます。

注意:
  BOOST Move Hub は usys 非対応のため動作しません。
  カラーセンサーは color_sensor.hsv() の値を変換せずそのまま送ります。
"""

from pybricks.hubs import ThisHub
from pybricks.parameters import Port
from pybricks.pupdevices import ColorSensor
from pybricks.tools import StopWatch, wait

from usys import stdout

# --- センサー設定（お使いのロボットに合わせて変更） ---
COLOR_SENSOR_PORT = Port.E

SEND_INTERVAL_MS = 100

VALUE_COLUMNS = (
    "turn",
    "speed",
    "battery",
    "angleL",
    "angleR",
    "bright",
    "Kp",
    "Ki",
    "Kd",
    "roll",
    "yaw",
    "pitch",
)


def format_number(value):
    if float(value) == int(value):
        return str(int(value))
    return "{:.6f}".format(value)


def format_log_line(time_ms=None, values=None):
    """1 レコード分のログ行（末尾に改行）。"""
    values = values or {}
    fields = []

    if time_ms is not None:
        fields.append(format_number(time_ms))

    for column in VALUE_COLUMNS:
        value = values.get(column)
        if value is None:
            fields.append("")
        else:
            fields.append(format_number(value))

    return ",".join(fields) + "\n"


def send_log_line(line):
    stdout.write(line)


def read_hsv(color_sensor):
    """カラーセンサーの HSV 生値 (h, s, v) を読む。"""
    try:
        return color_sensor.hsv()
    except OSError:
        return None


def read_orientation(hub):
    """ラージハブ内蔵 IMU の姿勢角 roll / yaw / pitch（deg）を読む。"""
    try:
        pitch, roll = hub.imu.tilt()
        yaw = hub.imu.heading()
        return roll, yaw, pitch
    except (AttributeError, TypeError, ValueError):
        return None, None, None


def read_battery(hub):
    """バッテリー電圧（mV）を読む。未対応時は None。"""
    try:
        return hub.battery.voltage()
    except AttributeError:
        return None


hub = ThisHub()
color_sensor = ColorSensor(COLOR_SENSOR_PORT)
watch = StopWatch()

while True:
    elapsed_ms = watch.time()
    hsv = read_hsv(color_sensor)
    if hsv is None:
        hue, saturation, value = None, None, None
    else:
        hue, saturation, value = hsv

    roll, yaw, pitch = read_orientation(hub)

    line = format_log_line(
        time_ms=elapsed_ms,
        values={
            "turn": 0.0,
            "speed": 0.0,
            "battery": read_battery(hub),
            "angleL": hue,
            "angleR": saturation,
            "bright": value,
            "Kp": 0.0,
            "Ki": 0.0,
            "Kd": 0.0,
            "roll": roll,
            "yaw": yaw,
            "pitch": pitch,
        },
    )
    send_log_line(line)

    wait(SEND_INTERVAL_MS)
