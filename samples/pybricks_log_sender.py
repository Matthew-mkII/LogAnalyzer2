# SPDX-License-Identifier: MIT
"""LogAnalyzer2 向けログ送信（Pybricks）

対象: SPIKE Prime / Robot Inventor / Technic Hub 等（Pybricks firmware 3.3+）

使い方:
  1. COLOR_SENSOR_PORT を環境に合わせて変更
  2. 本ファイルをハブに書き込み、Pybricks Code から切断
  3. LogAnalyzer2 でスキャン → 接続 → ハブでプログラム開始

送信: usys.stdout へ CSV 行を出力（BLE stdout イベント）。
注意: BOOST Move Hub は usys 非対応。
"""

from pybricks.hubs import ThisHub
from pybricks.parameters import Port
from pybricks.pupdevices import ColorSensor
from pybricks.tools import StopWatch, wait
from usys import stdout

# --- 設定 ---
COLOR_SENSOR_PORT = Port.E
SEND_INTERVAL_MS = 100

# LogAnalyzer2 の CSV 列順（time 列は別途先頭に付与）
VALUE_COLUMNS = (
    "turn",
    "speed",
    "battery",
    "angleL",
    "angleR",
    "hue",
    "saturation",
    "value",
    "Kp",
    "Ki",
    "Kd",
    "roll",
    "yaw",
    "pitch",
)


def format_number(value):
    """数値を CSV 用の文字列に変換する。None は空欄。"""
    if value is None:
        return ""
    value = float(value)
    if value == int(value):
        return str(int(value))
    return "{:.6f}".format(value)


def format_log_line(time_ms, values):
    """time + データ列の 1 行を生成する（末尾に改行）。"""
    fields = [format_number(time_ms)]
    for column in VALUE_COLUMNS:
        fields.append(format_number(values.get(column)))
    return ",".join(fields) + "\n"


def read_hsv(color_sensor):
    """カラーセンサーの HSV 生値 (h, s, v) を読む。"""
    try:
        return color_sensor.hsv()
    except OSError:
        return None, None, None


def read_orientation(hub):
    """IMU の姿勢角 roll / yaw / pitch（deg）を読む。"""
    try:
        pitch, roll = hub.imu.tilt()
        yaw = hub.imu.heading()
        return roll, yaw, pitch
    except (AttributeError, TypeError, ValueError):
        return None, None, None


def read_battery(hub):
    """バッテリー電圧（mV）を読む。"""
    try:
        return hub.battery.voltage()
    except AttributeError:
        return None


def build_log_values(hub, color_sensor):
    """1 サンプル分のセンサー値を辞書にまとめる。"""
    hue, saturation, value = read_hsv(color_sensor)
    roll, yaw, pitch = read_orientation(hub)

    return {
        "turn": 0.0,
        "speed": 0.0,
        "battery": read_battery(hub),
        "angleL": 0.0,
        "angleR": 0.0,
        "hue": hue,
        "saturation": saturation,
        "value": value,
        "Kp": 0.0,
        "Ki": 0.0,
        "Kd": 0.0,
        "roll": roll,
        "yaw": yaw,
        "pitch": pitch,
    }


hub = ThisHub()
color_sensor = ColorSensor(COLOR_SENSOR_PORT)
watch = StopWatch()

while True:
    elapsed_ms = watch.time()
    values = build_log_values(hub, color_sensor)
    stdout.write(format_log_line(elapsed_ms, values))
    wait(SEND_INTERVAL_MS)
