// SPDX-License-Identifier: MIT
/*
 * LogAnalyzer2 向け SPIKE-RT ライントレース + BLE ログ送信（C）
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

#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "kernel_cfg.h"
#include "line_tracer_log_sender.h"

#include <syssvc/serial.h>
#include "serial/serial.h"
#include <spike/hub/battery.h>
#include <spike/hub/bluetooth.h>
#include <spike/hub/display.h>
#include <spike/hub/imu.h>
#include <spike/hub/speaker.h>
#include <spike/pup/colorsensor.h>
#include <spike/pup/forcesensor.h>
#include <spike/pup/motor.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// ---------------------------------------------------------------------------
// ライントレース設定（環境に合わせて変更）
// ---------------------------------------------------------------------------

#define K_LEFT_EDGE 1
#define K_RIGHT_EDGE (-1)
#define K_EDGE K_LEFT_EDGE /* 右エッジ走行時は K_RIGHT_EDGE に変更 */

/* 走行ループ: K_LOOP_COUNT × K_LOOP_WAIT_US ≒ 6000 × 10ms = 60 秒 */
#define K_DRIVE_SPEED_DEG 360 /* 各モーター基準速度 [°/秒]（pup_motor_set_speed） */
#define K_STEER_SPEED_DEG 220 /* On/Off 制御の左右速度差 [°/秒] */
#define K_LOOP_WAIT_US 10000 /* 制御周期 10 ms（dly_tsk の引数はマイクロ秒） */
#define K_LOOP_COUNT 6000UL

/* ポート割り当て（Pybricks 版 pybricks_line_tracer_log_sender.py と同じ） */
#define K_MOTOR_RIGHT_PORT PBIO_PORT_ID_A
#define K_MOTOR_LEFT_PORT PBIO_PORT_ID_B
#define K_BUTTON_PORT PBIO_PORT_ID_D
#define K_COLOR_SENSOR_PORT PBIO_PORT_ID_E

// ---------------------------------------------------------------------------
// ハブ 5×5 LED マトリクス用アイコン（左/右エッジ表示）
// ---------------------------------------------------------------------------

static uint8_t k_img_left[1][25] = {
    {0b0000000, 0b0000000, 0b1100100, 0b0000000, 0b0000000, 0b0000000,
     0b1100100, 0b1100100, 0b0000000, 0b0000000, 0b1100100, 0b1100100,
     0b1100100, 0b1100100, 0b1100100, 0b0000000, 0b1100100, 0b1100100,
     0b0000000, 0b0000000, 0b0000000, 0b0000000, 0b1100100, 0b0000000,
     0b0000000},
};

static uint8_t k_img_right[1][25] = {
    {0b0000000, 0b0000000, 0b1100100, 0b0000000, 0b0000000, 0b0000000,
     0b0000000, 0b1100100, 0b1100100, 0b0000000, 0b1100100, 0b1100100,
     0b1100100, 0b1100100, 0b1100100, 0b0000000, 0b0000000, 0b1100100,
     0b1100100, 0b0000000, 0b0000000, 0b0000000, 0b1100100, 0b0000000,
     0b0000000},
};

// ---------------------------------------------------------------------------
// グローバル状態（main_task のみから使用）
// ---------------------------------------------------------------------------

static pup_motor_t *g_motor_right = NULL;
static pup_motor_t *g_motor_left = NULL;
static pup_device_t *g_color_sensor = NULL;
static pup_device_t *g_force_sensor = NULL;

static float g_yaw_angle = 0.0f; /* IMU 角速度の Z 軸積分（heading 相当） */
static ER g_serial_open = E_OBJ; /* Bluetooth シリアルポートのオープン結果 */

// ---------------------------------------------------------------------------
// デバイス初期化
// ---------------------------------------------------------------------------

/*
 * モーターをセットアップする。
 * pup_motor_setup は同一モーターに複数回呼ぶと不安定になるため、成功するまで最大 10 回リトライ。
 */
