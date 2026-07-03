# SPDX-License-Identifier: MIT
"""LogAnalyzer2 向けライントレース + ログ送信（Pybricks）

LineTracerOnOff（On/Off 制御）をベースに、走行中のセンサー値を usys.stdout 経由で送信します。

対象: SPIKE Prime / Robot Inventor 等（Pybricks firmware 3.3+、PrimeHub 想定）

配線（LineTracerOnOff と同じ）:
  Port A: 右モーター / Port B: 左モーター / Port C: アーム（未使用可）
  Port D: フォースセンサー（開始ボタン）/ Port E: カラーセンサー

使い方:
  1. 下の「設定」セクションで edge・ポート・走行パラメータを確認
  2. ハブに書き込み、Pybricks Code から切断（同時接続不可）
  3. LogAnalyzer2 でスキャン → 接続 → ハブでプログラム開始
  4. フォースセンサーを押して閾値測定 → もう一度押して走行開始

エッジの向き（左エッジ走行のイメージ）:
        ■
        ■
 (-1) <=== ■ ===> (1)
 LEFT   ■   RIGHT
        ■
        ■

注意:
  - BOOST Move Hub は usys 非対応のため動作しません
  - 姿勢角は hub.imu.tilt() と heading() を使用（orientation() は使わない）
"""

from pybricks.hubs import PrimeHub
from pybricks.parameters import Direction, Icon, Port
from pybricks.pupdevices import ColorSensor, ForceSensor, Motor
from pybricks.robotics import DriveBase
from pybricks.tools import StopWatch, wait
from usys import stdout

# =============================================================================
# 設定（環境に合わせてここを変更してください）
# =============================================================================

# --- ライントレース ---
LEFT_EDGE = 1
RIGHT_EDGE = -1

# 走行するラインの種類。左エッジなら LEFT_EDGE、右エッジなら RIGHT_EDGE
edge = LEFT_EDGE
# edge = RIGHT_EDGE

# 直進速度 [mm/s]（LogAnalyzer2 の speed 列にもこの値が入ります）
DRIVE_SPEED = 100
# On/Off 制御でラインを見つけた／外れたときの旋回指令 [deg/s]
STEER_ANGLE = 55
# 制御ループの待ち時間 [ms]。短いほど反応は速いが CPU 負荷が上がります
LOOP_WAIT_MS = 10
# ループ回数。LOOP_WAIT_MS と掛け合わせて最大走行時間になる（既定: 約 60 秒）
LOOP_COUNT = 6000

# --- ポート割り当て ---
MOTOR_RIGHT_PORT = Port.A
MOTOR_LEFT_PORT = Port.B
# MOTOR_ARM_PORT = Port.C  # アームモーターを使う場合はここを有効化
BUTTON_PORT = Port.D       # フォースセンサー（押下で閾値測定／走行開始）
COLOR_SENSOR_PORT = Port.E # ライン検出 + HSV ログ

# --- ロボット寸法（DriveBase 用。実機のタイヤ・軸距に合わせて調整） ---
WHEEL_DIAMETER_MM = 56
AXLE_TRACK_MM = 114

# LogAnalyzer2 の CSV 列順（先頭の time 列は format_log_line が付与）
# 列名を変えると LogAnalyzer2 側と不一致になるため、通常は変更不要です
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


# =============================================================================
# ログ送信（LogAnalyzer2 CSV 形式）
# =============================================================================


def format_number(value):
    """数値を CSV 用の文字列に変換する。None は空欄。"""
    if value is None:
        return ""
    value = float(value)
    if value == int(value):
        return str(int(value))
    return "{:.6f}".format(value)


def format_log_line(time_ms, values):
    """1 行分の CSV を組み立てる。末尾に改行を付けて stdout 向けに返す。"""
    fields = [format_number(time_ms)]
    for column in VALUE_COLUMNS:
        fields.append(format_number(values.get(column)))
    return ",".join(fields) + "\n"


def read_hsv(color_sensor):
    """カラーセンサーの HSV。読み取り失敗時は (None, None, None)。"""
    try:
        return color_sensor.hsv()
    except OSError:
        return None, None, None


def read_orientation(hub):
    """IMU から roll / yaw / pitch [deg] を取得。失敗時は (None, None, None)。"""
    try:
        pitch, roll = hub.imu.tilt()
        yaw = hub.imu.heading()
        return roll, yaw, pitch
    except (AttributeError, TypeError, ValueError):
        return None, None, None


def read_battery(hub):
    """バッテリー電圧 [mV]。取得できないハブでは None。"""
    try:
        return hub.battery.voltage()
    except AttributeError:
        return None


def build_log_values(hub, color_sensor, motor_l, motor_r, speed, turn):
    """走行中のセンサー値を辞書にまとめる（VALUE_COLUMNS の各キーに対応）。"""
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
        "Kp": 0.0,  # PID 制御を使う場合はここにゲインを入れる
        "Ki": 0.0,
        "Kd": 0.0,
        "roll": roll,
        "yaw": yaw,
        "pitch": pitch,
    }


# =============================================================================
# ライントレース制御
# =============================================================================


def wait_button_pressed(hub, button):
    """フォースセンサーが触れるまで待つ。検出時に短いビープを鳴らす。"""
    while True:
        if button.touched():
            hub.speaker.beep(frequency=880, duration=50)
            break
        wait(200)


def measure_threshold(color_sensor, samples=50):
    """反射光を複数回平均し、ライン上／床の境目判定用の閾値を求める。

    測定時はセンサーを走行予定の床面（ライン上またはライン外）に近づけた状態で
    ボタンを押してください。走行中は「反射光 > 閾値」をライン上とみなします。
    """
    total = 0
    for _ in range(samples):
        total += color_sensor.reflection()
        wait(20)
    return int(total / samples)


def steer_for_edge(on_line, edge_side):
    """On/Off 制御の旋回角（drive の turn 引数 [deg/s]）を返す。"""
    if on_line:
        return STEER_ANGLE if edge_side == LEFT_EDGE else -STEER_ANGLE
    return -STEER_ANGLE if edge_side == LEFT_EDGE else STEER_ANGLE


# =============================================================================
# メインプログラム
# =============================================================================

hub = PrimeHub()
motor_r = Motor(MOTOR_RIGHT_PORT, Direction.CLOCKWISE)
motor_l = Motor(MOTOR_LEFT_PORT, Direction.COUNTERCLOCKWISE)
button = ForceSensor(BUTTON_PORT)
color_sensor = ColorSensor(COLOR_SENSOR_PORT)

motor_l.reset_angle(0)
motor_r.reset_angle(0)

drive_base = DriveBase(motor_l, motor_r, WHEEL_DIAMETER_MM, AXLE_TRACK_MM)
watch = StopWatch()

# Phase 1: 閾値キャリブレーション（フォースセンサーを 1 回押す）
wait_button_pressed(hub, button)
threshold = measure_threshold(color_sensor)
hub.display.icon(Icon.LEFT if edge == LEFT_EDGE else Icon.RIGHT)

# Phase 2: ライントレース + ログ送信（もう一度押すと走行開始）
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
