# LogAnalyzer2

## 概要

PySide6 と Plotly を使ったグラフ描画アプリです。Bluetooth Low Energy（BLE）経由でデバイスから受信したデータをリアルタイムで折れ線グラフに表示し、受信ログを CSV ファイルに自動保存します。センサー値（従来の 10 列）に加え、IMU の姿勢角（`roll`, `yaw`, `pitch`）も記録・表示できます。保存済みの CSV ログからの再表示や、グラフの画像エクスポート（PNG 等）にも対応しています。

## 環境構築

```bash
python3 -m venv la2
source la2/bin/activate
pip install -r requirements.txt
```

主な依存パッケージ:

- PySide6 / PySide6-WebEngine … GUI とグラフ表示
- Plotly … グラフ描画
- kaleido … グラフの画像エクスポート（Plotly 用）
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

- PySide6 + Qt WebEngine + kaleido を含むため、配布フォルダのサイズは数百 MB 程度になります。
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
- 初回データ受信後、グラフ上部に **14 系列のチェックボックス**（`turn`, `speed`, `battery`, `angleL`, `angleR`, `hue`, … `pitch`）が表示されます。初期状態では `hue`, `saturation`, `value`, `roll`, `yaw`, `pitch` が ON です。
- 列の値が null（空欄・非数値）の点は、グラフ上で欠損として表示されます（線が途切れます）。

### 4. グラフを画像として保存する

表示中のグラフを画像ファイルとして保存できます。Bluetooth 接続中・CSV 読み込み後のどちらでも利用できます。

1. **画像として保存** ボタンをクリックします。
2. 保存先とファイル形式を選びます（初期フォルダは `logs/`）。
3. 保存が完了すると確認ダイアログが表示されます。

| 項目 | 内容 |
|------|------|
| 対応形式 | PNG / SVG / JPEG / WebP |
| デフォルトファイル名 | `graph_YYYYMMDD_HHMMSS.png` |
| 出力サイズ | 1200×800 px、`scale=2`（高解像度） |
| データなし時 | 「エクスポートするデータがありません」と表示 |

画像は画面上のグラフと同じ系列（チェック ON の系列）・タイトルで出力されます。Plotly の `write_image` と kaleido を使用しています。

### 5. 接続を切断する

**切断（ログ書き込み）** ボタンをクリックすると、BLE 接続が終了します。記録中のログファイルが保存されます。

### 6. ログをファイルに保存する

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

Bluetooth 接続中に自動保存される CSV は、従来の `angleL` / `angleR` 列に加え、カラーセンサー用の `hue` / `saturation` / `value` 列と IMU 姿勢角 `roll` / `yaw` / `pitch` 列を含む形式です。`#` で始まる行はコメントとして扱われ、データ行はカンマ区切りの数値列です。本アプリが保存するファイルでは、コメント行は列名の 1 行のみです。

##### ファイル構成

| 行 | 内容 |
|----|------|
| 1 行目 | `# time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch` — データ列名 |
| 2 行目以降 | データ行（ヘッダー行はありません） |

LogAnalyzer 2015 等が出力した既存ログ（`gyro` 列を含む 10 データ列）も **CSVからグラフ** で読み込めます（ヘッダー行の列名に従って解釈）。本アプリが新規保存する CSV には `gyro` 列は含まれません。

##### データ列

| 列名 | 内容 |
|------|------|
| `time` | 経過時間（ms）。デバイスが `time` 列を送らない場合は接続開始からの経過時間。整数値の場合は小数点なし |
| `turn` | 旋回量 |
| `speed` | 速度 |
| `battery` | バッテリー電圧 |
| `angleL` | 左モーター角度 |
| `angleR` | 右モーター角度 |
| `hue` | カラーセンサー色相（HSV の H 生値） |
| `saturation` | カラーセンサー彩度（HSV の S 生値） |
| `value` | カラーセンサー明度（HSV の V 生値） |
| `Kp`, `Ki`, `Kd` | PID パラメータ |
| `roll` | ロール角（deg） |
| `yaw` | ヨー角（deg） |
| `pitch` | ピッチ角（deg） |

##### null（欠損値）の扱い

Bluetooth 受信行のパース時、次の場合は該当列を **null** として扱います。

| 条件 | 挙動 |
|------|------|
| 列数が 14 未満 | 不足列を null でパディング |
| 数値に変換できない列 | その列のみ null |
| 15 列以上で先頭列が数値 | 先頭を `time`、続く 14 列をデータ列として解釈 |
| 14 列以下で先頭からデータ列 | `time` なし。接続開始からの経過 ms を使用 |

CSV への記録では null は **空欄** として出力します。**CSVからグラフ** で読み込む際も空欄は null として解釈されます。

