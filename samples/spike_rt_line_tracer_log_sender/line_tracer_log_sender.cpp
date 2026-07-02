// SPDX-License-Identifier: MIT
/*
 * LogAnalyzer2 向け SPIKE-RT ライントレース + BLE ログ送信（C++）
 *
 * LineTracerOnOff（On/Off 制御）と LogAnalyzer2 CSV 形式を組み合わせたプログラムです。
 * Bluetooth シリアル（Pybricks NUS）で CSV 行を送信します。LogAnalyzer2 の NUS 受信に対応。
 *
 * 配線（Pybricks 版と同じ）:
 *   Port A: 右モーター / Port B: 左モーター
 *   Port D: フォースセンサー（開始ボタン）/ Port E: カラーセンサー
 *
 * 動作フロー:
 *   1. デバイス初期化 → BLE 接続待ち（画面: READY）
 *   2. フォースセンサー 1 回目: 反射光の平均で閾値を測定
 *   3. 画面に左/右エッジの矢印を表示
 *   4. フォースセンサー 2 回目: ライントレース開始（最大約 60 秒）
 *   5. 各ループで走行制御 + センサー値を Bluetooth 経由で CSV 送信
 *
 * ビルド:
 *   spike-rt-sample/API-sample/ に本フォルダをコピーし、make && make deploy-lin
 *   詳細は LogAnalyzer2 README の SPIKE-RT 節を参照。
 */

#include <kernel.h>
#include <t_syslog.h>

#include <cmath>
#include <cstdio>
#include <cstring>

#include "kernel_cfg.h"
#include "line_tracer_log_sender.h"

#include <syssvc/serial.h>
#include <spike/hub/battery.h>
#include <spike/hub/bluetooth.h>
#include <spike/hub/display.h>
#include <spike/hub/imu.h>
#include <spike/hub/speaker.h>
#include <spike/pup/colorsensor.h>
#include <spike/pup/forcesensor.h>
#include <spike/pup/motor.h>

