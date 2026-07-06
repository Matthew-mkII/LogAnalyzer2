# SPIKE-RT 向け LogAnalyzer2 サンプル — ビルド・転送手順

LEGO SPIKE Prime ハブに [SPIKE-RT](https://github.com/spike-rt/spike-rt)（TOPPERS/ASP）ファームウェアを書き込み、C/C++ でアプリを動かしながら [LogAnalyzer2](../README.md) へ Bluetooth（NUS）でログを送信するための手順書です。

## 目次

1. [クイックスタート（全体の流れ）](#クイックスタート全体の流れ)
2. [サンプル一覧](#サンプル一覧)
3. [前提環境](#前提環境)
4. [ソースのコピー（samples → etrobo workspace）](#ソースのコピーsamples--etrobo-workspace)
5. [ビルド](#ビルド)
6. [ハブへの書き込み（DFU モード）](#ハブへの書き込みdfu-モード)
7. [LogAnalyzer2 での受信](#loganalyzer2-での受信)
8. [送信データ形式](#送信データ形式)
9. [spike-rt-sample への配置（別ルート）](#spike-rt-sample-への配置別ルート)
10. [クリーンアップ](#クリーンアップ)
11. [トラブルシューティング](#トラブルシューティング)
12. [参考リンク](#参考リンク)

---

## クイックスタート（全体の流れ）

etrobo + SPIKE-RT モードで、LogAnalyzer2 サンプルを動かすまでの流れです。

```text
① LogAnalyzer2/samples から etrobo workspace へコピー
        ↓
② make img=<プロジェクト名> でビルド（asp.bin 生成）
        ↓
③ ハブを DFU モードで USB 接続
        ↓
④ make upload（または make app=<名前> up）
        ↓
⑤ ハブ再起動 → LogAnalyzer2 で BLE 接続
```

コマンド例（ライントレース + ログ送信）:

```bash
# ① コピー
cd ~/python/LogAnalyzer2
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh

# ② ビルド
cd "$ETROBO_ROOT/workspace"
make img=line_tracer_logger

# ③④ DFU 接続後に転送
make upload
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
| [LogAnalyzer2](../README.md) | 本リポジトリ（`~/python/LogAnalyzer2`） |
| [etrobo](https://github.com/ETrobocon/etrobo) | SPIKE-RT ビルド環境（例: `$HOME/SPIKE-RT/etrobo`） |
| SPIKE-RT モード | etrobo 内で `touch SPIKE_RT` 後、ターミナルを開き直す |

```bash
cd "$ETROBO_ROOT"
touch SPIKE_RT
# ターミナルを開き直す

ls -l workspace    # → .../spike-rt/sdk/workspace
```

### USB 確認コマンド（Mac）

```bash
lsusb | grep 0694
spike device       # DFU / HubOS / Pybricks
```

---

## ソースのコピー（samples → etrobo workspace）

LogAnalyzer2 のソースは **`~/python/LogAnalyzer2/samples/`** にあります。  
etrobo のビルドは **`$ETROBO_ROOT/workspace/`**（= `spike-rt/sdk/workspace`）で行うため、まずサンプルを workspace へコピーします。

### 方法 A — インストールスクリプト（推奨）

#### ログ送信のみ（`spike_rt_log_sender`）

```bash
cd ~/python/LogAnalyzer2
./samples/spike_rt_log_sender/install_to_etrobo_workspace.sh
```

デフォルトで `$ETROBO_ROOT/workspace/log_sender/` に配置されます。

プロジェクト名や workspace パスを指定する場合:

```bash
./samples/spike_rt_log_sender/install_to_etrobo_workspace.sh \
  log_sender \
  "$HOME/SPIKE-RT/etrobo/workspace"
```

#### ライントレース + ログ送信（`spike_rt_line_tracer_log_sender`）

```bash
cd ~/python/LogAnalyzer2
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh
```

デフォルトで `$ETROBO_ROOT/workspace/line_tracer_logger/` に配置されます。

```bash
./samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh \
  line_tracer_logger \
  "$HOME/SPIKE-RT/etrobo/workspace"
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
workspace/
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
`sample_c5/` の構成も参考にできます。

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

コピー済みのプロジェクト名を `img=`（または `app=`）に指定します。

### workspace 直下でビルド

```bash
cd "$ETROBO_ROOT/workspace"
make img=line_tracer_logger
# または
make img=log_sender
```

成功すると `workspace/asp.bin` が生成され、`configuration check passed` と表示されます。

### etrobo ルートからビルド（fakemake 経由）

```bash
cd "$ETROBO_ROOT"
make app=line_tracer_logger
```

`app=` の値は `currentapp` に記録され、次回以降は `make up` で同じプロジェクトをビルドできます。

### ビルド + 転送を一度に

ハブを DFU モード（後述）にしたうえで:

```bash
cd "$ETROBO_ROOT"
make app=line_tracer_logger up
```

### 転送のみ

```bash
cd "$ETROBO_ROOT/workspace"
make upload
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
cd "$ETROBO_ROOT/workspace"
make upload
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
cd ~/python/LogAnalyzer2

# ログ送信のみ
./samples/spike_rt_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
cd /path/to/spike-rt-sample/API-sample/log_sender && make

# ライントレース + ログ送信
./samples/spike_rt_line_tracer_log_sender/install_to_spike_rt_sample.sh /path/to/spike-rt-sample
cd /path/to/spike-rt-sample/API-sample/line_tracer_log_sender && make
```

etrobo 環境では spike-rt-sample は `$ETROBO_ROOT/spike-rt/spike-rt-sample` に置かれることが多いです。  
書き込みは `make deploy-lin`（Linux/WSL）等。**etrobo workspace では `make upload`** を使います。

---

## クリーンアップ

```bash
cd "$ETROBO_ROOT/workspace"
make clean       # 直近アプリのオブジェクト削除
make realclean   # カーネルライブラリも削除
make distclean   # 全アプリの build/ を削除
```

サンプルを再コピーする場合は、対象フォルダを削除してからインストールスクリプトを再実行してください。

```bash
rm -rf "$ETROBO_ROOT/workspace/line_tracer_logger"
~/python/LogAnalyzer2/samples/spike_rt_line_tracer_log_sender/install_to_etrobo_workspace.sh
```

---

## トラブルシューティング

### `ValueError: No DFU device found`

- `lsusb | grep 0694` → `0694:0008` を確認
- `spike device` → `DFU` を確認
- Bluetooth ボタン押しながら USB 接続をやり直す

### `lsusb | grep 0694` が何も出ない

```bash
lsusb    # grep なしで接続前後を比較
```

行が増えなければケーブルまたはポートの問題です。

### ビルドエラー

- `make img=` の名前が workspace 内フォルダ名と一致しているか
- コピー後に `app.c` / `app.cfg` / `app.cdl` / `Makefile.inc` が揃っているか
- インストールスクリプトを再実行して上書きコピー

### BLE 接続できない

- Pybricks Code 等の他アプリが接続していないか確認
- ハブ再起動後に LogAnalyzer2 から再接続

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
