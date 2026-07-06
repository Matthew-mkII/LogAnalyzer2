#!/bin/bash
# -----------------------------------------------------------------------------
# install_to_etrobo_workspace.sh
#
# LogAnalyzer2 の SPIKE-RT ライントレース + ログ送信サンプルを
# etrobo workspace へコピーします。
#
# 使い方:
#   ./install_to_etrobo_workspace.sh [プロジェクト名] [workspaceパス]
#
# 例:
#   ./install_to_etrobo_workspace.sh
#   ./install_to_etrobo_workspace.sh line_tracer_logger "$HOME/SPIKE-RT/etrobo/workspace"
# -----------------------------------------------------------------------------
set -euo pipefail

PROJECT_NAME="${1:-line_tracer_logger}"
WORKSPACE="${2:-${ETROBO_ROOT:-$HOME/etrobo}/workspace}"
TARGET_DIR="$WORKSPACE/$PROJECT_NAME"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$WORKSPACE/Makefile" ]; then
  echo "Error: etrobo workspace not found at $WORKSPACE" >&2
  echo "Hint: SPIKE-RT モードの etrobo 環境で workspace が存在するか確認してください。" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SOURCE_DIR/line_tracer_log_sender.cdl" "$TARGET_DIR/app.cdl"
sed 's/line_tracer_log_sender\.h/app.h/' "$SOURCE_DIR/line_tracer_log_sender.cfg" > "$TARGET_DIR/app.cfg"
cp "$SOURCE_DIR/line_tracer_log_sender.h" "$TARGET_DIR/app.h"
sed 's/line_tracer_log_sender\.h/app.h/' "$SOURCE_DIR/line_tracer_log_sender.c" > "$TARGET_DIR/app.c"

cat > "$TARGET_DIR/Makefile.inc" <<'EOF'
APPL_LIBS += -lm
EOF

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "  cd $WORKSPACE"
echo "  make img=$PROJECT_NAME"
echo "  # ハブを DFU モードにしてから:"
echo "  make upload"
