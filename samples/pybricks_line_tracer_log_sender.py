# SPDX-License-Identifier: MIT
"""LogAnalyzer2 向けライントレース + ログ送信（Pybricks）

LineTracerOnOff（On/Off 制御）をベースに、走行中のセンサー値を usys.stdout 経由で送信します。

配線（LineTracerOnOff と同じ）:
  Port A: 右モーター / Port B: 左モーター / Port C: アーム（未使用可）
  Port D: フォースセンサー（開始ボタン）/ Port E: カラーセンサー

使い方:
  1. edge（LEFT_EDGE / RIGHT_EDGE）とポートを環境に合わせて確認
  2. ハブに書き込み、Pybricks Code から切断
  3. LogAnalyzer2 でスキャン → 接続 → ハブでプログラム開始
  4. フォースセンサーを押して閾値測定 → もう一度押して走行開始

        ■
        ■
 (-1) <=== ■ ===> (1)
 LEFT   ■   RIGHT
        ■
        ■
"""

from pybricks.hubs import PrimeHub
from pybricks.parameters import Direction, Icon, Port
from pybricks.pupdevices import ColorSensor, ForceSensor, Motor
from pybricks.robotics import DriveBase
from pybricks.tools import StopWatch, wait
from usys import stdout

# --- ライントレース設定 ---
LEFT_EDGE = 1
RIGHT_EDGE = -1

edge = LEFT_EDGE
# edge = RIGHT_EDGE

DRIVE_SPEED = 100
STEER_ANGLE = 55
LOOP_WAIT_MS = 10
LOOP_COUNT = 6000

MOTOR_RIGHT_PORT = Port.A
MOTOR_LEFT_PORT = Port.B
# MOTOR_ARM_PORT = Port.C
BUTTON_PORT = Port.D
COLOR_SENSOR_PORT = Port.E

WHEEL_DIAMETER_MM = 56
AXLE_TRACK_MM = 114

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
    if value is None:
        return ""
    value = float(value)
    if value == int(value):
        return str(int(value))
    return "{:.6f}".format(value)


def format_log_line(time_ms, values):
    fields = [format_number(time_ms)]
    for column in VALUE_COLUMNS:
        fields.append(format_number(values.get(column)))
    return ",".join(fields) + "\n"


def read_hsv(color_sensor):
    try:
        return color_sensor.hsv()
    except OSError:
        return None, None, None


def read_orientation(hub):
    try:
        pitch, roll = hub.imu.tilt()
        yaw = hub.imu.heading()
        return roll, yaw, pitch
    except (AttributeError, TypeError, ValueError):
        return None, None, None


def read_battery(hub):
    try:
        return hub.battery.voltage()
    except AttributeError:
        return None


def build_log_values(hub, color_sensor, motor_l, motor_r, speed, turn):
    hue, saturation, value = read_hsv(color_sensor)
    roll, yaw, pitch = read_orientation(hub)

    return {
        "turn": turn,
        "speed": speed,
        "battery": read_battery(hub),
        "angleL": motor_l.angle(),
        "angleR": motor_r.angle(),
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


def wait_button_pressed(hub, button):
    while True:
        if button.touched():
            hub.speaker.beep(frequency=880, duration=50)
            break
        wait(200)


def measure_threshold(color_sensor, samples=50):
    total = 0
    for _ in range(samples):
        total += color_sensor.reflection()
        wait(20)
    return int(total / samples)


def steer_for_edge(on_line, edge_side):
    """On/Off 制御の旋回角（drive の turn 引数）を返す。"""
    if on_line:
        return STEER_ANGLE if edge_side == LEFT_EDGE else -STEER_ANGLE
    return -STEER_ANGLE if edge_side == LEFT_EDGE else STEER_ANGLE


hub = PrimeHub()
motor_r = Motor(MOTOR_RIGHT_PORT, Direction.CLOCKWISE)
motor_l = Motor(MOTOR_LEFT_PORT, Direction.COUNTERCLOCKWISE)
button = ForceSensor(BUTTON_PORT)
color_sensor = ColorSensor(COLOR_SENSOR_PORT)

motor_l.reset_angle(0)
motor_r.reset_angle(0)

drive_base = DriveBase(motor_l, motor_r, WHEEL_DIAMETER_MM, AXLE_TRACK_MM)
watch = StopWatch()

wait_button_pressed(hub, button)
threshold = measure_threshold(color_sensor)
hub.display.icon(Icon.LEFT if edge == LEFT_EDGE else Icon.RIGHT)

wait_button_pressed(hub, button)

for _ in range(LOOP_COUNT):
    on_line = color_sensor.reflection() > threshold
    turn = steer_for_edge(on_line, edge)
    drive_base.drive(DRIVE_SPEED, turn)

    values = build_log_values(
        hub, color_sensor, motor_l, motor_r, DRIVE_SPEED, turn
    )
    stdout.write(format_log_line(watch.time(), values))

    wait(LOOP_WAIT_MS)

drive_base.brake()
