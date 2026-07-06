# SPIKE-RT 向け LogAnalyzer2 ログ送信プログラム

LEGO SPIKE Prime ハブで SPIKE-RT (TOPPERS/ASP) を使用し、C++ でライントレーサーを実装しながら LogAnalyzer2 へリアルタイムでログを送信するサンプルです。

## ファイル

| ファイル | 内容 |
|---------|------|
| `spike_rt_log_sender.cpp` | 基本的なログ送信の実装例 |
| `spike_rt_line_tracer.cpp` | PID 制御によるライントレーサー + ログ送信 |

## 環境構築

### 1. SPIKE-RT のインストール

```bash
# SPIKE-RT SDK をクローン
git clone https://github.com/spike-rt/spike-rt.git
cd spike-rt

# 依存パッケージのインストール（Ubuntu/Debian の場合）
sudo apt install gcc-arm-none-eabi build-essential python3 python3-pip
pip3 install pyusb
```

### 2. プロジェクトの作成

```bash
# SPIKE-RT のワークスペースに移動
cd workspace

# 新しいプロジェクトを作成
mkdir line_tracer_logger
cd line_tracer_logger

# サンプルファイルをコピー
cp /path/to/spike_rt_line_tracer.cpp app.cpp
```

### 3. Makefile の編集

`Makefile` を作成または編集:

```makefile
APPL = line_tracer_logger
SRCS = app.cpp

# SPIKE-RT のパスを指定
SPIKE_RT_PATH = ../..

include $(SPIKE_RT_PATH)/target/spike/Makefile.app
```

## ビルドと書き込み

### ビルド

```bash
make
```

### ハブへの書き込み

1. SPIKE Prime ハブを USB ケーブルで PC に接続
2. ハブを DFU モードにする（中央ボタン + Bluetooth ボタンを同時に長押し）
3. 書き込み実行:

```bash
make upload
```

または:

```bash
make deploy
```

## 使い方

### 基本的なログ送信（`spike_rt_log_sender.cpp`）

1. ハブにプログラムを書き込む
2. ハブの電源を入れる（プログラムが自動起動）
3. LogAnalyzer2 を起動
4. **スキャン** → ハブを選択 → **接続**
5. グラフにリアルタイムでデータが表示される

### ライントレーサー（`spike_rt_line_tracer.cpp`）

#### 接続

| ポート | デバイス |
|--------|----------|
| Port B | 左モーター |
| Port C | 右モーター |
| Port E | カラーセンサー |

#### 操作

1. プログラムを書き込んで起動（ディスプレイに `RDY` 表示）
2. LogAnalyzer2 で BLE 接続
3. ハブの **中央ボタン** を押して走行開始（`GO` 表示）
4. もう一度押すと停止（`STP` 表示）
5. LogAnalyzer2 でリアルタイムグラフ表示 + CSV 自動保存

## 送信データ形式

CSV 形式（15 列）:

```csv
time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
```

| 列名 | 内容 | 単位 |
|------|------|------|
| `time` | 経過時間 | ms |
| `turn` | 操舵量 | - |
| `speed` | 速度 | - |
| `battery` | バッテリー電圧 | mV |
| `angleL` | 左モーター角度 | deg |
| `angleR` | 右モーター角度 | deg |
| `hue` | カラーセンサー色相 | - |
| `saturation` | カラーセンサー彩度 | - |
| `value` | カラーセンサー明度 | - |
| `Kp` | PID 比例ゲイン | - |
| `Ki` | PID 積分ゲイン | - |
| `Kd` | PID 微分ゲイン | - |
| `roll` | ロール角 | deg |
| `yaw` | ヨー角 | deg |
| `pitch` | ピッチ角 | deg |

## PID パラメータの調整

`spike_rt_line_tracer.cpp` の以下の定数を変更:

```cpp
#define TARGET_BRIGHTNESS    50.0f   // 目標輝度（0-100）
#define BASE_SPEED          50.0f    // 基本速度

#define KP_DEFAULT          0.8f     // 比例ゲイン
#define KI_DEFAULT          0.05f    // 積分ゲイン
#define KD_DEFAULT          0.15f    // 微分ゲイン
```

### 調整のヒント

| 症状 | 対策 |
|------|------|
| 蛇行が激しい | `KP` を小さく、`KD` を大きく |
| ラインから外れる | `KP` を大きく |
| 定常偏差がある | `KI` を少し増やす |
| 振動する | `KD` を小さく |
| 速度が遅い | `BASE_SPEED` を大きく |

LogAnalyzer2 の CSV ログを Excel 等で開いて、グラフを見ながら調整すると効果的です。

## Bluetooth API について

### BLE データ送信

```cpp
#include "spike/hub/bluetooth.h"

// 初期化（通常は自動で行われる）
hub_bluetooth_init();

// データ送信（NUS 経由）
char data[] = "100,0.5,50.0,7971,...\n";
hub_bluetooth_send((uint8_t*)data, strlen(data));
```

SPIKE-RT では Nordic UART Service (NUS) が自動的に有効化されるため、特別な設定なしで LogAnalyzer2 と接続できます。

## トラブルシューティング

### BLE 接続できない

- Pybricks Code など他のアプリが接続していないか確認
- ハブを再起動（電源ボタン長押し）
- LogAnalyzer2 でスキャン → 接続を再試行

### センサー値が取得できない

- ポート番号が正しいか確認
- センサーがしっかり接続されているか確認
- `pup_color_sensor_get_device()` の戻り値が NULL でないか確認

### コンパイルエラー

- SPIKE-RT SDK のバージョンを確認（最新版を推奨）
- ヘッダーファイルのパスが正しいか確認
- Makefile の設定を確認

## 参考資料

- [SPIKE-RT 公式ドキュメント](https://spike-rt.github.io/)
- [TOPPERS/ASP カーネル仕様書](https://www.toppers.jp/asp-kernel.html)
- [LogAnalyzer2 README](../README.md)

## ライセンス

MIT License

## 注意事項

- SPIKE-RT は LEGO Education SPIKE Prime 向けの非公式ファームウェアです
- ハブに書き込むと、公式ファームウェアは上書きされます
- 公式ファームウェアに戻すには、LEGO Education SPIKE アプリから復元できます
