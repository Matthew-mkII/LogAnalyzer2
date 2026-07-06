// SPDX-License-Identifier: MIT
/**
 * LogAnalyzer2 向けログ送信（SPIKE-RT / C++）
 * 
 * 対象: LEGO SPIKE Prime ハブ + SPIKE-RT (TOPPERS/ASP)
 * 
 * 使い方:
 *   1. SPIKE-RT 開発環境をセットアップ
 *   2. 本ファイルをプロジェクトに追加してビルド
 *   3. ハブに書き込み、実行
 *   4. LogAnalyzer2 でスキャン → 接続
 * 
 * 送信: BLE 経由で NUS (Nordic UART Service) を使用
 * フォーマット: CSV (time, turn, speed, battery, angleL, angleR, 
 *                    hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch)
 */

#include <stdio.h>
#include <string.h>
#include "spike/hub/display.h"
#include "spike/hub/button.h"
#include "spike/hub/battery.h"
#include "spike/hub/imu.h"
#include "spike/pup/colorsensor.h"
#include "spike/pup/motor.h"
#include "spike/pup/ultrasonicsensor.h"
#include "spike/hub/bluetooth.h"

extern "C" {
#include "kernel.h"
#include "kernel_id.h"
}

// --- 設定 ---
#define COLOR_SENSOR_PORT    PUP_PORT_E
#define LEFT_MOTOR_PORT      PUP_PORT_B
#define RIGHT_MOTOR_PORT     PUP_PORT_C
#define SEND_INTERVAL_MS     100

// Bluetoothデバイス名の設定
// 注意: SPIKE-RT API にはランタイムで名前を変更する関数がありません。
// 以下のいずれかの方法で名前を設定してください：
//
// 方法1: LEGO公式アプリで事前に設定（推奨）
//   - LEGO Education SPIKE アプリでハブに接続
//   - ハブ設定から名前を変更（例: "LineTracer-01"）
//   - SPIKE-RTファームウェアを書き込んでも名前は保持される
//
// 方法2: pbioライブラリの内部変数を操作（非公式、推奨しない）
//   - extern char pbdrv_bluetooth_hub_name[16];
//   - strncpy(pbdrv_bluetooth_hub_name, "MyRobot", 15);
//   - 互換性の問題が発生する可能性あり
//
// 方法3: ファームウェアビルド時に変更（要SPIKE-RTソース修正）
//   - lib/pbio/drv/bluetooth/bluetooth_stm32_cc2640.c の
//     pbdrv_bluetooth_hub_name のデフォルト値を変更

// --- グローバル変数 ---
static pup_device_t *color_sensor = NULL;
static pup_device_t *left_motor = NULL;
static pup_device_t *right_motor = NULL;
static char send_buffer[256];
static uint32_t start_time_ms = 0;

/**
 * 数値を文字列に変換（整数の場合は小数点なし）
 */
static void format_number(char *buf, size_t size, float value, bool is_valid) {
    if (!is_valid) {
        buf[0] = '\0';
        return;
    }
    
    if (value == (int)value) {
        snprintf(buf, size, "%d", (int)value);
    } else {
        snprintf(buf, size, "%.6f", value);
    }
}

/**
 * HSV値を取得
 */
static void get_hsv(float *hue, float *saturation, float *value, bool *valid) {
    *valid = false;
    
    if (color_sensor == NULL) {
        return;
    }
    
    pup_color_hsv_t hsv;
    if (pup_color_sensor_hsv(color_sensor, &hsv) == PBIO_SUCCESS) {
        *hue = hsv.h;
        *saturation = hsv.s;
        *value = hsv.v;
        *valid = true;
    }
}

/**
 * IMU姿勢角を取得（roll, yaw, pitch）
 */
static void get_orientation(float *roll, float *yaw, float *pitch, bool *valid) {
    *valid = false;
    
    float tilt[2];  // pitch, roll
    float heading;
    
    if (hub_imu_get_tilt(tilt) == PBIO_SUCCESS && 
        hub_imu_get_heading(&heading) == PBIO_SUCCESS) {
        *pitch = tilt[0];
        *roll = tilt[1];
        *yaw = heading;
        *valid = true;
    }
}

/**
 * モーター角度を取得
 */
