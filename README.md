# LogAnalyzer2

## 概要

PySide6 と Plotly を使ったグラフ描画アプリです。Bluetooth Low Energy（BLE）経由でデバイスから受信したデータをリアルタイムで折れ線グラフに表示し、受信ログを CSV ファイルに自動保存します。保存済みの CSV ログからもグラフを再表示できます。

## 環境構築

```bash
python -m venv la2
source la2/bin/activate
pip install -r requirements.txt
```

主な依存パッケージ:

- PySide6 / PySide6-WebEngine … GUI とグラフ表示
- Plotly … グラフ描画
- bleak … BLE 通信
- qasync … PySide6 と asyncio の統合

## 起動方法

```bash
source la2/bin/activate
python main.py
```

ウィンドウが開くと、上部に Bluetooth 操作パネルとログ操作パネル、中央に系列チェックボックス（データ受信時・CSV 読み込み時）、下部にグラフ表示エリアが表示されます。

## Windows 向け exe 化（PyInstaller）

`.exe` のビルドは **Windows 上** で行ってください（PyInstaller は基本的にビルド元 OS 向けの実行ファイルを生成します）。

### 手順（Windows）

1. [Python 3](https://www.python.org/downloads/) をインストールします。
2. プロジェクトフォルダで `build_windows.bat` を実行します。

```bat
build_windows.bat
```

または手動で:

```bat
python -m venv la2
la2\Scripts\activate
pip install -r requirements-build.txt
pyinstaller --noconfirm LogAnalyzer2.spec
```

3. 完了後、`dist\LogAnalyzer2\LogAnalyzer2.exe` が生成されます。

### 配布方法

- **`dist\LogAnalyzer2` フォルダごと** 配布してください（exe 単体では動作しません）。
- 初回起動時に exe と同じ場所に `logs\` フォルダが自動作成され、CSV ログが保存されます。
- グラフ描画用の `temp.html` も exe と同じフォルダに生成されます。

### 関連ファイル

| ファイル | 内容 |
|---------|------|
| `LogAnalyzer2.spec` | PyInstaller 設定 |
| `requirements-build.txt` | ビルド用依存（PyInstaller 含む） |
| `build_windows.bat` | Windows 向けビルドスクリプト |
| `app_paths.py` | 開発時・exe 化後のパス解決 |
| `runtime_hook_qtwebengine.py` | Qt WebEngine 用ランタイムフック |

### 注意

- PySide6 + Qt WebEngine を含むため、配布フォルダのサイズは数百 MB 程度になります。
- フォルダ配布形式（onedir）を採用しています。onefile（単一 exe）は Qt WebEngine との相性問題があるため非推奨です。
- Windows Defender 等が初回実行を警告する場合があります（コード署名未実施のため）。
- BLE 利用には Windows 10 以降と Bluetooth 対応環境が必要です。

## 使い方

### 1. デバイスをスキャンする

1. **スキャン** ボタンをクリックします。
2. 約 5 秒間、近くの BLE デバイスを検索します。
3. 見つかったデバイスがプルダウンリストに表示されます。
4. 右端のステータス表示に検出台数が表示されます。

### 2. デバイスに接続する

1. プルダウンリストから接続したいデバイスを選択します。
2. **接続** ボタンをクリックします。
3. 接続が成功すると、ステータスが「接続済み: （アドレス）」に変わります。
4. 接続中は **スキャン** ボタンは無効になります。

### 3. データをグラフ表示する

- 接続先デバイスからデータが送られると、自動的に折れ線グラフが更新されます。
- グラフの横軸は **経過時間（ms）**、縦軸は各系列の数値です。
- 横軸は **先頭データを 0 ms** として表示されます（デバイス側が `time` 列を送る場合はその値を使用）。
- データがまだない場合は「データ待機中...」と表示されます。
- グラフは 200ms 間隔で更新されます。
- 初回データ受信後、グラフ上部に **10 系列のチェックボックス**（`turn`, `speed`, `battery`, …）が表示されます。初期状態では `gyro` のみ ON です。
- 列の値が null（空欄・非数値）の点は、グラフ上で欠損として表示されます（線が途切れます）。

### 4. 接続を切断する

**切断（ログ書き込み）** ボタンをクリックすると、BLE 接続が終了します。記録中のログファイルが保存されます。

### 5. ログをファイルに保存する

Bluetooth 接続中に受信したデータは、自動的に CSV ファイルへ記録されます。手動での保存操作は不要です。

#### 記録の開始・終了

| タイミング | 動作 |
|-----------|------|
| **接続** 時 | `logs/` フォルダに新しい CSV ファイルを作成し、記録を開始 |
| データ受信時 | 受信データをリアルタイムで CSV に追記 |
| **切断** 時 | ファイルを閉じて保存完了 |

画面上のログ表示ラベルで、記録中のファイル名や保存完了を確認できます。

- 記録中: `ログ記録中: logs/log_YYYYMMDD_HHMMSS.csv`
- 保存完了: `ログ保存済み: logs/log_YYYYMMDD_HHMMSS.csv`
- 書き込み失敗: `ログ: 記録エラー（書き込み停止）`
- 保存失敗: `ログ: 保存エラー`

#### 保存先とファイル名

- 保存先: プロジェクト直下の `logs/` フォルダ（存在しない場合は自動作成）
- ファイル名: `log_YYYYMMDD_HHMMSS.csv`
  - 例: `log_20260618_120000.csv`

#### ログファイル形式

Bluetooth 接続中に自動保存される CSV は、LogAnalyzer 2015 等と同様の **レガシー形式** です。`#` で始まる行はコメントとして扱われ、データ行はカンマ区切りの数値列です。本アプリが保存するファイルでは、コメント行は列名の 1 行のみです。

##### ファイル構成

| 行 | 内容 |
|----|------|
| 1 行目 | `# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd` — データ列名 |
| 2 行目以降 | データ行（ヘッダー行はありません） |

LogAnalyzer 2015 等が出力した既存ログには、`# THRESHOLD= ...` や `# Speed = ...` などの追加コメント行が含まれる場合があります。**CSVからグラフ** ではこれらも `#` 行として無視して読み込みます。

##### データ列

| 列名 | 内容 |
|------|------|
| `time` | 経過時間（ms）。デバイスが `time` 列を送らない場合は接続開始からの経過時間。整数値の場合は小数点なし |
| `turn` | 旋回量 |
| `speed` | 速度 |
| `battery` | バッテリー電圧 |
| `angleL` | 左モーター角度 |
| `angleR` | 右モーター角度 |
| `bright` | 明るさ |
| `gyro` | ジャイロ値 |
| `Kp`, `Ki`, `Kd` | PID パラメータ |

##### null（欠損値）の扱い

Bluetooth 受信行のパース時、次の場合は該当列を **null** として扱います。

| 条件 | 挙動 |
|------|------|
| 列数が 10 未満 | 不足列を null でパディング |
| 数値に変換できない列 | その列のみ null |
| 11 列以上で先頭列が非数値 | `time` を null とみなし、接続開始からの経過 ms を使用 |

CSV への記録では null は **空欄** として出力します。**CSVからグラフ** で読み込む際も空欄は null として解釈されます。

##### 記録例（Bluetooth 受信時の自動保存）

完全な 11 列（`time` + 10 データ列）:

```csv
# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd
315,-45.000000,10.000000,7971,0.000000,0.000000,0.090000,44.000000,0.000000,0.000000,0.000000
318,-45.000000,10.000000,7970,0.000000,0.000000,0.100000,46.000000,0.000000,0.000000,0.000000
```

列不足・欠損を含む行:

```csv
0,23.500000,,,,,,,,,
15,,10.000000,,,,,,44.000000,,
```

LogAnalyzer 2015 等が出力した既存ログ（例: `log_20150911_105700.csv`）も同じ形式のため、**CSVからグラフ** でそのまま読み込めます。

#### ログファイルの確認

保存されたログは、エクスプローラーやターミナルから `logs/` フォルダ内の CSV ファイルを開いて確認できます。

```bash
ls logs/
cat logs/log_20260618_120000.csv
```

Excel や Google スプレッドシートなど、CSV 対応のアプリでも開けます。

### 6. CSV ログからグラフを表示する

過去に保存したログ CSV を読み込んで、折れ線グラフを表示できます。Bluetooth 未接続の状態でも利用できます。

1. **CSVからグラフ** ボタンをクリックします。
2. ファイル選択ダイアログで表示したい CSV を選びます（初期フォルダは `logs/`）。
3. 読み込みが成功すると、グラフと系列チェックボックスが表示されます。
4. チェックボックスで表示する系列を切り替えます。
5. 表示をやめる場合は **初期状態に戻す** ボタンをクリックします（CSV 読み込み後のみ有効）。

#### 対応している CSV 形式

**レガシー形式**（[ログファイル形式](#ログファイル形式)）

- 本アプリが Bluetooth 受信時に自動保存した CSV
- LogAnalyzer 2015 等の既存ログ
- `#` で始まる行はコメントとして無視
- ヘッダー例: `# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd`
- 空欄は null（欠損値）として読み込み
- 全系列を一度に読み込み、チェックボックスで個別に表示切替

レガシー形式の記録例（LogAnalyzer 2015 出力）:

```csv
# THRESHOLD= 0.100800
# Speed = 0.000000; Proportional = 0.000000; Integral = 0.000000
# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd
315,-45.000000,10.000000,7971,0,0,0.090000,44.000000,0.000000,0.000000,0.000000
318,-45.000000,10.000000,7970,0,0,0.100000,46.000000,0.000000,0.000000,0.000000
```

**旧 LogAnalyzer2 形式**（後方互換の読み込みのみ）

- 1 行目が `received_at,sample_index,raw_data,parsed_value` の CSV
- 過去バージョンで保存したファイルを **CSVからグラフ** で開く場合に対応
- 現在のバージョンではこの形式での新規保存は行いません

#### グラフの軸と系列

| 項目 | 内容 |
|------|------|
| 横軸 | 経過時間（ms）。先頭データを 0 ms として表示 |
| 縦軸 | 選択した系列の数値 |
| 凡例 | チェックが入っている系列名を表示 |

横軸は `time` 列（経過時間 ms）を使用します。先頭データを 0 ms として表示します。旧 LogAnalyzer2 形式の CSV を読み込む場合のみ、`received_at` 列から経過時間を計算します。

#### 系列チェックボックス

データ受信時および CSV 読み込み後、グラフ上部に系列名のチェックボックスが表示されます。

- チェック ON: その系列をグラフに表示
- チェック OFF: その系列をグラフから非表示
- 変更は即座にグラフへ反映されます

初期状態:

| 状況 | 初期表示 |
|------|---------|
| Bluetooth リアルタイム受信 | `gyro` のみ ON（他系列は OFF） |
| レガシー形式 CSV 読み込み | `gyro` のみ ON（他系列は OFF） |
| 旧 LogAnalyzer2 形式 CSV 読み込み | `parsed_value` のみ ON |

#### 表示内容

- グラフタイトル: `ファイル名 (プロット件数/総行数 件)` の形式
  - 例: `log_20150911_105700.csv (13106/13106 件)`
- ログ表示ラベル: `表示中: （ファイルパス）`

#### 補足

- Bluetooth 接続中に CSV を読み込んだ場合、その後リアルタイムでデータを受信すると、読み込んだグラフに追記されます。
- `time` 列が数値として読み取れない行は、CSV 読み込み時にスキップされます。
- プロット可能な行が 1 件もない CSV を開くと、エラーダイアログが表示されます。
- レガシー形式の CSV は系列数が多いため、必要な系列だけを ON にして表示することを推奨します。

## 受信データ形式

デバイスから送られるテキストデータは UTF-8 として解釈されます。**1 行が 1 レコード** で、改行（`\n` / `\r\n` / `\r`）で区切ります。

### 行の形式

| 形式 | 列数 | 例 | 説明 |
|------|------|-----|------|
| データ列のみ | 1〜10 列 | `-45,10,7971,0,0,0.09,44,0,0,0` | 先頭から `turn` … `Kd` に順に対応。不足列は null |
| time + データ列 | 11 列以上 | `315,-45,10,7971,0,0,0.09,44,0,0,0` | 先頭が `time`（ms）、続く 10 列がデータ列。12 列目以降は無視 |

列の対応順:

```
turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd
```

列数不足・非数値の項目は null として扱われ、エラーにはなりません（[null（欠損値）の扱い](#null欠損値の扱い) 参照）。

### 受信バッファ

BLE の notify はパケット単位で届くため、アプリ側で改行までデータをバッファリングしてから 1 行として処理します。切断時に改行のない残りデータがある場合も、最後の 1 行として処理します。バッファ上限は 64 KB です。

## Bluetooth 接続の仕様

- 通信方式: BLE（Bluetooth Low Energy）
- 役割: LogAnalyzer2 が **セントラル**（接続側）、送信デバイスが **ペリフェラル**（アドバタイズ側）
- 優先サービス: Nordic UART Service（NUS）
  - Service UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
  - TX UUID（通知）: `6e400003-b5a3-f393-e0a9-e50e24dcca9e`
  - RX UUID（書き込み）: `6e400002-b5a3-f393-e0a9-e50e24dcca9e`（LogAnalyzer2 は現状未使用）
- NUS が見つからない場合は、通知（notify）可能なキャラクタリスティックを自動検出して接続します。
- 受信データは改行までバッファリングしてから行単位で処理します（[受信バッファ](#受信バッファ) 参照）。

## エラー処理

| 状況 | 挙動 |
|------|------|
| BLE スキャン・接続・切断エラー | ダイアログ表示。接続エラー時は UI を未接続状態に戻す |
| notify 特性が見つからない | ダイアログ表示後、接続を解除 |
| 受信バッファ上限（64 KB）超過 | ダイアログ表示。バッファをクリア |
| ログファイル作成失敗（接続時） | ダイアログ表示後、BLE 接続を自動切断 |
| ログ書き込み失敗（記録中） | ダイアログ表示。以降の記録を停止 |
| ログ保存失敗（切断時） | ダイアログ表示 |
| グラフ HTML 書き込み失敗 | ダイアログ表示（連続エラーは初回のみ通知） |
| CSV 読み込み失敗 | ダイアログ表示 |
| 受信データの列不足・非数値 | 該当列を null として記録（エラーにしない） |

## ログ送信側プログラム

LogAnalyzer2 にデータを送るデバイス側は、BLE ペリフェラルとして動作するプログラムを書きます。

### 送信側の役割

```
[センサー等] → 値を取得 → 文字列化（UTF-8） → BLE notify で送信
                                                    ↓
                              LogAnalyzer2 が受信 → グラフ表示 + CSV 保存
```

送信側プログラムが行うこと:

1. BLE ペリフェラルとしてアドバタイズを開始する
2. NUS（または notify 可能な独自サービス）を登録する
3. LogAnalyzer2 からの接続を待つ
4. センサー値などをテキストに変換し、`notify` で送信する

### 送るデータ形式

- 文字コード: UTF-8
- 区切り: 1 レコードごとに改行（`\n` 推奨）を付ける
- 内容: [受信データ形式](#受信データ形式) に準拠（レガシー CSV と同じ 10 データ列、または `time` 付き 11 列）

送信例:

```text
315,-45.0,10.0,7971,0,0,0.09,44.0,0,0,0
318,-45.0,10.0,7970,0,0,0.10,46.0,0,0,0
```

1 行が BLE MTU を超える場合でも、**改行まで分割送信** すればアプリ側で結合されます。

### 実装例（Pybricks）

LEGO SPIKE Prime / Robot Inventor / Technic Hub 等で Pybricks を使う場合の例です。  
サンプル: [`samples/pybricks_log_sender.py`](samples/pybricks_log_sender.py)

Pybricks は **NUS ではなく `usys.stdout` 経由** で PC にデータを送ります。LogAnalyzer2 は Pybricks の stdout イベント（GATT `c5f50002-...`）と NUS の両方を受信できます。

SPIKE Prime ラージハブにはジャイロセンサーが内蔵されており、Pybricks では `hub.imu.angular_velocity()` で角速度を取得します。カラーセンサーは外付けです。

```python
from pybricks.hubs import ThisHub
from pybricks.parameters import Axis, Port
from pybricks.pupdevices import ColorSensor
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = ThisHub()
color_sensor = ColorSensor(Port.A)
watch = StopWatch()

while True:
    hue, saturation, value = color_sensor.hsv()
    gyro = hub.imu.angular_velocity(Axis.Z)
    line = "{},0,0,{},{},{},{},0,0,0\n".format(
        watch.time(), hub.battery.voltage(), hue, saturation, value, gyro
    )
    stdout.write(line)
    wait(100)
```

カラーセンサーは `hsv()` の生値を `angleL=h`, `angleR=s`, `bright=v` 列にそのまま送ります。

手順:

1. Pybricks Code で `pybricks_log_sender.py` をハブに書き込む
2. **Pybricks Code から切断する**（他アプリと同時接続不可）
3. LogAnalyzer2 で **スキャン** → ハブ名を選択 → **接続**
4. ハブのボタンでプログラムを開始
5. グラフと `logs/*.csv` にデータが記録される

注意:

- BOOST Move Hub は `usys` 非対応のため動作しません
- センサー値は環境に合わせてサンプル内の読み取り部を書き換えてください

### 実装例（PC + bless、テスト用）

PC を仮想デバイス `LogSensor` として動かすテスト用サンプルです。  
サンプル: [`samples/pc_ble_log_sender.py`](samples/pc_ble_log_sender.py)

```bash
pip install -r samples/requirements-sender.txt
python samples/pc_ble_log_sender.py
```

macOS では bless の制約により動作しない場合があります。実機検証は Pybricks ハブまたは ESP32 等を推奨します。

### 実装例（ESP32 + Arduino）

ESP32 などのマイコンで NUS ペリフェラルとして動作させる例です。

```cpp
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define SERVICE_UUID "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define TX_UUID      "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

BLECharacteristic *txChar;
bool deviceConnected = false;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server) { deviceConnected = true; }
  void onDisconnect(BLEServer *server) {
    deviceConnected = false;
    server->getAdvertising()->start();
  }
};

void setup() {
  BLEDevice::init("LogSensor");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService *service = server->createService(SERVICE_UUID);
  txChar = service->createCharacteristic(
      TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  txChar->addDescriptor(new BLE2902());
  service->start();

  BLEDevice::getAdvertising()->start();
}

void loop() {
  if (!deviceConnected) { delay(500); return; }

  unsigned long t = millis();
  float gyro = 20.0 + (t % 1000) / 100.0;
  String line = String(t) + ",-45,10,7971,0,0,0.09," + String(gyro, 1) + ",0,0,0\n";
  txChar->setValue(line.c_str());
  txChar->notify();

  delay(1000);
}
```

1. 上記を ESP32 に書き込む
2. LogAnalyzer2 で **スキャン** → `LogSensor` を選択 → **接続**
3. グラフと `logs/*.csv` にデータが記録される

### 送信側の実装メモ

| 項目 | 推奨 |
|------|------|
| デバイス名 | `BLEDevice::init("名前")` で付けるとスキャン時に識別しやすい |
| 送信タイミング | LogAnalyzer2 接続後（`onConnect` 後）に notify を開始する |
| 1 回の送信サイズ | BLE の MTU 制限を考慮し、1 行を複数 notify に分割しても可（改行までバッファリング） |
| 切断時 | 再アドバタイズして再接続できるようにする |
| 開発ボード | Pybricks 対応ハブ / ESP32 / nRF52840 など |

Pybricks ハブでは NUS ではなく stdout イベントで送ります。ESP32 等では NUS notify を使います。

## 画面構成

```
┌────────────────────────────────────────────────────────────────────────────┐
│ [スキャン] [デバイス選択 ▼] [接続] [切断（ログ書き込み）]        状態      │
│ ログ: 記録中 / 保存済み / 表示中     [CSVからグラフ] [初期状態に戻す]      │
│ [turn] [speed] [battery] [gyro] ...  ← 系列チェックボックス                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│              Plotly 折れ線グラフ（凡例付き）                               │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

- **初期状態に戻す**: CSV 読み込み後にのみ有効。グラフと系列チェックボックスをクリアし、CSV 読み込み前のログ表示ラベルに戻します。Bluetooth 接続中は接続を維持したまま、表示だけを初期状態に戻します。

## ファイル構成

```
LogAnalyzer2/
├── main.py                  # メインウィンドウ・グラフ表示
├── app_paths.py             # 開発時・exe 化後のパス解決
├── bluetooth_manager.py     # BLE スキャン・接続・データ受信
├── log_writer.py            # 受信ログの CSV 出力
├── log_reader.py            # 保存済み CSV ログの読み込み
├── LogAnalyzer2.spec        # PyInstaller 設定
├── build_windows.bat        # Windows 向け exe ビルドスクリプト
├── requirements-build.txt   # ビルド用依存
├── runtime_hook_qtwebengine.py  # Qt WebEngine ランタイムフック
├── requirements.txt         # 依存パッケージ
├── LICENSE                  # 本ソフトウェアの利用許諾
├── THIRD_PARTY_NOTICES.txt  # 第三者ライブラリのライセンス表示
├── licenses/                # 第三者ライセンス全文
│   ├── LGPL-3.0.txt         # PySide6 / Qt 用
│   └── MIT.txt
├── logs/                    # 受信ログの保存先（自動生成）
└── temp.html                # グラフ描画用の一時 HTML（自動生成）
```

## ライセンス

### 本ソフトウェア（LogAnalyzer2）

- 利用条件: [LICENSE](LICENSE) を参照
- 著作権者: matthew
- 配布形態: クローズドコミュニティ内での利用を想定

### 第三者ライブラリ

本ソフトウェアには PySide6、Plotly、bleak などの第三者ライブラリが含まれます。

- 一覧と著作権表示: [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)
- ライセンス全文: [licenses/](licenses/) ディレクトリ

特に PySide6 / Qt は **LGPL v3** の下で使用しています。  
配布時は `licenses/LGPL-3.0.txt` を同梱してください。

## 注意事項

- macOS では初回実行時に Bluetooth の使用許可を求められる場合があります。
- BLE デバイスは接続前にアドバタイズ（発見可能）状態である必要があります。
- 送信側は [受信データ形式](#受信データ形式) に従った行データを送ってください。列不足は null として記録されますが、意図したログにならない場合があります。
- 接続先のデバイスが独自のサービス UUID やデータ形式を使っている場合は、`bluetooth_manager.py` の調整が必要になることがあります。
- `logs/` フォルダや `temp.html` への書き込み権限がない場合、ログ記録やグラフ表示が失敗します（[エラー処理](#エラー処理) 参照）。
- ログファイル（`logs/*.csv`）は `.gitignore` により Git 管理対象外です。
- 配布時は `LICENSE`、`THIRD_PARTY_NOTICES.txt`、`licenses/` を同梱してください。