##### 記録例（Bluetooth 受信時の自動保存）

完全な 15 列（`time` + 14 データ列）:

```csv
# time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
315,0.000000,0.000000,7971,0.000000,0.000000,120.000000,80.000000,0.090000,0.000000,0.000000,0.000000,2.500000,-12.000000,1.250000
```

LogAnalyzer 2015 等の旧形式（`gyro` 列あり）の読み込み例:

```csv
# time, turn, speed, battery, angleL, angleR, bright, gyro, Kp, Ki, Kd
315,-45.000000,10.000000,7971,0.000000,0.000000,0.090000,44.000000,0.000000,0.000000,0.000000
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

### 7. CSV ログからグラフを表示する

過去に保存したログ CSV を読み込んで、折れ線グラフを表示できます。Bluetooth 未接続の状態でも利用できます。

1. **CSVからグラフ** ボタンをクリックします。
2. ファイル選択ダイアログで表示したい CSV を選びます（初期フォルダは `logs/`）。
3. 読み込みが成功すると、グラフと系列チェックボックスが表示されます。
4. チェックボックスで表示する系列を切り替えます。
5. 表示をやめる場合は **初期状態に戻す** ボタンをクリックします（CSV 読み込み後のみ有効）。

#### 対応している CSV 形式

**本アプリ形式**（[ログファイル形式](#ログファイル形式)）

- 本アプリが Bluetooth 受信時に自動保存した CSV（14 データ列）
- LogAnalyzer 2015 等の既存ログ（`gyro` 列を含む場合あり）
- `#` で始まる行はコメントとして無視
- ヘッダー例: `# time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch`
- 空欄は null（欠損値）として読み込み
- 全系列を一度に読み込み、チェックボックスで個別に表示切替

本アプリ形式の記録例:

```csv
# time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
315,0,0,7971,0,0,120,80,0.09,0,0,0,2.5,-12.0,1.25
```

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
| Bluetooth リアルタイム受信 | `hue`, `saturation`, `value`, `roll`, `yaw`, `pitch` が ON |
| 本アプリ形式 / 旧 CSV 読み込み | ヘッダーに存在する系列のうち、上記 6 系列が ON |
| 旧 LogAnalyzer2 形式 CSV 読み込み | `parsed_value` のみ ON |

#### 表示内容

- グラフタイトル: `ファイル名 (プロット件数/総行数 件)` の形式
  - 例: `log_20150911_105700.csv (13106/13106 件)`
- ログ表示ラベル: `表示中: （ファイルパス）`

#### 補足

- Bluetooth 接続中に CSV を読み込んだ場合、その後リアルタイムでデータを受信すると、読み込んだグラフに追記されます。
- `time` 列が数値として読み取れない行は、CSV 読み込み時にスキップされます。
- プロット可能な行が 1 件もない CSV を開くと、エラーダイアログが表示されます。

## 受信データ形式

デバイスから送られるテキストデータは UTF-8 として解釈されます。**1 行が 1 レコード** で、改行（`\n` / `\r\n` / `\r`）で区切ります。

### 行の形式

| 形式 | 列数 | 例 | 説明 |
|------|------|-----|------|
| データ列のみ | 1〜14 列 | `-45,10,7971,0,0,120,80,0.09,0,0,0,2.5,-12,1.25` | 先頭から `turn` … `pitch` に順に対応。不足列は null |
| time + データ列 | 15 列 | `315,0,0,7971,0,0,120,80,0.09,0,0,0,2.5,-12,1.25` | 先頭が `time`（ms）、続く 14 列がデータ列 |

列の対応順:

```
turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
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
- Pybricks stdout イベント（ハブからの `usys.stdout` 出力）
  - Characteristic UUID: `c5f50002-8280-46da-89f4-6d8051e4aeef`
  - イベント種別 `0x01`（WRITE_STDOUT）のペイロードを UTF-8 テキストとして受信
- NUS または Pybricks のいずれかが見つかれば接続成功。両方ある場合は両方の notify を購読します。
- NUS が見つからない場合は、NUS サービス内の notify 可能なキャラクタリスティックを自動検出して接続します。
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
| グラフ画像エクスポート失敗 | ダイアログ表示 |
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
- 内容: [受信データ形式](#受信データ形式) に準拠（14 データ列、または `time` 付き 15 列）

送信例:

```text
315,0,0,7971,0,0,120,80,0.09,0,0,0,2.5,-12.0,1.25
```

1 行が BLE MTU を超える場合でも、**改行まで分割送信** すればアプリ側で結合されます。

### 実装例（Pybricks）

LEGO SPIKE Prime / Robot Inventor / Technic Hub 等で Pybricks を使う場合の例です。

Pybricks は **NUS ではなく `usys.stdout` 経由** で PC にデータを送ります。LogAnalyzer2 は Pybricks の stdout イベント（GATT `c5f50002-...`）と NUS の両方を受信できます。

SPIKE Prime ラージハブにはジャイロセンサー（IMU）が内蔵されています。サンプルでは次の値を送信します。

| 列 | Pybricks API | 内容 |
|----|--------------|------|
| `roll`, `pitch` | `hub.imu.tilt()` | ロール角・ピッチ角（deg） |
| `yaw` | `hub.imu.heading()` | ヨー角（deg、プログラム開始時を 0 とする累積値） |
| `hue`, `saturation`, `value` | `color_sensor.hsv()` | カラーセンサーの H, S, V 生値（各列を独立してグラフ表示） |
| `battery` | `hub.battery.voltage()` | バッテリー電圧（mV） |

注意: `hub.imu.orientation()` は 3×3 の回転行列を返すため、姿勢角の取得には `tilt()` と `heading()` を使います。角速度（旧 `gyro` 列）は送信しません。

```python
from pybricks.hubs import ThisHub
from pybricks.parameters import Port
from pybricks.pupdevices import ColorSensor
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = ThisHub()
color_sensor = ColorSensor(Port.E)
watch = StopWatch()

while True:
    hue, saturation, value = color_sensor.hsv()
    pitch, roll = hub.imu.tilt()
    yaw = hub.imu.heading()

    line = "{},0,0,{},0,0,{},{},{},0,0,0,{},{},{}\n".format(
        watch.time(),
        hub.battery.voltage(),
        hue, saturation, value,
        roll, yaw, pitch,
    )
    stdout.write(line)
    wait(100)
