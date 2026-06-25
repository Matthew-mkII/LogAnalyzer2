# SPDX-License-Identifier: MIT
"""LogAnalyzer2 向けログ送信（Pybricks）

対象: SPIKE Prime / Robot Inventor / Technic Hub 等（Pybricks firmware 3.3+）

センサー:
  - カラーセンサー（外付け）→ angleL=h, angleR=s, bright=v（HSV 生値）
  - ジャイロセンサー（ラージハブ内蔵）→ gyro 列（角速度 deg/s）

配線:
  SPIKE カラーセンサーを COLOR_SENSOR_PORT に接続してください。
  ジャイロは SPIKE Prime ラージハブに内蔵されているため、追加配線は不要です。
  Pybricks では hub.imu 経由で読み取ります。

使い方:
  1. 下の COLOR_SENSOR_PORT / GYRO_AXIS を環境に合わせて変更
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
from pybricks.parameters import Axis, Port
from pybricks.pupdevices import ColorSensor
from pybricks.tools import StopWatch, wait

from usys import stdout

# --- センサー設定（お使いのロボットに合わせて変更） ---
COLOR_SENSOR_PORT = Port.E
GYRO_AXIS = Axis.Z  # ヨー角速度。ピッチ=Axis.X、ロール=Axis.Y

SEND_INTERVAL_MS = 100

# LogAnalyzer2 レガシー CSV と同じ列順
VALUE_COLUMNS = (
    "turn",
    "speed",
    "battery",
    "angleL",
    "angleR",
    "bright",
    "gyro",
    "Kp",
    "Ki",
    "Kd",
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
    # MicroPython では str.encode() が使えない場合があるため stdout.write を使う
    stdout.write(line)


def read_hsv(color_sensor):
    """カラーセンサーの HSV 生値 (h, s, v) を読む。"""
    try:
        return color_sensor.hsv()
    except OSError:
        return None


def read_gyro(hub):
    """ラージハブ内蔵ジャイロセンサーの角速度（deg/s）を読む。"""
    try:
        return hub.imu.angular_velocity(GYRO_AXIS)
    except AttributeError:
        return None


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

    line = format_log_line(
        time_ms=elapsed_ms,
        values={
            "turn": 0.0,
            "speed": 0.0,
            "battery": read_battery(hub),
            "angleL": hue,
            "angleR": saturation,
            "bright": value,
            "gyro": read_gyro(hub),
            "Kp": 0.0,
            "Ki": 0.0,
            "Kd": 0.0,
        },
    )
    send_log_line(line)

    wait(SEND_INTERVAL_MS)
