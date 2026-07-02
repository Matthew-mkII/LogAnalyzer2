#!/bin/bash
# -----------------------------------------------------------------------------
# install_to_spike_rt_sample.sh
#
# LogAnalyzer2 の SPIKE-RT サンプルを spike-rt-sample の API-sample へコピーします。
# SPIKE-RT のビルドは spike-rt-sample ツリー内で行う必要があるため、
# 本リポジトリのソースをそちらへ配置するための補助スクリプトです。
#
# 使い方:
#   ./install_to_spike_rt_sample.sh /path/to/spike-rt-sample
#
# 前提:
#   - spike-rt と spike-rt-sample がクローン済みであること
#   - spike-rt-sample/API-sample/template が存在すること
# -----------------------------------------------------------------------------
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/spike-rt-sample" >&2
  exit 1
fi

SAMPLE_ROOT="$1"
TARGET_DIR="$SAMPLE_ROOT/API-sample/line_tracer_log_sender"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

# spike-rt-sample の存在確認
if [ ! -d "$SAMPLE_ROOT/API-sample/template" ]; then
  echo "Error: spike-rt-sample not found at $SAMPLE_ROOT" >&2
  exit 1
fi

# 既存ビルド成果物を消してから上書きコピー
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

# template/objs … ビルド用の空ディレクトリ構造
cp -r "$SAMPLE_ROOT/API-sample/template/objs" "$TARGET_DIR/"
# ソース・Makefile・CDL 等
cp "$SOURCE_DIR"/* "$TARGET_DIR/"

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "  cd $TARGET_DIR"
echo "  make"
echo "  make deploy-lin   # Linux / WSL。macOS は deploy-win 等を参照"
