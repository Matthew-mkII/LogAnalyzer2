// SPDX-License-Identifier: MIT
/*
 * log_sender_app.c
 *
 * LogAnalyzer2 へセンサー値のみを BLE 送信するデモアプリ。
 * ライントレース・モーター制御は行いません。
 *
 * 動作:
 *   1. BLE 接続待ち（画面: READY）
 *   2. 10 ms 周期でバッテリー / IMU / カラーセンサー（Port E）を CSV 送信
 *   3. 約 60 秒後に "done" を送信して終了
 *
 * 外部プログラムから log_sender.h の API だけを使う場合は、
 * 本ファイルの main_task を参考にしてください。
 */

#include <kernel.h>
#include <t_syslog.h>

#include "kernel_cfg.h"
#include "log_sender.h"
#include "log_sender_app.h"

#include <spike/hub/battery.h>
#include <spike/hub/display.h>
#include <spike/pup/colorsensor.h>

/* 送信周期・回数（変更可） */
#define APP_INTERVAL_US 10000
#define APP_LOOP_COUNT  6000UL

/* カラーセンサー Port（未接続なら hue/saturation/value は 0） */
#define APP_COLOR_SENSOR_PORT PBIO_PORT_ID_E

static void app_wait_ble(log_sender_t *sender) {
  hub_display_off();
  hub_display_text_scroll("READY", 100);
  log_sender_open_ble(sender);
  hub_display_image_off();
}

void main_task(intptr_t exinf) {
  log_sender_t sender;
  pup_device_t *color_sensor;
  unsigned long i;

  (void)exinf;

  syslog(LOG_NOTICE, "LogAnalyzer2 log sender (SPIKE-RT) starting.");

  dly_tsk(1000000);

  log_sender_init(&sender);
  sender.imu_interval_us = APP_INTERVAL_US;

  app_wait_ble(&sender);

  color_sensor = pup_color_sensor_get_device((pbio_port_id_t)APP_COLOR_SENSOR_PORT);

  for (i = 0; i < APP_LOOP_COUNT; ++i) {
    log_sender_row_t row;
    pup_color_hsv_t hsv;

    log_sender_row_clear(&row);
    row.include_time = true;
    row.time_ms = log_sender_elapsed_ms(&sender);
    row.battery = (float)hub_battery_get_voltage();
    row.speed = 0.0f;
    row.turn = 0.0f;

    if (color_sensor != NULL) {
      hsv = pup_color_sensor_hsv(color_sensor, true);
      row.hue = (float)hsv.h;
      row.saturation = (float)hsv.s;
      row.value = (float)hsv.v;
    }

    log_sender_read_imu(&sender, &row, APP_INTERVAL_US);
    log_sender_send_row(&sender, &row);

    dly_tsk(APP_INTERVAL_US);
  }

  log_sender_send_raw(&sender, "done\n");
  hub_display_text_scroll("DONE", 100);
}
