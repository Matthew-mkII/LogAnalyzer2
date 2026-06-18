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

ウィンドウが開くと、上部に Bluetooth 操作パネルとログ操作パネル、中央に系列チェックボックス（CSV 読み込み時）、下部にグラフ表示エリアが表示されます。

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
- グラフの横軸は **ログ取得開始からの経過時間（ms）**、縦軸は受信した数値です。
- 横軸は **0 ms から** 表示されます。
- データがまだない場合は「データ待機中...」と表示されます。
- グラフは 200ms 間隔で更新されます。
- リアルタイム表示時の系列名は `受信データ` です。

### 4. 接続を切断する

**切断** ボタンをクリックすると、BLE 接続が終了します。記録中のログファイルが保存されます。

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

#### 保存先とファイル名

- 保存先: プロジェクト直下の `logs/` フォルダ（存在しない場合は自動作成）
- ファイル名: `log_YYYYMMDD_HHMMSS.csv`
  - 例: `log_20260618_120000.csv`

#### ログファイル形式（LogAnalyzer2 形式）

Bluetooth 接続中に自動保存される CSV です。1 行目はヘッダー行です。

| 列名 | 内容 |
|------|------|
| `received_at` | アプリがデータを受信した日時（ISO 8601 形式） |
| `sample_index` | グラフ用のサンプル番号（数値に変換できた場合のみ） |
| `raw_data` | デバイスから受信した生テキスト |
| `parsed_value` | グラフ描画に使用した数値（変換できない場合は空） |

記録例:

```csv
received_at,sample_index,raw_data,parsed_value
2026-06-18T12:00:01.234,1,"23.5",23.5
2026-06-18T12:00:01.456,2,"1234567890,45.6",45.6
2026-06-18T12:00:01.789,,"invalid",
```

数値に変換できない行も `raw_data` として記録されます。グラフには数値として解釈できるデータのみ反映されます。

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

#### 対応している CSV 形式

**LogAnalyzer2 形式**（[ログファイル形式（LogAnalyzer2 形式）](#ログファイル形式loganalyzer2-形式)）

- 本アプリが Bluetooth 受信時に自動保存した CSV
- 系列は `parsed_value` の 1 列

**レガシー形式**（LogAnalyzer 2015 等の既存ログ）

- `#` で始まる行はコメントとして無視
- ヘッダー例: `# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd`
- データ例: `315,-45.000000,10.000000,7971,0,0,0.090000,44.000000,...`
- 全系列を一度に読み込み、チェックボックスで個別に表示切替

レガシー形式の記録例:

```csv
# THRESHOLD= 0.100800
# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd
315,-45.000000,10.000000,7971,0,0,0.090000,44.000000,0.000000,0.000000,0.000000
318,-45.000000,10.000000,7970,0,0,0.100000,46.000000,0.000000,0.000000,0.000000
```

#### グラフの軸と系列

| 項目 | 内容 |
|------|------|
| 横軸 | 経過時間（ms）。先頭データを 0 ms として表示 |
| 縦軸 | 選択した系列の数値 |
| 凡例 | チェックが入っている系列名を表示 |

LogAnalyzer2 形式では `received_at` 列から、レガシー形式では `time` 列から経過時間を計算します。

#### 系列チェックボックス

CSV 読み込み後、グラフ上部に系列名のチェックボックスが表示されます。

- チェック ON: その系列をグラフに表示
- チェック OFF: その系列をグラフから非表示
- 変更は即座にグラフへ反映されます

初期状態:

| CSV 形式 | 初期表示 |
|---------|---------|
| LogAnalyzer2 形式 | `parsed_value` のみ ON |
| レガシー形式 | `gyro` のみ ON（他系列は OFF） |

Bluetooth リアルタイム受信中は、系列チェックボックスは表示されません（`受信データ` 系列のみ）。

#### 表示内容

- グラフタイトル: `ファイル名 (プロット件数/総行数 件)` の形式
  - 例: `log_20150911_105700.csv (13106/13106 件)`
- ログ表示ラベル: `表示中: （ファイルパス）`

#### 補足

- Bluetooth 接続中に CSV を読み込んだ場合、その後リアルタイムでデータを受信すると、読み込んだグラフに追記されます。
- 数値データが 1 件もない CSV を開くと、エラーダイアログが表示されます。
- レガシー形式の CSV は系列数が多いため、必要な系列だけを ON にして表示することを推奨します。

## 受信データ形式

デバイスから送られるテキストデータは UTF-8 として解釈されます。次の形式に対応しています。

| 形式 | 例 | 説明 |
|------|-----|------|
| 数値のみ | `23.5` | そのままグラフの値として使用 |
| CSV 形式 | `1234567890,23.5` | カンマ区切りの場合、右側から数値に変換できる部分を使用 |

1 行に 1 データを想定しています。改行で区切られた複数行が一度に届いた場合も、行ごとに処理されます。

## Bluetooth 接続の仕様

- 通信方式: BLE（Bluetooth Low Energy）
- 役割: LogAnalyzer2 が **セントラル**（接続側）、送信デバイスが **ペリフェラル**（アドバタイズ側）
- 優先サービス: Nordic UART Service（NUS）
  - Service UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
  - TX UUID（通知）: `6e400003-b5a3-f393-e0a9-e50e24dcca9e`
  - RX UUID（書き込み）: `6e400002-b5a3-f393-e0a9-e50e24dcca9e`（LogAnalyzer2 は現状未使用）
- NUS が見つからない場合は、通知（notify）可能なキャラクタリスティックを自動検出して接続します。

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
- 区切り: 1 レコードごとに改行（`\n`）を付ける
- 内容: [受信データ形式](#受信データ形式) に準拠

送信例:

```text
23.5
24.1
1718707200,25.3
```

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

  float value = 20.0 + (millis() % 1000) / 100.0;
  String line = String(value, 1) + "\n";
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
| 1 回の送信サイズ | BLE の MTU 制限を考慮し、短い行単位で送る |
| 切断時 | 再アドバタイズして再接続できるようにする |
| 開発ボード | ESP32 / nRF52840 などが手軽 |

macOS 上の PC を送信側（ペリフェラル）にする方法は環境制約が多いため、実機検証は ESP32 等のマイコンを使うことを推奨します。

## 画面構成

```
┌─────────────────────────────────────────────────────────┐
│ [スキャン] [デバイス選択 ▼] [接続] [切断]  ステータス   │
│ ログ: 記録中 / 保存済み / 表示中 [CSVからグラフ]        │
│ [turn] [speed] [battery] [gyro] ...  ← 系列チェックボックス │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              Plotly 折れ線グラフ（凡例付き）            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## ファイル構成

```
LogAnalyzer2/
├── main.py                  # メインウィンドウ・グラフ表示
├── bluetooth_manager.py     # BLE スキャン・接続・データ受信
├── log_writer.py            # 受信ログの CSV 出力
├── log_reader.py            # 保存済み CSV ログの読み込み
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
- 接続先のデバイスが独自のサービス UUID やデータ形式を使っている場合は、`bluetooth_manager.py` の調整が必要になることがあります。
- ログファイル（`logs/*.csv`）は `.gitignore` により Git 管理対象外です。
- 配布時は `LICENSE`、`THIRD_PARTY_NOTICES.txt`、`licenses/` を同梱してください。
