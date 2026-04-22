#!/usr/bin/env bash
# 双击运行: 创建桌面 App + 启动 Dashboard
xattr -d com.apple.quarantine "$0" 2>/dev/null || true
set -euo pipefail

INSTALL_DIR="$HOME/vc-research"

echo "🔧 正在创建桌面 App..."
bash "$INSTALL_DIR/installer/create_app.sh" "$INSTALL_DIR"

echo ""
echo "✅ 桌面 App 已创建！正在启动 Dashboard..."
echo ""
"$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/web/dashboard.py"
