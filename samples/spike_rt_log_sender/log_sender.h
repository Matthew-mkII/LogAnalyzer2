// SPDX-License-Identifier: MIT
/*
 * log_sender.h
 *
 * LogAnalyzer2 向け BLE（NUS）ログ送信モジュール。
 * ライントレース等の走行制御は含みません。
 *
 * CSV 列（LogAnalyzer2 互換）:
 *   time, turn, speed, battery, angleL, angleR,
 *   hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
 */
#ifndef LOG_SENDER_H
#define LOG_SENDER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include <kernel.h>

typedef enum {
  LOG_SENDER_OK = 0,
  LOG_SENDER_ERR_BLE,
} log_sender_result_t;

/* 1 行分のセンサー値。未使用列は 0 のままにできます。 */
typedef struct {
  bool include_time;
  unsigned long time_ms;

  float turn;
  float speed;
  float battery;
  float angleL;
  float angleR;
  float hue;
  float saturation;
  float value;
  float Kp;
  float Ki;
  float Kd;
  float roll;
  float yaw;
  float pitch;
} log_sender_row_t;

typedef struct {
  ER serial_open;
  SYSTIM start_ms;
  float yaw_angle;
  int imu_interval_us;
} log_sender_t;

void log_sender_row_clear(log_sender_row_t *row);

void log_sender_init(log_sender_t *self);

log_sender_result_t log_sender_open_ble(log_sender_t *self);

bool log_sender_is_connected(const log_sender_t *self);

unsigned long log_sender_elapsed_ms(const log_sender_t *self);

/*
 * LogAnalyzer2 形式の CSV 1 行を buffer に書き込む（末尾に \\n）。
 * 戻り値は書き込んだ文字数（snprintf 準拠）。負値はエラー。
 */
int log_sender_format_row(char *buffer, size_t buffer_size, const log_sender_row_t *row);

/* 接続中のみ BLE へ送信。未接続時は何もしません。 */
void log_sender_send_row(log_sender_t *self, const log_sender_row_t *row);

void log_sender_send_raw(log_sender_t *self, const char *line);

/*
 * row の roll / yaw / pitch を IMU から更新し、yaw は角速度積分します。
 * dt_us は前回送信からの周期 [µs]。
 */
void log_sender_read_imu(log_sender_t *self, log_sender_row_t *row, int dt_us);

#endif /* LOG_SENDER_H */
