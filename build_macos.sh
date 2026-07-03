#!/bin/bash
# LogAnalyzer2 — macOS 向け PyInstaller ビルドスクリプト
#
# 使い方:
#   ./build_macos.sh
#
# 出力: dist/LogAnalyzer2/mac/LogAnalyzer2 （フォルダごと配布）

set -euo pipefail

cd "$(dirname "$0")"

DIST_DIR="dist/LogAnalyzer2/mac"
VENV_ACTIVATE="la2/bin/activate"

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "[1/5] Creating virtual environment..."
  python3 -m venv la2
fi

# shellcheck disable=SC1091
source "$VENV_ACTIVATE"

echo "[2/5] Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements-build.txt

echo "[3/5] Building LogAnalyzer2 ..."
pyinstaller --distpath dist/LogAnalyzer2 --noconfirm LogAnalyzer2.spec

echo "[4/5] Copying license files for distribution..."
if [ ! -d "$DIST_DIR" ]; then
  echo "Distribution folder not found: $DIST_DIR"
  exit 1
fi

cp LICENSE "$DIST_DIR/"
cp THIRD_PARTY_NOTICES.txt "$DIST_DIR/"

if [ ! -d licenses ]; then
  echo "licenses folder not found"
  exit 1
fi

mkdir -p "$DIST_DIR/licenses"
cp licenses/*.txt "$DIST_DIR/licenses/"

echo "[5/5] Done."
echo "Output: $DIST_DIR/LogAnalyzer2"
echo "License files copied to $DIST_DIR"
echo "Copy the entire $DIST_DIR folder when distributing."