namespace {

// ---------------------------------------------------------------------------
// ライントレース設定（環境に合わせて変更）
// ---------------------------------------------------------------------------

constexpr int kLeftEdge = 1;
constexpr int kRightEdge = -1;
constexpr int kEdge = kLeftEdge;  // 右エッジ走行時は kRightEdge に変更

/* 走行ループ: kLoopCount × kLoopWaitUs ≒ 6000 × 10ms = 60 秒 */
constexpr int kDriveSpeedDeg = 360;   // 各モーター基準速度 [°/秒]（pup_motor_set_speed）
constexpr int kSteerSpeedDeg = 220;   // On/Off 制御の左右速度差 [°/秒]
constexpr int kLoopWaitUs = 10000;    // 制御周期 10 ms（dly_tsk の引数はマイクロ秒）
constexpr unsigned long kLoopCount = 6000;

// ポート割り当て（Pybricks 版 pybricks_line_tracer_log_sender.py と同じ）
constexpr int kMotorRightPort = PBIO_PORT_ID_A;
constexpr int kMotorLeftPort = PBIO_PORT_ID_B;
constexpr int kButtonPort = PBIO_PORT_ID_D;
constexpr int kColorSensorPort = PBIO_PORT_ID_E;

// ---------------------------------------------------------------------------
// ハブ 5×5 LED マトリクス用アイコン（左/右エッジ表示）
// ---------------------------------------------------------------------------

static uint8_t kImgLeft[1][25] = {
    {0b0000000, 0b0000000, 0b1100100, 0b0000000, 0b0000000, 0b0000000,
     0b1100100, 0b1100100, 0b0000000, 0b0000000, 0b1100100, 0b1100100,
     0b1100100, 0b1100100, 0b1100100, 0b0000000, 0b1100100, 0b1100100,
     0b0000000, 0b0000000, 0b0000000, 0b0000000, 0b1100100, 0b0000000,
     0b0000000},
};

static uint8_t kImgRight[1][25] = {
    {0b0000000, 0b0000000, 0b1100100, 0b0000000, 0b0000000, 0b0000000,
     0b0000000, 0b1100100, 0b1100100, 0b0000000, 0b1100100, 0b1100100,
     0b1100100, 0b1100100, 0b1100100, 0b0000000, 0b0000000, 0b1100100,
     0b1100100, 0b0000000, 0b0000000, 0b0000000, 0b1100100, 0b0000000,
     0b0000000},
};

// ---------------------------------------------------------------------------
// グローバル状態（main_task のみから使用）
// ---------------------------------------------------------------------------

pup_motor_t *g_motor_right = nullptr;
pup_motor_t *g_motor_left = nullptr;
pup_device_t *g_color_sensor = nullptr;
pup_device_t *g_force_sensor = nullptr;

float g_yaw_angle = 0.0f;   // IMU 角速度の Z 軸積分（heading 相当）
ER g_serial_open = E_OBJ;     // Bluetooth シリアルポートのオープン結果

// ---------------------------------------------------------------------------
// デバイス初期化
// ---------------------------------------------------------------------------

/*
 * モーターをセットアップする。
 * pup_motor_setup は同一モーターに複数回呼ぶと不安定になるため、成功するまで最大 10 回リトライ。
 */
pbio_error_t setup_motor(pup_motor_t *motor, pup_direction_t direction) {
  for (int attempt = 0; attempt < 10; ++attempt) {
    const pbio_error_t err = pup_motor_setup(motor, direction, true);
    if (err != PBIO_ERROR_AGAIN) {
      return err;
    }
    dly_tsk(1000000);  // 1 秒待って再試行
  }
  return PBIO_ERROR_AGAIN;
}

/* IMU ドライバを初期化（失敗時はリトライ） */
bool init_imu() {
  while (hub_imu_init() == PBIO_ERROR_FAILED) {
    dly_tsk(100000);
  }
  return true;
}

// ---------------------------------------------------------------------------
// Bluetooth（LogAnalyzer2 連携）
// ---------------------------------------------------------------------------

/*
 * BLE 接続を待つ。serial_opn_por は内部でアドバタイジングを開始し、
 * PC（LogAnalyzer2）からの接続完了までブロックする。
 */
void wait_for_bluetooth() {
  hub_display_off();
  hub_display_text_scroll("READY", 100);

  if (g_serial_open != E_OK) {
    g_serial_open = serial_opn_por(SIO_BLUETOOTH_PORTID);
  }

  hub_display_image(kImgRight[0]);  // 接続完了の目印
}

/* 接続済みかつシリアルポートが開いているか */
bool bluetooth_ready() {
  bool connected = false;
  hub_bluetooth_is_connected(&connected);
  return connected && g_serial_open == E_OK;
}

/* CSV 1 行を Bluetooth（NUS）へ送信。未接続時は破棄 */
void write_bluetooth_line(const char *line) {
  if (!bluetooth_ready()) {
    return;
  }
  serial_wri_dat(SIO_BLUETOOTH_PORTID, line, static_cast<uint16_t>(strlen(line)));
}

// ---------------------------------------------------------------------------
// ユーザー操作（フォースセンサー）
// ---------------------------------------------------------------------------

/*
 * フォースセンサーのタッチを待つ。
 * 押下検出時にビープ音を鳴らし、離すまで待機（チャタリング防止）。
 */
void wait_force_pressed() {
  while (!pup_force_sensor_touched(g_force_sensor)) {
    dly_tsk(200000);  // 200 ms
  }
  hub_speaker_play_tone(static_cast<uint16_t>(NOTE_A5), 50);
  dly_tsk(50000);
  while (pup_force_sensor_touched(g_force_sensor)) {
    dly_tsk(10000);
  }
}

/*
 * カラーセンサーの反射光を複数回平均し、ライン/on 閾値を求める。
 * Pybricks 版 measure_threshold() と同じ考え方。
 */
int measure_threshold(int samples = 50) {
  long total = 0;
  for (int i = 0; i < samples; ++i) {
    total += pup_color_sensor_reflection(g_color_sensor);
    dly_tsk(20000);  // 20 ms 間隔
  }
  return static_cast<int>(total / samples);
}

// ---------------------------------------------------------------------------
// ライントレース制御（On/Off）
// ---------------------------------------------------------------------------

/*
 * On/Off 制御の旋回指令を返す。
 * on_line: 反射光が閾値より大きい（ライン上）かどうか
 * 戻り値: 左右モーター速度差 [°/秒]（drive() に渡す）
 */
int steer_for_edge(bool on_line) {
  if (on_line) {
    return (kEdge == kLeftEdge) ? kSteerSpeedDeg : -kSteerSpeedDeg;
  }
  return (kEdge == kLeftEdge) ? -kSteerSpeedDeg : kSteerSpeedDeg;
}

/*
 * 左右モーターを差動駆動する。
 * turn > 0 で左モーター加速・右モーター減速（左旋回）。
 */
void drive(int turn) {
  const int left = kDriveSpeedDeg + turn;
  const int right = kDriveSpeedDeg - turn;
  pup_motor_set_speed(g_motor_left, left);
  pup_motor_set_speed(g_motor_right, right);
}

void brake_motors() {
  pup_motor_brake(g_motor_left);
  pup_motor_brake(g_motor_right);
}

// ---------------------------------------------------------------------------
// センサー読み取り（ログ用）
// ---------------------------------------------------------------------------

/*
 * 姿勢角を推定する。
 * roll / pitch: 加速度ベクトルから算出（静止時に有効）
 * yaw: Z 軸角速度を積分（imu4 サンプルと同様のノイズ除去あり）
 *
 * 注意: Pybricks の tilt() / heading() とは算出方法が異なる場合があります。
 */
void read_orientation(float *roll, float *yaw, float *pitch) {
  float accel[3];
  hub_imu_get_acceleration(accel);

  const float ax = accel[0];
  const float ay = accel[1];
  const float az = accel[2];
  const float denom = sqrtf(ay * ay + az * az);

  *pitch = atan2f(-ax, denom) * 180.0f / static_cast<float>(M_PI);
  *roll = atan2f(ay, az) * 180.0f / static_cast<float>(M_PI);
  *yaw = g_yaw_angle;

  float angv[3];
  hub_imu_get_angular_velocity(angv);
  float wz = angv[2];
  /* ハブ静止時の角速度ノイズ（約 ±1 °/s）をゼロ扱い */
  if (wz > -1.0f && wz < 1.0f) {
    wz = 0.0f;
  }
  g_yaw_angle += wz * (static_cast<float>(kLoopWaitUs) / 1000000.0f);
}

// ---------------------------------------------------------------------------
// LogAnalyzer2 CSV 形式
// ---------------------------------------------------------------------------

/*
 * LogAnalyzer2 の CSV 1 行を組み立てる。
 * 列順: time, turn, speed, battery, angleL, angleR,
 *       hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
 * speed 列は Pybricks 版と同様に 100 固定。Kp/Ki/Kd は未使用で 0。
 */
void format_log_line(
    char *buffer,
    size_t buffer_size,
    unsigned long time_ms,
    int turn,
    int battery_mv,
    int angle_left,
    int angle_right,
    int hue,
    int saturation,
    int value,
    float roll,
    float yaw,
    float pitch) {
  snprintf(
      buffer,
      buffer_size,
      "%lu,%d,%d,%d,%d,%d,%d,%d,%d,0,0,0,%.6f,%.6f,%.6f\n",
      time_ms,
      turn,
      100,  // speed 列（Pybricks DriveBase の DRIVE_SPEED と揃える）
      battery_mv,
      angle_left,
      angle_right,
      hue,
      saturation,
      value,
      roll,
      yaw,
      pitch);
}

/* 走行開始時刻からの経過時間 [ms] */
unsigned long elapsed_ms(unsigned long start_ms) {
  SYSTIM now = 0;
  get_tim(&now);
  return static_cast<unsigned long>(now) - start_ms;
}

}  // namespace

