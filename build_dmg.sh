#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# 构建 VC Research macOS 安装 DMG
# 用法: bash build_dmg.sh
# 输出: dist/VC-Research-Installer.dmg (约 10-15MB)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION=$(grep '__version__' "$PROJECT_DIR/src/vc_research/__init__.py" | cut -d'"' -f2)
DMG_NAME="VC-Research-${VERSION}-Installer"
BUILD_DIR="$PROJECT_DIR/dist/dmg-staging"
DMG_PATH="$PROJECT_DIR/dist/${DMG_NAME}.dmg"

echo -e "${BOLD}构建 VC Research v${VERSION} macOS 安装 DMG${NC}"
echo ""

# ── 清理 ──
rm -rf "$BUILD_DIR" "$DMG_PATH"
mkdir -p "$BUILD_DIR"

# ── 复制源码（排除不需要的文件）──
info "打包源码..."
SRC_DIR="$BUILD_DIR/vc-research-src"
mkdir -p "$SRC_DIR"

rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.env' \
    --exclude='.claude' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    --exclude='installer' \
    "$PROJECT_DIR/" "$SRC_DIR/"

success "源码打包完成 ($(du -sh "$SRC_DIR" | cut -f1))"

# ── 复制安装器 ──
info "复制安装器..."
cp "$PROJECT_DIR/installer/安装 VC Research.command" "$BUILD_DIR/"
cp "$PROJECT_DIR/installer/README.txt" "$BUILD_DIR/"
chmod +x "$BUILD_DIR/安装 VC Research.command"

# ── 创建 .background 图标说明 (纯文本替代) ──
# 创建一个简短的 DS_Store 提示
cat > "$BUILD_DIR/.vol_label" << 'EOF'
VC Research Installer
EOF

success "安装器就绪"

# ── 构建 DMG ──
info "生成 DMG (${DMG_NAME}.dmg)..."
mkdir -p "$PROJECT_DIR/dist"

# 使用 hdiutil 创建 DMG
hdiutil create \
    -volname "VC Research 安装器" \
    -srcfolder "$BUILD_DIR" \
    -ov \
    -format UDZO \
    -fs HFS+ \
    "$DMG_PATH" \
    2>/dev/null

# ── 清理临时文件 ──
rm -rf "$BUILD_DIR"

# ── 完成 ──
DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
echo ""
success "DMG 构建完成！"
echo ""
echo -e "  ${BOLD}文件:${NC} $DMG_PATH"
echo -e "  ${BOLD}大小:${NC} $DMG_SIZE"
echo -e "  ${BOLD}版本:${NC} v${VERSION}"
echo ""
echo -e "  ${CYAN}分发方式:${NC}"
echo -e "  • 隔空投送 (AirDrop): 在 Finder 中右键 → 共享 → 隔空投送"
echo -e "  • 直接拷贝: 通过 U盘/网盘/邮件 发送 DMG 文件"
echo -e "  • GitHub Release: gh release create v${VERSION} '$DMG_PATH'"
echo ""
echo -e "  ${CYAN}接收方使用:${NC}"
echo -e "  1. 双击打开 DMG"
echo -e "  2. 双击「安装 VC Research.command」"
echo -e "  3. 按提示完成安装（全自动,约 5-15 分钟）"
echo ""
