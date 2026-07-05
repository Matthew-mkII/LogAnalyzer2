#!/bin/bash
# -----------------------------------------------------------------------------
# install_to_spike_rt_sample.sh
#
# LogAnalyzer2 の SPIKE-RT ログ送信専用サンプルを spike-rt-sample へコピーします。
#
# 使い方:
#   ./install_to_spike_rt_sample.sh /path/to/spike-rt-sample
# -----------------------------------------------------------------------------
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/spike-rt-sample" >&2
  exit 1
fi

SAMPLE_ROOT="$1"
TARGET_DIR="$SAMPLE_ROOT/API-sample/log_sender"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$SAMPLE_ROOT/API-sample/template" ]; then
  echo "Error: spike-rt-sample not found at $SAMPLE_ROOT" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -r "$SAMPLE_ROOT/API-sample/template/objs" "$TARGET_DIR/"
cp "$SOURCE_DIR"/* "$TARGET_DIR/"

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "  cd $TARGET_DIR"
echo "  make"
echo "  make deploy-lin   # Linux / WSL。macOS は deploy-win 等を参照"