// ---------------------------------------------------------------------------
// SPIKE-RT メインタスク（カーネル起動時に TA_ACT で自動実行）
// ---------------------------------------------------------------------------

void main_task(intptr_t /*exinf*/) {
  syslog(LOG_NOTICE, "LogAnalyzer2 line tracer (SPIKE-RT) starting.");

  /* センサー・モーターの電源安定待ち（3 秒） */
  dly_tsk(3000000);

  // --- デバイス取得 ---
  g_motor_right = pup_motor_get_device(static_cast<pbio_port_id_t>(kMotorRightPort));
  g_motor_left = pup_motor_get_device(static_cast<pbio_port_id_t>(kMotorLeftPort));
  g_color_sensor = pup_color_sensor_get_device(static_cast<pbio_port_id_t>(kColorSensorPort));
  g_force_sensor = pup_force_sensor_get_device(static_cast<pbio_port_id_t>(kButtonPort));

  if (g_motor_right == nullptr || g_motor_left == nullptr || g_color_sensor == nullptr ||
      g_force_sensor == nullptr) {
    hub_display_text_scroll("NO DEV", 100);
    return;
  }

  if (setup_motor(g_motor_right, PUP_DIRECTION_CLOCKWISE) != PBIO_SUCCESS ||
      setup_motor(g_motor_left, PUP_DIRECTION_COUNTERCLOCKWISE) != PBIO_SUCCESS) {
    hub_display_text_scroll("MOTOR?", 100);
    return;
  }

  init_imu();

  // --- Phase 1: BLE 接続待ち（LogAnalyzer2 でスキャン → 接続） ---
  wait_for_bluetooth();

  // --- Phase 2: 閾値キャリブレーション ---
  wait_force_pressed();
  const int threshold = measure_threshold();
  hub_display_image((kEdge == kLeftEdge) ? kImgLeft[0] : kImgRight[0]);

  // --- Phase 3: ライントレース + ログ送信 ---
  wait_force_pressed();

  SYSTIM start_ms = 0;
  get_tim(&start_ms);
  g_yaw_angle = 0.0f;

  for (unsigned long i = 0; i < kLoopCount; ++i) {
    const int reflection = pup_color_sensor_reflection(g_color_sensor);
    const bool on_line = reflection > threshold;
    const int turn = steer_for_edge(on_line);

    drive(turn);

    const pup_color_hsv_t hsv = pup_color_sensor_hsv(g_color_sensor, true);
    float roll = 0.0f;
    float yaw = 0.0f;
    float pitch = 0.0f;
    read_orientation(&roll, &yaw, &pitch);

    char line[192];
    format_log_line(
        line,
        sizeof(line),
        elapsed_ms(static_cast<unsigned long>(start_ms)),
        turn,
        hub_battery_get_voltage(),
        pup_motor_get_count(g_motor_left),
        pup_motor_get_count(g_motor_right),
        hsv.h,
        hsv.s,
        hsv.v,
        roll,
        yaw,
        pitch);
    write_bluetooth_line(line);

    dly_tsk(kLoopWaitUs);
  }

  brake_motors();
  write_bluetooth_line("done\n");
}