static pbio_error_t setup_motor(pup_motor_t *motor, pup_direction_t direction) {
  int attempt;

  for (attempt = 0; attempt < 10; ++attempt) {
    const pbio_error_t err = pup_motor_setup(motor, direction, true);
    if (err != PBIO_ERROR_AGAIN) {
      return err;
    }
    dly_tsk(1000000); /* 1 秒待って再試行 */
  }
  return PBIO_ERROR_AGAIN;
}

/* IMU ドライバを初期化（失敗時はリトライ） */
static void init_imu(void) {
  while (hub_imu_init() == PBIO_ERROR_FAILED) {
    dly_tsk(100000);
  }
}

// ---------------------------------------------------------------------------
// Bluetooth（LogAnalyzer2 連携）
// ---------------------------------------------------------------------------

/*
 * BLE 接続を待つ。serial_opn_por は内部でアドバタイジングを開始し、
 * PC（LogAnalyzer2）からの接続完了までブロックする。
 */
static void wait_for_bluetooth(void) {
  hub_display_off();
  hub_display_text_scroll("READY", 100);

  if (g_serial_open != E_OK) {
    g_serial_open = serial_opn_por(SIO_BLUETOOTH_PORTID);
  }

  hub_display_image(k_img_right[0]); /* 接続完了の目印 */
}

/* 接続済みかつシリアルポートが開いているか */
static bool bluetooth_ready(void) {
  bool connected = false;
  hub_bluetooth_is_connected(&connected);
  return connected && g_serial_open == E_OK;
}

/* CSV 1 行を Bluetooth（NUS）へ送信。未接続時は破棄 */
static void write_bluetooth_line(const char *line) {
  if (!bluetooth_ready()) {
    return;
  }
  serial_wri_dat(SIO_BLUETOOTH_PORTID, line, (uint16_t)strlen(line));
}

// ---------------------------------------------------------------------------
// ユーザー操作（フォースセンサー）
// ---------------------------------------------------------------------------

/*
 * フォースセンサーのタッチを待つ。
 * 押下検出時にビープ音を鳴らし、離すまで待機（チャタリング防止）。
 */
static void wait_force_pressed(void) {
  while (!pup_force_sensor_touched(g_force_sensor)) {
    dly_tsk(200000); /* 200 ms */
  }
  hub_speaker_play_tone((uint16_t)NOTE_A5, 50);
  dly_tsk(50000);
  while (pup_force_sensor_touched(g_force_sensor)) {
    dly_tsk(10000);
  }
}

/*
 * カラーセンサーの反射光を複数回平均し、ライン/on 閾値を求める。
 * Pybricks 版 measure_threshold() と同じ考え方。
 */
static int measure_threshold(int samples) {
  long total = 0;
  int i;

  for (i = 0; i < samples; ++i) {
    total += pup_color_sensor_reflection(g_color_sensor);
    dly_tsk(20000); /* 20 ms 間隔 */
  }
  return (int)(total / samples);
}

// ---------------------------------------------------------------------------
// ライントレース制御（On/Off）
// ---------------------------------------------------------------------------

/*
 * On/Off 制御の旋回指令を返す。
 * on_line: 反射光が閾値より大きい（ライン上）かどうか
 * 戻り値: 左右モーター速度差 [°/秒]（drive() に渡す）
 */
static int steer_for_edge(bool on_line) {
  if (on_line) {
    return (K_EDGE == K_LEFT_EDGE) ? K_STEER_SPEED_DEG : -K_STEER_SPEED_DEG;
  }
  return (K_EDGE == K_LEFT_EDGE) ? -K_STEER_SPEED_DEG : K_STEER_SPEED_DEG;
}

/*
 * 左右モーターを差動駆動する。
 * turn > 0 で左モーター加速・右モーター減速（左旋回）。
 */
static void drive(int turn) {
  const int left = K_DRIVE_SPEED_DEG + turn;
  const int right = K_DRIVE_SPEED_DEG - turn;
  pup_motor_set_speed(g_motor_left, left);
  pup_motor_set_speed(g_motor_right, right);
}