```

カラーセンサーは `hsv()` の生値を `hue`, `saturation`, `value` 列にそのまま送ります。`turn`, `speed`, `angleL`, `angleR`, `Kp`, `Ki`, `Kd` はサンプルでは 0 固定です。

手順:

1. Pybricks Code で上記コードをハブに書き込む
2. **Pybricks Code から切断する**（他アプリと同時接続不可）
3. LogAnalyzer2 で **スキャン** → ハブ名を選択 → **接続**
4. ハブのボタンでプログラムを開始
5. グラフと `logs/*.csv` にデータが記録される

注意:

- BOOST Move Hub は `usys` 非対応のため動作しません
- センサー値は環境に合わせてサンプル内の読み取り部を書き換えてください
- **Pybricks 公式ファームウェア**では Python のみ実行可能です。**C/C++ でハブ上で動かす**場合は [SPIKE-RT](https://github.com/spike-rt/spike-rt) へのファームウェア差し替えが必要です（下記参照）

### 実装例（Pybricks：ライントレース + ログ）

On/Off 制御でライントレースしながらセンサー値を送信する例です。  
サンプル: [`samples/pybricks_line_tracer_log_sender.py`](samples/pybricks_line_tracer_log_sender.py)

`LineTracerOnOff` と同じ配線・制御ロジックに、LogAnalyzer2 形式の CSV 出力を組み合わせています。

| 項目 | 内容 |
|------|------|
| モーター | Port A: 右 / Port B: 左 |
| ボタン | Port D: フォースセンサー（1 回目で閾値測定、2 回目で走行開始） |
| カラーセンサー | Port E: ライン検出 + HSV ログ |
| 走行 | `speed=100`, `turn=±55`, 最大約 60 秒 |
| ログ列 | `turn`, `speed`, `battery`, `angleL`, `angleR`, `hue`, `saturation`, `value`, `Kp`, `Ki`, `Kd`, `roll`, `yaw`, `pitch` |

手順:

1. ファイル先頭の `edge`（`LEFT_EDGE` / `RIGHT_EDGE`）とポートを確認
2. Pybricks Code でハブに書き込み、**切断する**
3. LogAnalyzer2 で **スキャン** → ハブ名を選択 → **接続**
4. ハブでプログラムを開始し、フォースセンサーで閾値測定 → 走行開始

### 実装例（SPIKE-RT + C++：ライントレース + ログ）

[SPIKE-RT](https://github.com/spike-rt/spike-rt) ファームウェアを SPIKE Prime ハブに書き込み、C++ でライントレースしながら LogAnalyzer2 形式の CSV を Bluetooth（NUS）で送信する例です。  
サンプル: [`samples/spike_rt_line_tracer_log_sender/`](samples/spike_rt_line_tracer_log_sender/)

Pybricks 版（`pybricks_line_tracer_log_sender.py`）と同じ配線・On/Off 制御・CSV 列です。BLE は SPIKE-RT の Pybricks 互換シリアル（Nordic UART Service）経由で、LogAnalyzer2 の NUS 受信に対応します。

| 項目 | 内容 |
|------|------|
| 対象ハブ | SPIKE Prime（SPIKE-RT 書き込み済み） |
| モーター | Port A: 右 / Port B: 左 |
| ボタン | Port D: フォースセンサー |
| カラーセンサー | Port E |
| ソース | `line_tracer_log_sender.cpp` |

#### 環境構築（概要）

1. [spike-rt](https://github.com/spike-rt/spike-rt) と [spike-rt-sample](https://github.com/Hiyama1026/spike-rt-sample) をクローンし、SPIKE-RT のビルド手順に従って開発環境を用意（Linux / WSL / Docker 推奨）
2. サンプルを spike-rt-sample に配置:

```bash
./samples/spike_rt_line_tracer_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
```

3. ビルドと書き込み（ハブを DFU モードにして USB 接続）:

```bash
cd /path/to/spike-rt-sample/API-sample/line_tracer_log_sender
make
make deploy-lin    # Linux / WSL
```

4. ハブの電源を入れると `READY` 表示で BLE 待機 → LogAnalyzer2 で **スキャン** → ハブを選択 → **接続**
5. フォースセンサー 1 回目: 閾値測定 / 2 回目: 走行開始

注意:

- SPIKE-RT は LEGO 公式ファームウェアを置き換えます。元に戻すには公式ファームウェアの再書き込みが必要です
- `kEdge`（`kLeftEdge` / `kRightEdge`）は `line_tracer_log_sender.cpp` 先頭で切り替え
- IMU の `yaw` は角速度積分、`roll` / `pitch` は加速度から算出（Pybricks の `tilt()` / `heading()` とは算出方法が異なる場合があります）

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
  String line = String(t) + ",-45,10,7971,0,0,0.09,0,0,0,2.5,-12,1.25\n";
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
│ ログ: 記録中 / 保存済み / 表示中  [CSVからグラフ] [画像として保存] [初期状態に戻す] │
│ [turn] [speed] [angleL] [angleR] [hue] [saturation] [value] [roll] ...    │
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
├── main.py                      # メインウィンドウ・グラフ表示
├── app_paths.py                 # 開発時・exe 化後のパス解決
├── bluetooth_manager.py         # BLE スキャン・接続・データ受信（NUS / Pybricks stdout）
├── log_writer.py                # 受信ログの CSV 出力
├── log_reader.py                # 保存済み CSV ログの読み込み
├── LogAnalyzer2.spec            # PyInstaller 設定
├── build_windows.bat            # Windows 向け exe ビルドスクリプト
├── requirements.txt             # 実行時依存パッケージ
├── requirements-build.txt       # ビルド用依存（PyInstaller 等）
├── runtime_hook_qtwebengine.py  # Qt WebEngine ランタイムフック
├── LICENSE                      # 本ソフトウェアの利用許諾
├── THIRD_PARTY_NOTICES.txt      # 第三者ライブラリのライセンス表示
├── README.md                    # 本ドキュメント
├── .gitignore
├── licenses/                    # 第三者ライセンス全文
│   ├── LGPL-3.0.txt             # PySide6 / Qt 用
│   └── MIT.txt
├── logs/                        # 受信ログの保存先（実行時に自動生成、*.csv は .gitignore）
├── samples/                     # ログ送信サンプル
│   ├── pybricks_line_tracer_log_sender.py  # Pybricks: ライントレース + ログ
│   ├── pc_ble_log_sender.py                # PC BLE テスト用（bless）
│   ├── log_format.py                       # CSV 行フォーマット共通モジュール
│   ├── format_demo.py                      # log_format の動作確認用
│   ├── requirements-sender.txt             # pc_ble_log_sender 用依存
│   └── spike_rt_line_tracer_log_sender/    # SPIKE-RT (C++): ライントレース + ログ
│       ├── line_tracer_log_sender.cpp
│       ├── line_tracer_log_sender.h
│       ├── line_tracer_log_sender.cfg
│       ├── line_tracer_log_sender.cdl
│       ├── Makefile
│       └── install_to_spike_rt_sample.sh
├── temp.html                    # グラフ描画用の一時 HTML（実行時に自動生成、.gitignore）
├── build/                       # PyInstaller 中間出力（ビルド時のみ、.gitignore）
└── dist/                        # PyInstaller 成果物（ビルド時のみ、.gitignore）
```

ビルドや実行で生成される `logs/`・`temp.html`・`build/`・`dist/` は `.gitignore` 対象です。ローカル開発用の仮想環境（`la2/` 等）も同様に Git 管理外です。

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