static void get_motor_angles(float *angle_l, float *angle_r, 
                             bool *valid_l, bool *valid_r) {
    *valid_l = false;
    *valid_r = false;
    
    if (left_motor != NULL) {
        int32_t angle;
        if (pup_motor_get_angle(left_motor, &angle) == PBIO_SUCCESS) {
            *angle_l = (float)angle;
            *valid_l = true;
        }
    }
    
    if (right_motor != NULL) {
        int32_t angle;
        if (pup_motor_get_angle(right_motor, &angle) == PBIO_SUCCESS) {
            *angle_r = (float)angle;
            *valid_r = true;
        }
    }
}

/**
 * バッテリー電圧を取得（mV）
 */
static void get_battery_voltage(float *voltage, bool *valid) {
    *valid = false;
    
    int32_t voltage_mv;
    if (hub_battery_get_voltage(&voltage_mv) == PBIO_SUCCESS) {
        *voltage = (float)voltage_mv;
        *valid = true;
    }
}

/**
 * ログ行を生成して送信
 */
static void send_log_line(float turn, float speed, 
                         float kp, float ki, float kd) {
    uint32_t elapsed_ms = hub_system_get_time_ms() - start_time_ms;
    
    // センサー値を取得
    float hue, saturation, value;
    bool hsv_valid;
    get_hsv(&hue, &saturation, &value, &hsv_valid);
    
    float roll, yaw, pitch;
    bool orientation_valid;
    get_orientation(&roll, &yaw, &pitch, &orientation_valid);
    
    float angle_l, angle_r;
    bool angle_l_valid, angle_r_valid;
    get_motor_angles(&angle_l, &angle_r, &angle_l_valid, &angle_r_valid);
    
    float battery;
    bool battery_valid;
    get_battery_voltage(&battery, &battery_valid);
    
    // CSV行を組み立て
    char time_str[32];
    snprintf(time_str, sizeof(time_str), "%u", elapsed_ms);
    
    char buf[32];
    int pos = 0;
    
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", time_str);
    
    // turn
    format_number(buf, sizeof(buf), turn, true);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // speed
    format_number(buf, sizeof(buf), speed, true);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // battery
    format_number(buf, sizeof(buf), battery, battery_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // angleL
    format_number(buf, sizeof(buf), angle_l, angle_l_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // angleR
    format_number(buf, sizeof(buf), angle_r, angle_r_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // hue
    format_number(buf, sizeof(buf), hue, hsv_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // saturation
    format_number(buf, sizeof(buf), saturation, hsv_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // value
    format_number(buf, sizeof(buf), value, hsv_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // Kp
    format_number(buf, sizeof(buf), kp, true);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // Ki
    format_number(buf, sizeof(buf), ki, true);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // Kd
    format_number(buf, sizeof(buf), kd, true);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // roll
    format_number(buf, sizeof(buf), roll, orientation_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // yaw
    format_number(buf, sizeof(buf), yaw, orientation_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", buf);
    
    // pitch
    format_number(buf, sizeof(buf), pitch, orientation_valid);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s\n", buf);
    
    // BLE経由で送信
    hub_bluetooth_send((uint8_t*)send_buffer, strlen(send_buffer));
}

/**
 * デバイスの初期化
 */
static void init_devices() {
    // カラーセンサー
    color_sensor = pup_color_sensor_get_device(COLOR_SENSOR_PORT);
    
    // モーター
    left_motor = pup_motor_get_device(LEFT_MOTOR_PORT);
    right_motor = pup_motor_get_device(RIGHT_MOTOR_PORT);
    
    // IMU初期化
    hub_imu_init();
}

/**
 * メインタスク
 */
void log_sender_task(intptr_t unused) {
    // デバイス初期化
    init_devices();
    
    // 開始時刻を記録
    start_time_ms = hub_system_get_time_ms();
    
    // ディスプレイに表示
    hub_display_text("LOG", 1);
    
    // ライントレーサーのパラメータ（例）
    float kp = 0.5f;
    float ki = 0.0f;
    float kd = 0.1f;
    
    // メインループ
    while (1) {
        // ここに実際のライントレーサー制御を実装
        // 以下は固定値の例
        float turn = 0.0f;
        float speed = 0.0f;
        
        // ログ送信
        send_log_line(turn, speed, kp, ki, kd);
        
        // 待機
        tslp_tsk(SEND_INTERVAL_MS);
    }
}
