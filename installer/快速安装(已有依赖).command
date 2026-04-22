#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# VC Research 快速安装器 (macOS)
# 复制源码 + 安装依赖 + 创建桌面 App + 启动 Dashboard
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── 清除 macOS 隔离标记（AirDrop 传输会添加）──
xattr -d com.apple.quarantine "$0" 2>/dev/null || true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
fail()    { echo -e "${RED}✗${NC}  $*"; }
step()    { echo -e "\n${CYAN}${BOLD}━━━ [$1/4] $2 ━━━${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/vc-research-src" ]]; then
    SOURCE_DIR="$SCRIPT_DIR/vc-research-src"
elif [[ -d "$SCRIPT_DIR/../src/vc_research" ]]; then
    SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    SOURCE_DIR=""
fi

INSTALL_DIR="$HOME/vc-research"
VENV_DIR="$INSTALL_DIR/.venv"

# ── Homebrew PATH ──
ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PREFIX="/usr/local"
fi
export PATH="$BREW_PREFIX/bin:$PATH"
eval "$($BREW_PREFIX/bin/brew shellenv)" 2>/dev/null || true

clear
echo -e "${BOLD}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   🔬  VC Research — 快速安装                         ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"
echo -e "  按 ${BOLD}回车${NC} 开始，或 ${BOLD}Ctrl+C${NC} 取消..."
read -r

# ──────────────────────────────────────────────────────────────
# 1. 复制源码
# ──────────────────────────────────────────────────────────────
step 1 "复制源码"

if [[ -n "$SOURCE_DIR" && -d "$SOURCE_DIR/src/vc_research" ]]; then
    mkdir -p "$INSTALL_DIR"
    rsync -a --delete --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='.env' \
          "$SOURCE_DIR/" "$INSTALL_DIR/"
    success "源码已复制到 $INSTALL_DIR"
else
    fail "未找到源码目录，请确认从 DMG 中运行"
    read -rp "按回车关闭..."; exit 1
fi

# ──────────────────────────────────────────────────────────────
# 2. 系统依赖 + Python 虚拟环境
# ──────────────────────────────────────────────────────────────
step 2 "安装依赖"

# 检测 Python
PYTHON_CMD=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON_CMD="$candidate"
        break
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    fail "未找到 Python 3.10+，请先运行「完整安装(首次)」"
    read -rp "按回车关闭..."; exit 1
fi
info "Python: $($PYTHON_CMD --version 2>&1)"

# 安装 PDF 渲染所需的系统库（weasyprint 依赖）
BREW_DEPS=(pango cairo glib gdk-pixbuf libffi)
MISSING=()
for dep in "${BREW_DEPS[@]}"; do
    brew list "$dep" &>/dev/null || MISSING+=("$dep")
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
    info "安装系统依赖: ${MISSING[*]}..."
    brew install "${MISSING[@]}"
fi
success "系统依赖就绪"

# 创建虚拟环境
if [[ ! -d "$VENV_DIR" ]]; then
    info "创建虚拟环境..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet 2>/dev/null

info "安装 vc-research（可能需要 1-2 分钟）..."
if ! pip install -e "$INSTALL_DIR" 2>&1; then
    fail "pip install 失败，请检查上方错误信息"
    read -rp "按回车关闭..."; exit 1
fi

if [[ -x "$VENV_DIR/bin/vc-research" ]]; then
    success "vc-research 命令就绪"
else
    fail "安装失败 — vc-research 命令未生成"
    read -rp "按回车关闭..."; exit 1
fi

# ──────────────────────────────────────────────────────────────
# 3. 创建桌面 App
# ──────────────────────────────────────────────────────────────
step 3 "创建桌面 App"

if [[ -f "$INSTALL_DIR/installer/create_app.sh" ]]; then
    bash "$INSTALL_DIR/installer/create_app.sh" "$INSTALL_DIR"
    success "VC Research.app 已放置到桌面"
else
    warn "未找到 create_app.sh，跳过桌面 App"
fi

# ──────────────────────────────────────────────────────────────
# 4. 配置 Shell 快捷命令
# ──────────────────────────────────────────────────────────────
step 4 "配置快捷命令"

cat > "$INSTALL_DIR/activate.sh" << 'ACTIVATE_INNER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
echo "✓ vc-research 环境已激活"
ACTIVATE_INNER
chmod +x "$INSTALL_DIR/activate.sh"

ZSHRC="$HOME/.zshrc"
MARKER="# vc-research"
if ! grep -q "$MARKER" "$ZSHRC" 2>/dev/null; then
    cat >> "$ZSHRC" << SHELL_EOF

$MARKER
alias vcr='source $INSTALL_DIR/activate.sh && vc-research'
alias vcr-dashboard='source $INSTALL_DIR/activate.sh && python $INSTALL_DIR/web/dashboard.py'
SHELL_EOF
    success "已添加 vcr / vcr-dashboard 到 ~/.zshrc"
else
    success "快捷命令已存在"
fi

# ──────────────────────────────────────────────────────────────
# 完成 + 启动 Dashboard
# ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ✅ 安装完成！${NC}"
echo ""
echo -e "  ${BOLD}正在启动 Dashboard...${NC}"
echo -e "  ${DIM}关闭此窗口会停止 Dashboard${NC}"
echo -e "  ${DIM}日后使用: 双击桌面「VC Research」图标${NC}"
echo ""

"$VENV_DIR/bin/python" "$INSTALL_DIR/web/dashboard.py"
