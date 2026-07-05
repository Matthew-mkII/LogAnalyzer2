# SPIKE-RT ログ送信サンプル（C）

[LogAnalyzer2](https://github.com/matthew/LogAnalyzer2) へセンサー値だけを Bluetooth（NUS）で送信する SPIKE-RT 用 C サンプルです。

ライントレースやモーター制御は行いません。走行しながらログを送る例は [`../spike_rt_line_tracer_log_sender/`](../spike_rt_line_tracer_log_sender/) を参照してください。

## 概要

| 項目 | 内容 |
|------|------|
| 対象ハブ | SPIKE Prime（[SPIKE-RT](https://github.com/spike-rt/spike-rt) ファームウェア書き込み済み） |
| 通信 | Pybricks 互換 Bluetooth シリアル（Nordic UART Service） |
| 送信形式 | LogAnalyzer2 互換 CSV（1 行 1 レコード、末尾改行） |
| デモ動作 | `READY` 表示 → BLE 接続後 10 ms 周期で送信 → 約 60 秒後に `done` で終了 |

### 送信する CSV 列

```
time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
```

デモでは次の値を送信します。

| 列 | デモでの内容 |
|----|-------------|
| `time` | 起動からの経過時間 [ms] |
| `turn`, `speed` | 0（走行制御なし） |
| `battery` | バッテリー電圧 [mV] |
| `angleL`, `angleR` | 0 |
| `hue`, `saturation`, `value` | Port E のカラーセンサー（未接続時は 0） |
| `Kp`, `Ki`, `Kd` | 0 |
| `roll`, `yaw`, `pitch` | IMU から算出 |

## ファイル構成

```
spike_rt_log_sender/
├── README.md              # 本ドキュメント
├── log_sender.h           # ログ送信 API（外部アプリから再利用可）
├── log_sender.c           # API 実装（BLE / CSV 整形 / IMU 読み取り）
├── log_sender_app.h       # カーネルタスク設定（.cfg から include）
├── log_sender_app.c       # デモ用 main_task
├── log_sender.cfg         # TOPPERS/ASP タスク定義
├── log_sender.cdl         # Bluetooth シリアル有効化（etrobo 互換）
├── Makefile
└── install_to_spike_rt_sample.sh
```

## 前提環境

1. [spike-rt](https://github.com/spike-rt/spike-rt) と [spike-rt-sample](https://github.com/Hiyama1026/spike-rt-sample) をクローン済み
2. SPIKE-RT のビルド環境（`arm-none-eabi-gcc` 等）が整っていること
3. PC 側で [LogAnalyzer2](../../README.md) が起動できること

etrobo 環境を使う場合、`spike-rt-sample` は `spike-rt/spike-rt-sample` 配下に置きます（`etrobo` 直下ではありません）。

## ビルドと書き込み

### 1. spike-rt-sample へ配置

LogAnalyzer2 リポジトリ内から:

```bash
./samples/spike_rt_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
```

例（etrobo 環境）:

```bash
./samples/spike_rt_log_sender/install_to_spike_rt_sample.sh \
  $HOME/SPIKE-RT/etrobo/spike-rt/spike-rt-sample
```

### 2. ビルド

```bash
cd /path/to/spike-rt-sample/API-sample/log_sender
make
```

成功すると `asp.bin` が生成されます。

### 3. ハブへ書き込み

ハブを DFU モードにして USB 接続したうえで:

```bash
make deploy-lin    # Linux / WSL
# macOS の場合は spike-rt-sample の手順に従い deploy-win 等を使用
```

## LogAnalyzer2 での受信手順

1. PC で LogAnalyzer2 を起動
2. ハブの電源を入れる（画面に `READY` が表示される）
3. LogAnalyzer2 で **スキャン** → ハブを選択 → **接続**
4. 接続後、グラフと `logs/*.csv` にデータが記録される
5. 約 60 秒後、ハブ画面に `DONE` が表示され、送信が終了する

## `log_sender_app.c` のカスタマイズ

デモの動作は `log_sender_app.c` 先頭のマクロで変更できます。

```c
#define APP_INTERVAL_US 10000      /* 送信周期 [µs]。10000 = 10 ms */
#define APP_LOOP_COUNT  6000UL     /* 送信回数。6000 × 10 ms ≒ 60 秒 */
#define APP_COLOR_SENSOR_PORT PBIO_PORT_ID_E
```

| 変更したい内容 | 編集箇所 |
|----------------|----------|
| 送信周期 | `APP_INTERVAL_US` |
| 送信時間 | `APP_LOOP_COUNT`（`回数 × 周期` で概算） |
| カラーセンサーのポート | `APP_COLOR_SENSOR_PORT` |
| 独自のセンサー値を送る | `main_task` 内の `log_sender_row_t row` の各フィールドを設定してから `log_sender_send_row()` を呼ぶ |

ループ内で独自の値を送る例:

```c
log_sender_row_clear(&row);
row.include_time = true;
row.time_ms = log_sender_elapsed_ms(&sender);
row.turn = 55.0f;
row.speed = 100.0f;
row.angleL = left_motor_angle;
row.angleR = right_motor_angle;
log_sender_read_imu(&sender, &row, APP_INTERVAL_US);
log_sender_send_row(&sender, &row);
```

## 外部アプリから API だけ使う

走行制御など別の SPIKE-RT アプリに組み込む場合は、`log_sender.h` / `log_sender.c` をプロジェクトに追加してビルドします。

```c
#include "log_sender.h"

log_sender_t sender;
log_sender_row_t row;

log_sender_init(&sender);
log_sender_open_ble(&sender);

log_sender_row_clear(&row);
row.include_time = true;
row.time_ms = log_sender_elapsed_ms(&sender);
row.battery = (float)hub_battery_get_voltage();
log_sender_read_imu(&sender, &row, 10000);
log_sender_send_row(&sender, &row);
```

### 主な API

| 関数 | 説明 |
|------|------|
| `log_sender_init()` | 内部状態を初期化 |
| `log_sender_open_ble()` | IMU 初期化と Bluetooth シリアルオープン |
| `log_sender_is_connected()` | BLE 接続状態 |
| `log_sender_elapsed_ms()` | 起動からの経過時間 [ms] |
| `log_sender_row_clear()` | 1 行分のデータを 0 クリア |
| `log_sender_read_imu()` | `roll` / `yaw` / `pitch` を IMU から更新 |
| `log_sender_send_row()` | CSV 1 行を BLE 送信（未接続時は何もしない） |
| `log_sender_send_raw()` | 任意の文字列を送信（例: `"done\n"`） |

`Makefile` で `log_sender_app.o` の代わりに自分の `main_task` を含むソースをビルドし、`.cfg` の `main_task` 宣言を合わせてください。

## 注意事項

- SPIKE-RT は LEGO 公式ファームウェアを置き換えます。元に戻すには公式ファームウェアの再書き込みが必要です
- `battery` は mV 単位です（`hub_battery_get_voltage()` の戻り値）
- IMU の `yaw` は角速度積分、`roll` / `pitch` は加速度から算出します（Pybricks の `tilt()` / `heading()` とは算出方法が異なる場合があります）
- `log_sender_send_row()` は BLE 未接続時には送信しません。接続後にループを回してください
- `log_sender.cdl` は etrobo 向け SPIKE-RT では `SerialPortUART_F` を無効化しています

## 関連ドキュメント

- [LogAnalyzer2 README（全体）](../../README.md)
- [ライントレース + ログ送信サンプル](../spike_rt_line_tracer_log_sender/)
