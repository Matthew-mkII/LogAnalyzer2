# SPIKE-RT 向け LogAnalyzer2 サンプル — ビルド・転送手順

LEGO SPIKE Prime ハブに [SPIKE-RT](https://github.com/spike-rt/spike-rt)（TOPPERS/ASP）ファームウェアを書き込み、C/C++ でアプリを動かしながら [LogAnalyzer2](../README.md) へ Bluetooth（NUS）でログを送信するための手順書です。

**本サンプルは SPIKE-RT 実機専用**です。etrobo のシミュレータ（RasPike / Athrill）ではビルドできません。

## 目次

1. [SPIKE-RT モードの有効化（最初に必ず行う）](#spike-rt-モードの有効化最初に必ず行う)
2. [クイックスタート（全体の流れ）](#クイックスタート全体の流れ)
3. [サンプル一覧](#サンプル一覧)
4. [前提環境](#前提環境)
5. [ソースのコピー（samples → etrobo workspace）](#ソースのコピーsamples--etrobo-workspace)
6. [ビルド](#ビルド)
7. [ハブへの書き込み（DFU モード）](#ハブへの書き込みdfu-モード)
8. [LogAnalyzer2 での受信](#loganalyzer2-での受信)
9. [送信データ形式](#送信データ形式)
10. [spike-rt-sample への配置（別ルート）](#spike-rt-sample-への配置別ルート)
11. [クリーンアップ](#クリーンアップ)
12. [トラブルシューティング](#トラブルシューティング)
13. [参考リンク](#参考リンク)

---

## SPIKE-RT モードの有効化（最初に必ず行う）

etrobo はデフォルトで **SPIKE（RasPike / シミュレータ）モード**です。LogAnalyzer2 の SPIKE-RT サンプルをビルドするには、先に **SPIKE-RT モード**へ切り替え、パッケージを取得してください。

### モードの違い

| モード | 切り替えファイル | workspace の実体 | 用途 |
|--------|------------------|------------------|------|
| SPIKE（デフォルト） | `SPIKE` または未指定 | `raspike-athrill-v850e2m/sdk/workspace` | シミュレータ |
| **SPIKE-RT** | `SPIKE_RT` | **`spike-rt/sdk/workspace`** | **SPIKE Prime 実機** |
| EV3 | `EV3` | `ev3rt-*/sdk/workspace` | EV3 実機 |

### 手順 1 — SPIKE-RT モードへ切り替え

etrobo のルート（`$ETROBO_ROOT`）で実行します。

```bash
cd "$ETROBO_ROOT"

# 他モードのマーカーファイルがあれば削除（任意）
rm -f SPIKE EV3 NXT

# SPIKE-RT モードを有効化
touch SPIKE_RT
```

**ターミナルを開き直す**（BeerHall を使っている場合は BeerHall を再起動）と、環境変数と `workspace` シンボリックリンクが更新されます。

### 手順 2 — 切り替えの確認

```bash
cd "$ETROBO_ROOT"
ls -l workspace
# 期待: workspace -> .../spike-rt/sdk/workspace

ls spike-rt/sdk/workspace
# hub-check, imu など SPIKE-RT 用サンプルが見えること
```

`workspace` がまだ `raspike-athrill-v850e2m/...` を指している場合は、ターミナルの再起動が完了していません。

### 手順 3 — SPIKE-RT パッケージの取得

初回は `spike-rt` ディレクトリが存在しません。etrobo ルートで `./update` を実行してクローンします。

```bash
cd "$ETROBO_ROOT"
./update
```

`clone SPIKE-RT core` と表示され、`spike-rt/` 以下に `sdk/workspace` が作成されれば成功です。

> **注意:** `spike-rt` が **空ファイル**のまま残っていると `./update` が失敗します。その場合は `rm -f spike-rt` してから `./update` を再実行してください。

### 手順 4 — Apple Silicon Mac（M1/M2/M3 等）の追加設定

etrobo が同梱する `gcc-arm-none-eabi` は **Intel Mac 向け (x86_64)** です。Apple Silicon では **Rosetta 2** が必要です。

```bash
softwareupdate --install-rosetta --agree-to-license
```

未インストールのままビルドすると次のエラーになります。

```text
arm-none-eabi-gcc: Bad CPU type in executable
```

### 手順 5 — ビルドコマンドの注意（`./make` を使う）

etrobo ルートの `make` は **ラッパースクリプト `./make`** です。システムの `make` や `workspace` 内の `make` だけでは `upload` や `sim` が使えません。

| 場所 | コマンド | 結果 |
|------|----------|------|
| `$ETROBO_ROOT` | `./make img=line_tracer_logger` | 正しい（推奨） |
| `$ETROBO_ROOT` | `make upload` | **`No rule to make target 'upload'`** |
| `workspace/` のみ | `make img=...` | 環境によってはパスエラー |

SPIKE-RT モードではプロジェクト指定は **`img=`** を使います（`app=` ではありません）。

---

## クイックスタート（全体の流れ）

```text
① SPIKE-RT モードを有効化（touch SPIKE_RT → ターミナル再起動）
        ↓
② ./update で spike-rt パッケージを取得
        ↓
③ LogAnalyzer2/samples から etrobo workspace へコピー
        ↓
④ ./make img=<プロジェクト名> でビルド（asp.bin 生成）
        ↓
⑤ ハブを DFU モードで USB 接続
        ↓
⑥ ./make upload（または ./make img=<名前> up）
        ↓
⑦ ハブ再起動 → LogAnalyzer2 で BLE 接続
```

コマンド例（ライントレース + ログ送信）:

```bash
# ①② SPIKE-RT 有効化・パッケージ取得（上記参照）
cd "$ETROBO_ROOT"
touch SPIKE_RT
# ターミナルを開き直す
./update

# ③ コピー（LogAnalyzer2 のパスは環境に合わせて変更）
cd /path/to/LogAnalyzer2
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh

# ④ ビルド
cd "$ETROBO_ROOT"
./make img=line_tracer_logger

# ⑤⑥ DFU 接続後に転送
./make upload
# またはビルドと同時: ./make img=line_tracer_logger up
```

---

## サンプル一覧

| ディレクトリ | 内容 | workspace へのコピー |
|-------------|------|---------------------|
| [`spike_rt_log_sender/`](spike_rt_log_sender/) | センサー値のみ BLE 送信（走行なし） | `install_to_etrobo_workspace.sh` |
| [`spike_rt_line_tracer_log_sender/`](spike_rt_line_tracer_log_sender/) | ライントレース + ログ送信 | `install_to_etrobo_workspace.sh` |
| `spike_rt_log_sender.cpp` | 参考用 C++ スケッチ（単体ビルド不可） | — |
| `spike_rt_line_tracer.cpp` | 参考用 C++ スケッチ（単体ビルド不可） | — |

詳細 API は各サブディレクトリの README を参照:

- [spike_rt_log_sender/README.md](spike_rt_log_sender/README.md)

---

## 前提環境

### ハードウェア

- LEGO Education SPIKE Prime ハブ
- **データ通信対応**の USB ケーブル（充電専用ケーブルは不可）
- Mac では可能な限り **USB ハブを挟まず**本体ポートへ直接接続

### ソフトウェア

| 項目 | 説明 |
|------|------|
| [LogAnalyzer2](../README.md) | 本リポジトリ |
| [etrobo](https://github.com/ETrobocon/etrobo) | SPIKE-RT ビルド環境（例: `$ETROBO_ROOT`） |
| SPIKE-RT モード | 上記「[SPIKE-RT モードの有効化](#spike-rt-モードの有効化最初に必ず行う)」を完了していること |
| Rosetta 2（Apple Silicon のみ） | x86_64 用クロスコンパイラ実行に必要 |

### USB 確認コマンド（Mac）

```bash
lsusb | grep 0694
spike device       # DFU / HubOS / Pybricks
```

---

## ソースのコピー（samples → etrobo workspace）

LogAnalyzer2 のソースは **`LogAnalyzer2/samples/`** にあります。  
etrobo のビルドは **`$ETROBO_ROOT/workspace/`**（= `spike-rt/sdk/workspace`）で行うため、SPIKE-RT モード有効化後にサンプルを workspace へコピーします。

インストールスクリプトは `workspace` に `Makefile` があるか確認します。SPIKE-RT モードで `./update` 済みであることが前提です。

### 方法 A — インストールスクリプト（推奨）

#### ログ送信のみ（`spike_rt_log_sender`）

```bash
cd /path/to/LogAnalyzer2
./samples/spike_rt_log_sender/install_to_etrobo_workspace.sh
```

デフォルトで `$ETROBO_ROOT/workspace/log_sender/` に配置されます。

プロジェクト名や workspace パスを明示する場合:

```bash
./samples/spike_rt_log_sender/install_to_etrobo_workspace.sh \
  log_sender \
  "$ETROBO_ROOT/workspace"
```

#### ライントレース + ログ送信（`spike_rt_line_tracer_log_sender`）

```bash
cd /path/to/LogAnalyzer2
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh
```

デフォルトで `$ETROBO_ROOT/workspace/line_tracer_logger/` に配置されます。

```bash
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh \
  line_tracer_logger \
  "$ETROBO_ROOT/workspace"
```

スクリプトは次の変換を行います（etrobo workspace 形式に合わせる）:

| samples 側のファイル | workspace 側 |
|---------------------|----------------|
| `log_sender.cdl` / `line_tracer_log_sender.cdl` | `app.cdl` |
| `log_sender.cfg` / `line_tracer_log_sender.cfg` | `app.cfg`（`#include` を `app.h` に変更） |
| `log_sender_app.h` / `line_tracer_log_sender.h` | `app.h` |
| `log_sender_app.c` / `line_tracer_log_sender.c` | `app.c`（`#include` を `app.h` に変更） |
| `log_sender.c` / `log_sender.h` | そのまま同フォルダへ（log_sender のみ） |
| （自動生成） | `Makefile.inc` |

配置後のディレクトリ例:

```text
spike-rt/sdk/workspace/
├── Makefile
├── log_sender/              ← spike_rt_log_sender からコピー
│   ├── app.c
│   ├── app.h
│   ├── app.cfg
│   ├── app.cdl
│   ├── log_sender.c
│   ├── log_sender.h
│   └── Makefile.inc
└── line_tracer_logger/      ← spike_rt_line_tracer_log_sender からコピー
    ├── app.c
    ├── app.h
    ├── app.cfg
    ├── app.cdl
    └── Makefile.inc
```

### 方法 B — 手動コピー

スクリプトを使わない場合は、上表のとおりリネームしながら `workspace/<プロジェクト名>/` を作成します。  
`hub-check/` など SPIKE-RT 同梱サンプルの構成も参考にできます。

**log_sender の `Makefile.inc` 例:**

```makefile
APPL_COBJS +=\
log_sender.o\

APPL_LIBS += -lm
```

**line_tracer の `Makefile.inc` 例:**

```makefile
APPL_LIBS += -lm
```

---

## ビルド

**必ず `$ETROBO_ROOT` で `./make` を使います。**

```bash
cd "$ETROBO_ROOT"
./make img=line_tracer_logger
# または
./make img=log_sender
```

成功すると `spike-rt/sdk/workspace/asp.bin` が生成され、末尾に `build succeed` / `configuration check passed` と表示されます。初回ビルドはカーネル全体のコンパイルのため **数分**かかります。

### ビルド + 転送を一度に

ハブを DFU モード（後述）にしたうえで:

```bash
cd "$ETROBO_ROOT"
./make img=line_tracer_logger up
```

### 転送のみ（ビルド済みの場合）

```bash
cd "$ETROBO_ROOT"
./make upload
```

内部処理: `asp.bin` → `firmware.dfu` 生成 → `pydfu.py` で VID `0x0694` / PID `0x0008` へ書き込み。

---

## ハブへの書き込み（DFU モード）

SPIKE-RT へのアプリ転送は **DFU モードのときだけ**可能です。

### USB ID とモード

| モード | USB ID (`lsusb`) | 転送 |
|--------|------------------|------|
| **DFU** | `0694:0008` | **可能** |
| HubOS（LEGO 標準） | `0694:0009` | 不可 |
| Pybricks | `0483:5740` | 不可 |

### DFU モードの入り方

1. ハブの USB を **いったん抜く**
2. 背面の **Bluetooth ボタンを押し続ける**
3. **押したまま** USB ケーブルを Mac に接続
4. 数秒待ってからボタンを離す（画面は **真っ暗** で正常）

### 認識確認

```bash
lsusb | grep 0694    # 0694:0008 が出れば OK
spike device         # "DFU" と表示されれば OK
```

### 書き込み

```bash
cd "$ETROBO_ROOT"
./make upload
```

DFU でない場合は次のメッセージで失敗します。

```text
[fakemake on SPIKE-RT] *** upload failed: SPIKE device not found in DFU mode.
```

成功後、USB を抜いて電源を入れ直すとアプリが起動します。

---

## LogAnalyzer2 での受信

### ログ送信サンプル（`log_sender`）

1. 書き込み後、電源 ON（画面 `READY`）
2. LogAnalyzer2 を起動 → **スキャン** → ハブを選択 → **接続**
3. グラフと `logs/*.csv` に記録（約 60 秒で `DONE`）

### ライントレース + ログ送信（`line_tracer_logger`）

#### 配線（ソース内の定義）

| ポート | デバイス |
|--------|----------|
| Port A | 右モーター |
| Port B | 左モーター |
| Port D | フォースセンサー（開始ボタン） |
| Port E | カラーセンサー |

#### 操作

1. 起動後 `READY` 表示 → LogAnalyzer2 で BLE 接続
2. フォースセンサー 1 回目: ライン閾値を測定
3. フォースセンサー 2 回目: ライントレース開始（最大約 60 秒）

---

## 送信データ形式

CSV（15 列、1 行 1 レコード、末尾改行）:

```csv
time, turn, speed, battery, angleL, angleR, hue, saturation, value, Kp, Ki, Kd, roll, yaw, pitch
```

| 列名 | 内容 | 単位 |
|------|------|------|
| `time` | 経過時間 | ms |
| `battery` | バッテリー電圧 | mV |
| `hue` / `saturation` / `value` | カラーセンサー | - |
| `roll` / `yaw` / `pitch` | IMU | deg |
| `Kp` / `Ki` / `Kd` | PID ゲイン（ライントレース時） | - |

### PID 調整のヒント

| 症状 | 対策 |
|------|------|
| 蛇行が激しい | `Kp` を下げる、`Kd` を上げる |
| ラインから外れる | `Kp` を上げる |
| 定常偏差がある | `Ki` を少し増やす |

---

## spike-rt-sample への配置（別ルート）

etrobo を使わず [spike-rt-sample](https://github.com/Hiyama1026/spike-rt-sample) 単体でビルドする場合:

```bash
cd /path/to/LogAnalyzer2

# ログ送信のみ
./samples/spike_rt_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
cd /path/to/spike-rt-sample/API-sample/log_sender && make

# ライントレース + ログ送信
./samples/spike_rt_line_tracer_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
cd /path/to/spike-rt-sample/API-sample/line_tracer_log_sender && make
```

etrobo 環境では spike-rt-sample は `$ETROBO_ROOT/spike-rt/spike-rt-sample` に置かれることが多いです。  
書き込みは `make deploy-lin`（Linux/WSL）等。**etrobo では `./make upload`** を使います。

---

## クリーンアップ

```bash
cd "$ETROBO_ROOT"
./make clean       # 直近アプリのオブジェクト削除
./make realclean   # カーネルライブラリも削除
```

サンプルを再コピーする場合は、対象フォルダを削除してからインストールスクリプトを再実行してください。

```bash
rm -rf "$ETROBO_ROOT/workspace/line_tracer_logger"
/path/to/LogAnalyzer2/samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh
```

---

## トラブルシューティング

### `spike-rt/sdk/workspace: Not a directory` / `project not found`

- SPIKE-RT モードが有効か: `ls "$ETROBO_ROOT/SPIKE_RT"`
- `spike-rt` が空ファイルでないか: `file "$ETROBO_ROOT/spike-rt"`
  - 空ファイルなら `rm -f spike-rt` のあと `./update`
- ターミナル再起動後、`ls -l workspace` が `spike-rt/sdk/workspace` を指すか確認

### `make: No rule to make target 'upload'`

- **`make` ではなく `./make`** を `$ETROBO_ROOT` で実行しているか確認
- `workspace` ディレクトリ内だけで `make upload` しても動きません

### `arm-none-eabi-gcc: Bad CPU type in executable`（Apple Silicon）

- Rosetta 2 をインストール: `softwareupdate --install-rosetta --agree-to-license`
- インストール後、同じ `./make img=...` を再実行

### `ValueError: No DFU device found` / `SPIKE device not found in DFU mode`

- `lsusb | grep 0694` → `0694:0008` を確認
- `spike device` → `DFU` を確認
- Bluetooth ボタン押しながら USB 接続をやり直す

### `lsusb | grep 0694` が何も出ない

```bash
lsusb    # grep なしで接続前後を比較
```

行が増えなければケーブルまたはポートの問題です。

### ビルドエラー（tecsgen / `SIOPortTarget1`）

- `app.cdl` が現行 SPIKE-RT と合っているか確認（`hub-check/app.cdl` を参考に、未使用 UART ポート定義をコメントアウト）
- インストールスクリプトを再実行して上書きコピー

### その他のビルドエラー

- `./make img=` の名前が `workspace/<プロジェクト名>/` と一致しているか
- コピー後に `app.c` / `app.cfg` / `app.cdl` / `Makefile.inc` が揃っているか

### BLE 接続できない

- Pybricks Code 等の他アプリが接続していないか確認
- ハブ再起動後に LogAnalyzer2 から再接続

### シミュレータで動かしたい場合

SPIKE-RT サンプルは実機専用です。シミュレータでライントレースを試す場合は **SPIKE モード**（`rm SPIKE_RT` → ターミナル再起動）で `./make app=sample_c5_spike sim up` 等を利用してください。

---

## 参考リンク

- [SPIKE-RT 公式](https://github.com/spike-rt/spike-rt)
- [etrobo README](https://github.com/ETrobocon/etrobo)
- [LogAnalyzer2 README](../README.md)
- [spike_rt_log_sender 詳細](spike_rt_log_sender/README.md)

## 注意事項

- SPIKE-RT は LEGO 公式ファームウェアを上書きします。復元には公式アプリ等が必要です。

## ライセンス

MIT License
