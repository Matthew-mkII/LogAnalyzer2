#!/bin/bash
# -----------------------------------------------------------------------------
# install_to_etrobo_workspace.sh
#
# LogAnalyzer2 の SPIKE-RT ログ送信サンプルを etrobo workspace へコピーします。
#
# 使い方:
#   ./install_to_etrobo_workspace.sh [プロジェクト名] [workspaceパス]
#
# 例:
#   ./install_to_etrobo_workspace.sh
#   ./install_to_etrobo_workspace.sh log_sender "$HOME/SPIKE-RT/etrobo/workspace"
# -----------------------------------------------------------------------------
set -euo pipefail

PROJECT_NAME="${1:-log_sender}"
WORKSPACE="${2:-${ETROBO_ROOT:-$HOME/etrobo}/workspace}"
ETROBO_ROOT="${ETROBO_ROOT:-$(dirname "$WORKSPACE")}"
TARGET_DIR="$WORKSPACE/$PROJECT_NAME"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$WORKSPACE/Makefile" ]; then
  echo "Error: etrobo workspace not found at $WORKSPACE" >&2
  echo "Hint: SPIKE-RT モードの etrobo 環境で workspace が存在するか確認してください。" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SOURCE_DIR/log_sender.cdl" "$TARGET_DIR/app.cdl"
sed 's/log_sender_app\.h/app.h/' "$SOURCE_DIR/log_sender.cfg" > "$TARGET_DIR/app.cfg"
cp "$SOURCE_DIR/log_sender_app.h" "$TARGET_DIR/app.h"
cp "$SOURCE_DIR/log_sender.h" "$TARGET_DIR/"
cp "$SOURCE_DIR/log_sender.c" "$TARGET_DIR/"
sed -e 's/log_sender_app\.h/app.h/' "$SOURCE_DIR/log_sender_app.c" > "$TARGET_DIR/app.c"

cat > "$TARGET_DIR/Makefile.inc" <<'EOF'
APPL_COBJS +=\
log_sender.o\

APPL_LIBS += -lm
EOF

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "  cd \"$ETROBO_ROOT\""
echo "  ./make img=$PROJECT_NAME"
echo "  # ハブを DFU モードにしてから:"
echo "  ./make upload"
