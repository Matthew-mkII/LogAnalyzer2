// SPDX-License-Identifier: MIT
/**
 * LogAnalyzer2 向けログ送信（カスタムデバイス名版）
 * 
 * pbio内部変数を使用してBluetoothデバイス名を変更します。
 * 注意: 非公式の方法であり、SPIKE-RTのバージョンアップで動作しなくなる可能性があります。
 * 
 * 推奨: LEGO公式アプリで事前にデバイス名を設定する方法
 */

#include <stdio.h>
#include <string.h>
#include "spike/hub/display.h"
#include "spike/hub/button.h"
#include "spike/hub/battery.h"
#include "spike/hub/imu.h"
#include "spike/pup/colorsensor.h"
#include "spike/pup/motor.h"
#include "spike/hub/bluetooth.h"

extern "C" {
#include "kernel.h"
#include "kernel_id.h"

// pbioライブラリの内部変数（非公式）
// 警告: SPIKE-RTのバージョンによっては使用できない可能性があります
extern char pbdrv_bluetooth_hub_name[16];
}

// --- 設定 ---
#define COLOR_SENSOR_PORT    PUP_PORT_E
#define LEFT_MOTOR_PORT      PUP_PORT_B
#define RIGHT_MOTOR_PORT     PUP_PORT_C
#define SEND_INTERVAL_MS     100

// カスタムデバイス名（最大15文字）
#define CUSTOM_DEVICE_NAME   "LineTracer-A"

// --- グローバル変数 ---
static pup_device_t *color_sensor = NULL;
static pup_device_t *left_motor = NULL;
static pup_device_t *right_motor = NULL;
static char send_buffer[256];
static uint32_t start_time_ms = 0;

/**
 * Bluetoothデバイス名を設定
 * 
 * 注意: この関数はpbioの内部変数を直接操作します。
 * SPIKE-RTの公式APIではありません。
 */
static void set_bluetooth_device_name(const char *name) {
    if (name == NULL || strlen(name) == 0) {
        return;
    }
    
    // 最大15文字 + NULL終端
    strncpy(pbdrv_bluetooth_hub_name, name, 15);
    pbdrv_bluetooth_hub_name[15] = '\0';
    
    // デバッグ: ディスプレイに確認表示
    hub_display_text("NAME", 1);
    tslp_tsk(1000);
}

/**
 * デバイスの初期化
 */
static void init_devices() {
    // ★ Bluetoothデバイス名を設定（アドバタイジング開始前に実行）
    set_bluetooth_device_name(CUSTOM_DEVICE_NAME);
    
    // カラーセンサー
    color_sensor = pup_color_sensor_get_device(COLOR_SENSOR_PORT);
    
    // モーター
    left_motor = pup_motor_get_device(LEFT_MOTOR_PORT);
    right_motor = pup_motor_get_device(RIGHT_MOTOR_PORT);
    
    // IMU初期化
    hub_imu_init();
}

/**
 * ログ送信（簡易版）
 */
static void send_log_data() {
    uint32_t elapsed_ms = hub_system_get_time_ms() - start_time_ms;
    
    // センサー値取得
    float hue = 0.0f, saturation = 0.0f, value = 0.0f;
    if (color_sensor != NULL) {
        pup_color_hsv_t hsv;
        if (pup_color_sensor_hsv(color_sensor, &hsv) == PBIO_SUCCESS) {
            hue = hsv.h;
            saturation = hsv.s;
            value = hsv.v;
        }
    }
    
    float roll = 0.0f, yaw = 0.0f, pitch = 0.0f;
    float tilt[2];
    float heading;
    if (hub_imu_get_tilt(tilt) == PBIO_SUCCESS && 
        hub_imu_get_heading(&heading) == PBIO_SUCCESS) {
        pitch = tilt[0];
        roll = tilt[1];
        yaw = heading;
    }
    
    int32_t battery_mv;
    float battery = 0.0f;
    if (hub_battery_get_voltage(&battery_mv) == PBIO_SUCCESS) {
        battery = (float)battery_mv;
    }
    
    // CSV行を生成
    snprintf(send_buffer, sizeof(send_buffer),
             "%u,0,0,%.0f,0,0,%.2f,%.2f,%.2f,0,0,0,%.2f,%.2f,%.2f\n",
             elapsed_ms, battery, hue, saturation, value, roll, yaw, pitch);
    
    // BLE送信
    hub_bluetooth_send((uint8_t*)send_buffer, strlen(send_buffer));
}

/**
 * メインタスク
 */
void log_sender_task(intptr_t unused) {
    // デバイス初期化（Bluetooth名も設定）
    init_devices();
    
    // 開始時刻を記録
    start_time_ms = hub_system_get_time_ms();
    
    // ディスプレイに表示
    hub_display_text("LOG", 1);
    
    // メインループ
    while (1) {
        // ログ送信
        send_log_data();
        
        // 待機
        tslp_tsk(SEND_INTERVAL_MS);
    }
}
