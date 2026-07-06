// SPDX-License-Identifier: MIT
/**
 * LogAnalyzer2 向けライントレーサー（SPIKE-RT / C++）
 * 
 * PID制御によるライントレース + リアルタイムログ送信
 * 
 * 接続:
 *   Port B: 左モーター
 *   Port C: 右モーター
 *   Port E: カラーセンサー
 * 
 * 動作:
 *   1. 中央ボタンで開始/停止
 *   2. LogAnalyzer2でBLE接続してログ表示
 *   3. CSV自動保存でデータ分析
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
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
}

// --- 設定 ---
#define COLOR_SENSOR_PORT    PUP_PORT_E
#define LEFT_MOTOR_PORT      PUP_PORT_B
#define RIGHT_MOTOR_PORT     PUP_PORT_C

#define SEND_INTERVAL_MS     50      // ログ送信間隔
#define CONTROL_INTERVAL_MS  10      // 制御周期

#define TARGET_BRIGHTNESS    50.0f   // 目標輝度（白と黒の中間）
#define BASE_SPEED          50.0f    // 基本速度

// PIDゲイン（要調整）
#define KP_DEFAULT          0.8f
#define KI_DEFAULT          0.05f
#define KD_DEFAULT          0.15f

// --- グローバル変数 ---
static pup_device_t *color_sensor = NULL;
static pup_device_t *left_motor = NULL;
static pup_device_t *right_motor = NULL;

static char send_buffer[256];
static uint32_t start_time_ms = 0;
static uint32_t last_send_time = 0;

// PID制御変数
static float pid_integral = 0.0f;
static float pid_last_error = 0.0f;
static float kp = KP_DEFAULT;
static float ki = KI_DEFAULT;
static float kd = KD_DEFAULT;

// 制御状態
static bool running = false;
static float current_turn = 0.0f;
static float current_speed = 0.0f;

/**
 * カラーセンサーから輝度を取得
 */
static float get_brightness() {
    if (color_sensor == NULL) {
        return 50.0f;
    }
    
    pup_color_hsv_t hsv;
    if (pup_color_sensor_hsv(color_sensor, &hsv) == PBIO_SUCCESS) {
        return hsv.v;  // V (Value) を輝度として使用
    }
    
    return 50.0f;
}

/**
 * PID制御による操舵量計算
 */
static float calculate_pid_turn(float error, float dt_sec) {
    // 比例項
    float p_term = kp * error;
    
    // 積分項
    pid_integral += error * dt_sec;
    // 積分巻き上げ防止
    if (pid_integral > 100.0f) pid_integral = 100.0f;
    if (pid_integral < -100.0f) pid_integral = -100.0f;
    float i_term = ki * pid_integral;
    
    // 微分項
    float d_term = 0.0f;
    if (dt_sec > 0.0001f) {
        d_term = kd * (error - pid_last_error) / dt_sec;
    }
    pid_last_error = error;
    
    return p_term + i_term + d_term;
}

/**
 * モーター制御
 */
static void set_motor_power(float left_power, float right_power) {
    if (left_motor != NULL) {
        // パワーを-100〜100に制限
        if (left_power > 100.0f) left_power = 100.0f;
        if (left_power < -100.0f) left_power = -100.0f;
        pup_motor_set_power(left_motor, (int)left_power);
    }
    
    if (right_motor != NULL) {
        if (right_power > 100.0f) right_power = 100.0f;
        if (right_power < -100.0f) right_power = -100.0f;
        pup_motor_set_power(right_motor, (int)right_power);
    }
}

/**
 * ログ送信（簡易版）
 */