static void brake_motors(void) {
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
static void read_orientation(float *roll, float *yaw, float *pitch) {
  float accel[3];
  float ax;
  float ay;
  float az;
  float denom;
  float angv[3];
  float wz;

  hub_imu_get_acceleration(accel);

  ax = accel[0];
  ay = accel[1];
  az = accel[2];
  denom = sqrtf(ay * ay + az * az);

  *pitch = atan2f(-ax, denom) * 180.0f / (float)M_PI;
  *roll = atan2f(ay, az) * 180.0f / (float)M_PI;
  *yaw = g_yaw_angle;

  hub_imu_get_angular_velocity(angv);
  wz = angv[2];
  /* ハブ静止時の角速度ノイズ（約 ±1 °/s）をゼロ扱い */
  if (wz > -1.0f && wz < 1.0f) {
    wz = 0.0f;
  }
  g_yaw_angle += wz * ((float)K_LOOP_WAIT_US / 1000000.0f);
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
static void format_log_line(
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
      100, /* speed 列（Pybricks DriveBase の DRIVE_SPEED と揃える） */
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
static unsigned long elapsed_ms(unsigned long start_ms) {
  SYSTIM now = 0;
  get_tim(&now);
  return (unsigned long)now - start_ms;
}

// ---------------------------------------------------------------------------
// SPIKE-RT メインタスク（カーネル起動時に TA_ACT で自動実行）
// ---------------------------------------------------------------------------

void main_task(intptr_t exinf) {
  int threshold;
  unsigned long i;
  SYSTIM start_ms = 0;

  (void)exinf;

  syslog(LOG_NOTICE, "LogAnalyzer2 line tracer (SPIKE-RT) starting.");

  /* センサー・モーターの電源安定待ち（3 秒） */
  dly_tsk(3000000);

  /* デバイス取得 */
  g_motor_right = pup_motor_get_device((pbio_port_id_t)K_MOTOR_RIGHT_PORT);
  g_motor_left = pup_motor_get_device((pbio_port_id_t)K_MOTOR_LEFT_PORT);
  g_color_sensor = pup_color_sensor_get_device((pbio_port_id_t)K_COLOR_SENSOR_PORT);
  g_force_sensor = pup_force_sensor_get_device((pbio_port_id_t)K_BUTTON_PORT);

  if (g_motor_right == NULL || g_motor_left == NULL || g_color_sensor == NULL ||
      g_force_sensor == NULL) {
    hub_display_text_scroll("NO DEV", 100);
    return;
  }

  if (setup_motor(g_motor_right, PUP_DIRECTION_CLOCKWISE) != PBIO_SUCCESS ||
      setup_motor(g_motor_left, PUP_DIRECTION_COUNTERCLOCKWISE) != PBIO_SUCCESS) {
    hub_display_text_scroll("MOTOR?", 100);
    return;
  }

  init_imu();

  /* Phase 1: BLE 接続待ち（LogAnalyzer2 でスキャン → 接続） */
  wait_for_bluetooth();

  /* Phase 2: 閾値キャリブレーション */
  wait_force_pressed();
  threshold = measure_threshold(50);
  hub_display_image((K_EDGE == K_LEFT_EDGE) ? k_img_left[0] : k_img_right[0]);

  /* Phase 3: ライントレース + ログ送信 */
  wait_force_pressed();

  get_tim(&start_ms);
  g_yaw_angle = 0.0f;

  for (i = 0; i < K_LOOP_COUNT; ++i) {
    const int reflection = pup_color_sensor_reflection(g_color_sensor);
    const bool on_line = reflection > threshold;
    const int turn = steer_for_edge(on_line);
    const pup_color_hsv_t hsv = pup_color_sensor_hsv(g_color_sensor, true);
    float roll = 0.0f;
    float yaw = 0.0f;
    float pitch = 0.0f;
    char line[192];

    drive(turn);
    read_orientation(&roll, &yaw, &pitch);
    format_log_line(
        line,
        sizeof(line),
        elapsed_ms((unsigned long)start_ms),
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

    dly_tsk(K_LOOP_WAIT_US);
  }

  brake_motors();
  write_bluetooth_line("done\n");
}