static void send_log_data() {
    uint32_t elapsed_ms = hub_system_get_time_ms() - start_time_ms;
    
    // センサー値取得
    float hue = 0.0f, saturation = 0.0f, value = 0.0f;
    bool hsv_valid = false;
    if (color_sensor != NULL) {
        pup_color_hsv_t hsv;
        if (pup_color_sensor_hsv(color_sensor, &hsv) == PBIO_SUCCESS) {
            hue = hsv.h;
            saturation = hsv.s;
            value = hsv.v;
            hsv_valid = true;
        }
    }
    
    float roll = 0.0f, yaw = 0.0f, pitch = 0.0f;
    bool imu_valid = false;
    float tilt[2];
    float heading;
    if (hub_imu_get_tilt(tilt) == PBIO_SUCCESS && 
        hub_imu_get_heading(&heading) == PBIO_SUCCESS) {
        pitch = tilt[0];
        roll = tilt[1];
        yaw = heading;
        imu_valid = true;
    }
    
    float angle_l = 0.0f, angle_r = 0.0f;
    bool angle_l_valid = false, angle_r_valid = false;
    if (left_motor != NULL) {
        int32_t angle;
        if (pup_motor_get_angle(left_motor, &angle) == PBIO_SUCCESS) {
            angle_l = (float)angle;
            angle_l_valid = true;
        }
    }
    if (right_motor != NULL) {
        int32_t angle;
        if (pup_motor_get_angle(right_motor, &angle) == PBIO_SUCCESS) {
            angle_r = (float)angle;
            angle_r_valid = true;
        }
    }
    
    int32_t battery_mv;
    float battery = 0.0f;
    bool battery_valid = false;
    if (hub_battery_get_voltage(&battery_mv) == PBIO_SUCCESS) {
        battery = (float)battery_mv;
        battery_valid = true;
    }
    
    // CSV行を生成（簡易版）
    snprintf(send_buffer, sizeof(send_buffer),
             "%u,%.2f,%.2f,%s,%s,%s,%s,%s,%s,%.6f,%.6f,%.6f,%s,%s,%s\n",
             elapsed_ms,
             current_turn,
             current_speed,
             battery_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.0f", battery)) : "",
             angle_l_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", angle_l)) : "",
             angle_r_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", angle_r)) : "",
             hsv_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", hue)) : "",
             hsv_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", saturation)) : "",
             hsv_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", value)) : "",
             kp, ki, kd,
             imu_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", roll)) : "",
             imu_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", yaw)) : "",
             imu_valid ? (char*)(&(char[32]){0} + sprintf((char[32]){0}, "%.2f", pitch)) : ""
    );
    
    // より安全なバージョン
    int pos = 0;
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%u,", elapsed_ms);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.2f,", current_turn);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.2f,", current_speed);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,", 
                    battery_valid ? (snprintf((char[32]){}, 32, "%.0f", battery), (char[32]){}) : "");
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,",
                    angle_l_valid ? (snprintf((char[32]){}, 32, "%.2f", angle_l), (char[32]){}) : "");
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%s,",
                    angle_r_valid ? (snprintf((char[32]){}, 32, "%.2f", angle_r), (char[32]){}) : "");
    
    // 簡略化バージョン（実用的）
    char tmp[32];
    pos = 0;
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%u,", elapsed_ms);
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.2f,%.2f,", 
                    current_turn, current_speed);
    
    if (battery_valid) {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.0f,", battery);
    } else {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, ",");
    }
    
    if (angle_l_valid) {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.2f,", angle_l);
    } else {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, ",");
    }
    
    if (angle_r_valid) {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, "%.2f,", angle_r);
    } else {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, ",");
    }
    
    if (hsv_valid) {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, 
                        "%.2f,%.2f,%.2f,", hue, saturation, value);
    } else {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, ",,,");
    }
    
    pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, 
                    "%.6f,%.6f,%.6f,", kp, ki, kd);
    
    if (imu_valid) {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, 
                        "%.2f,%.2f,%.2f\n", roll, yaw, pitch);
    } else {
        pos += snprintf(send_buffer + pos, sizeof(send_buffer) - pos, ",,\n");
    }
    
    // BLE送信
    hub_bluetooth_send((uint8_t*)send_buffer, strlen(send_buffer));
}

/**
 * 制御タスク
 */
void control_task(intptr_t unused) {
    // デバイス初期化
    color_sensor = pup_color_sensor_get_device(COLOR_SENSOR_PORT);
    left_motor = pup_motor_get_device(LEFT_MOTOR_PORT);
    right_motor = pup_motor_get_device(RIGHT_MOTOR_PORT);
    hub_imu_init();
    
    start_time_ms = hub_system_get_time_ms();
    last_send_time = start_time_ms;
    
    hub_display_text("RDY", 1);
    
    uint32_t last_control_time = start_time_ms;
    
    while (1) {
        uint32_t now = hub_system_get_time_ms();
        
        // ボタン処理
        if (hub_button_is_pressed(HUB_BUTTON_CENTER)) {
            running = !running;
            pid_integral = 0.0f;
            pid_last_error = 0.0f;
            
            if (running) {
                hub_display_text("GO", 1);
            } else {
                hub_display_text("STP", 1);
                set_motor_power(0.0f, 0.0f);
            }
            
            tslp_tsk(300);  // チャタリング防止
        }
        
        // 制御処理
        if (running && (now - last_control_time >= CONTROL_INTERVAL_MS)) {
            float dt = (now - last_control_time) / 1000.0f;
            last_control_time = now;
            
            // 輝度取得
            float brightness = get_brightness();
            
            // 誤差計算
            float error = TARGET_BRIGHTNESS - brightness;
            
            // PID制御
            current_turn = calculate_pid_turn(error, dt);
            current_speed = BASE_SPEED;
            
            // モーター出力計算
            float left_power = current_speed + current_turn;
            float right_power = current_speed - current_turn;
            
            // モーター制御
            set_motor_power(left_power, right_power);
        }
        
        // ログ送信
        if (now - last_send_time >= SEND_INTERVAL_MS) {
            last_send_time = now;
            send_log_data();
        }
        
        tslp_tsk(5);  // 短い待機
    }
}
