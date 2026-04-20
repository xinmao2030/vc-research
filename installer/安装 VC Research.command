#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# VC Research 一键安装器 (macOS)
# 双击此文件即可自动安装所有依赖和程序
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── 颜色 ──
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
step()    { echo -e "\n${CYAN}${BOLD}━━━ [$1/7] $2 ━━━${NC}"; }

# ── 定位安装源（DMG 挂载点或本地目录）──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 如果从 DMG 运行，源码在同级 vc-research-src/ 目录
if [[ -d "$SCRIPT_DIR/vc-research-src" ]]; then
    SOURCE_DIR="$SCRIPT_DIR/vc-research-src"
elif [[ -d "$SCRIPT_DIR/../src/vc_research" ]]; then
    # 从仓库内 installer/ 目录运行
    SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    SOURCE_DIR=""
fi

INSTALL_DIR="$HOME/vc-research"
VENV_DIR="$INSTALL_DIR/.venv"
MIN_PYTHON="3.10"
OLLAMA_MODEL="qwen3:8b"

# ── Banner ──
clear
echo -e "${BOLD}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   🔬  VC Research — 创投企业投资分析系统             ║
  ║                                                      ║
  ║   输入企业名 → 自动输出 7 层结构化投研报告           ║
  ║   支持分析任意中国 Pre-IPO / 已上市企业              ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"
echo -e "${DIM}  安装过程约 5-15 分钟 (取决于网速和是否已有部分依赖)${NC}"
echo -e "${DIM}  安装过程中可能需要输入 Mac 密码${NC}"
echo ""
echo -e "  按 ${BOLD}回车${NC} 开始安装，或 ${BOLD}Ctrl+C${NC} 取消..."
read -r

# ──────────────────────────────────────────────────────────────
# 操作系统检查
# ──────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    fail "本安装器仅支持 macOS。"
    exit 1
fi

ARCH="$(uname -m)"
MACOS_VER="$(sw_vers -productVersion)"
info "检测到 macOS $MACOS_VER ($ARCH)"

# macOS 版本检查 (需要 12.0+)
MAJOR_VER=$(echo "$MACOS_VER" | cut -d. -f1)
if [[ "$MAJOR_VER" -lt 12 ]]; then
    fail "需要 macOS 12 (Monterey) 或更高版本，当前 $MACOS_VER"
    exit 1
fi

# ──────────────────────────────────────────────────────────────
# 1. Xcode Command Line Tools
# ──────────────────────────────────────────────────────────────
step 1 "Xcode Command Line Tools"

if xcode-select -p &>/dev/null; then
    success "已安装"
else
    info "正在安装 Xcode CLT..."
    info "如果弹出安装窗口，请点击「安装」并等待完成"
    xcode-select --install 2>/dev/null || true
    echo ""
    echo -e "  ${YELLOW}安装窗口关闭后，按回车继续...${NC}"
    read -r
    if ! xcode-select -p &>/dev/null; then
        fail "Xcode CLT 安装未完成"
        echo "  请手动运行: xcode-select --install"
        echo "  安装完成后重新双击本安装器"
        echo ""; read -rp "按回车关闭..."
        exit 1
    fi
    success "安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 2. Homebrew
# ──────────────────────────────────────────────────────────────
step 2 "Homebrew (macOS 包管理器)"

if [[ "$ARCH" == "arm64" ]]; then
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PREFIX="/usr/local"
fi

export PATH="$BREW_PREFIX/bin:$PATH"

if command -v brew &>/dev/null; then
    success "已安装 ($(brew --version | head -1))"
elif [[ -x "$BREW_PREFIX/bin/brew" ]]; then
    eval "$($BREW_PREFIX/bin/brew shellenv)"
    success "已安装（已修正 PATH）"
else
    info "正在安装 Homebrew（可能需要输入 Mac 密码）..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$($BREW_PREFIX/bin/brew shellenv)"
    success "安装完成"
fi

# 确保 brew 在后续命令可用
eval "$($BREW_PREFIX/bin/brew shellenv)" 2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# 3. Python 3.10+
# ──────────────────────────────────────────────────────────────
step 3 "Python ≥ $MIN_PYTHON"

version_gte() {
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

PYTHON_CMD=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 | awk '{print $2}')
        if version_gte "$ver" "$MIN_PYTHON"; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [[ -n "$PYTHON_CMD" ]]; then
    success "已安装 $($PYTHON_CMD --version 2>&1)"
else
    info "正在安装 Python 3.12..."
    brew install python@3.12
    PYTHON_CMD="$(brew --prefix python@3.12)/bin/python3.12"
    [[ -x "$PYTHON_CMD" ]] || PYTHON_CMD="python3.12"
    success "$($PYTHON_CMD --version 2>&1) 安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 4. 系统依赖 (PDF 渲染)
# ──────────────────────────────────────────────────────────────
step 4 "PDF 渲染依赖 (pango/cairo)"

BREW_DEPS=(pango cairo glib gdk-pixbuf libffi)
MISSING=()
for dep in "${BREW_DEPS[@]}"; do
    brew list "$dep" &>/dev/null || MISSING+=("$dep")
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
    success "已就绪"
else
    info "安装 ${MISSING[*]}..."
    brew install "${MISSING[@]}"
    success "安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 5. VC Research 主程序
# ──────────────────────────────────────────────────────────────
step 5 "VC Research 主程序"

REPO_URL="https://github.com/xinmao2030/vc-research.git"

if [[ -n "$SOURCE_DIR" && -d "$SOURCE_DIR/src/vc_research" ]]; then
    # 从 DMG / 本地源码安装
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "已有安装，更新中..."
        # 保留已有 git 仓库，只拷贝源码
        rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
              "$SOURCE_DIR/" "$INSTALL_DIR/"
        success "更新完成（从本地源码）"
    else
        info "从安装包复制源码..."
        mkdir -p "$INSTALL_DIR"
        rsync -a --exclude='__pycache__' "$SOURCE_DIR/" "$INSTALL_DIR/"
        # 初始化 git 供后续更新
        cd "$INSTALL_DIR" && git init -q && git add -A && git commit -q -m "initial install" 2>/dev/null || true
        success "安装完成（从本地源码）"
    fi
else
    # 在线克隆
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "已有安装，拉取最新代码..."
        git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || warn "git pull 跳过（有本地修改）"
        success "已是最新"
    else
        [[ -d "$INSTALL_DIR" ]] && rm -rf "$INSTALL_DIR"
        info "从 GitHub 克隆..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        success "克隆完成"
    fi
fi

# ──────────────────────────────────────────────────────────────
# 6. Python 虚拟环境 + 依赖
# ──────────────────────────────────────────────────────────────
step 6 "Python 虚拟环境 + 依赖安装"

if [[ ! -d "$VENV_DIR" ]]; then
    info "创建虚拟环境..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

info "升级 pip..."
pip install --upgrade pip --quiet 2>/dev/null

info "安装 vc-research..."
pip install -e "$INSTALL_DIR" --quiet 2>&1 | grep -v "already satisfied" || true

if [[ -x "$VENV_DIR/bin/vc-research" ]]; then
    success "vc-research 命令就绪"
else
    fail "安装失败，请检查错误信息"
    echo ""; read -rp "按回车关闭..."
    exit 1
fi

# 写入快捷激活脚本
cat > "$INSTALL_DIR/activate.sh" << 'ACTIVATE_INNER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
echo "✓ vc-research 环境已激活。输入 vc-research --help 查看帮助。"
ACTIVATE_INNER
chmod +x "$INSTALL_DIR/activate.sh"

# ──────────────────────────────────────────────────────────────
# 7. Ollama + AI 模型
# ──────────────────────────────────────────────────────────────
step 7 "Ollama + $OLLAMA_MODEL AI 模型"

echo ""
info "Ollama 是本地 AI 引擎，用于分析任意企业（不仅限于标杆案例）"
info "模型大小约 5GB，下载后完全离线运行"
echo ""

OLLAMA_INSTALLED=false

if command -v ollama &>/dev/null; then
    success "Ollama 已安装"
    OLLAMA_INSTALLED=true
else
    info "正在安装 Ollama..."
    brew install ollama
    success "Ollama 安装完成"
    OLLAMA_INSTALLED=true
fi

if $OLLAMA_INSTALLED; then
    # 启动 Ollama 服务
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        info "启动 Ollama 服务..."
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        # 等待服务就绪
        for i in $(seq 1 15); do
            if curl -s http://localhost:11434/api/tags &>/dev/null; then
                break
            fi
            sleep 1
        done
    fi

    # 拉取模型
    if ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
        success "$OLLAMA_MODEL 模型已就绪"
    else
        info "正在下载 $OLLAMA_MODEL 模型（约 5GB）..."
        info "首次下载需要一些时间，请耐心等待..."
        echo ""
        ollama pull "$OLLAMA_MODEL"
        echo ""
        success "$OLLAMA_MODEL 模型下载完成"
    fi

    # 预热模型（减少首次使用时的冷启动时间）
    info "预热模型（约 10 秒）..."
    curl -s http://localhost:11434/api/generate \
        -d "{\"model\":\"$OLLAMA_MODEL\",\"prompt\":\"hi\",\"stream\":false}" \
        -o /dev/null --max-time 30 2>/dev/null || true
    success "模型预热完成"
fi

# ──────────────────────────────────────────────────────────────
# 配置 Shell 环境（写入 ~/.zshrc）
# ──────────────────────────────────────────────────────────────
echo ""
info "配置 Shell 快捷方式..."

ZSHRC="$HOME/.zshrc"
MARKER="# vc-research"

if ! grep -q "$MARKER" "$ZSHRC" 2>/dev/null; then
    cat >> "$ZSHRC" << SHELL_EOF

$MARKER
alias vcr='source $INSTALL_DIR/activate.sh && vc-research'
alias vcr-dashboard='source $INSTALL_DIR/activate.sh && python $INSTALL_DIR/web/dashboard.py'
SHELL_EOF
    success "已添加快捷命令到 ~/.zshrc: vcr / vcr-dashboard"
else
    success "快捷命令已存在"
fi

# ──────────────────────────────────────────────────────────────
# 验证安装
# ──────────────────────────────────────────────────────────────
echo ""
info "验证安装..."
"$VENV_DIR/bin/vc-research" analyze "影石创新" -o /tmp/vc_test_report.md 2>/dev/null
if [[ -f /tmp/vc_test_report.md ]] && [[ -s /tmp/vc_test_report.md ]]; then
    success "验证通过 — 研报生成成功"
    rm -f /tmp/vc_test_report.md
else
    warn "验证未通过，但不影响安装完成。请手动测试。"
fi

# ──────────────────────────────────────────────────────────────
# 完成
# ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}"
cat << 'DONE'
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║         ✅  VC Research 安装完成！                   ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝
DONE
echo -e "${NC}"

echo -e "  ${BOLD}使用方法:${NC}"
echo ""
echo -e "  ${CYAN}# 方式 1: 用快捷命令（重新打开终端后生效）${NC}"
echo -e "  vcr analyze \"影石创新\"              # 分析标杆企业"
echo -e "  vcr analyze \"字节跳动\" --live       # 分析任意企业"
echo -e "  vcr list-examples                    # 查看标杆案例列表"
echo -e "  vcr-dashboard                        # 打开 Web 界面"
echo ""
echo -e "  ${CYAN}# 方式 2: 手动激活${NC}"
echo -e "  source ~/vc-research/activate.sh"
echo -e "  vc-research analyze \"银诺医药\" --pdf"
echo ""
echo -e "  ${BOLD}6 家内置标杆企业（秒出报告,无需联网）:${NC}"
echo -e "  影石创新 | 澜起科技 | 银诺医药 | 比贝特医药 | 汉朔科技 | 强一股份"
echo ""
echo -e "  ${BOLD}任意企业（需 Ollama 运行,首次约 2 分钟）:${NC}"
echo -e "  vcr analyze \"企业名\" --live"
echo ""
echo -e "  ${DIM}Ollama 会在 Mac 启动时自动运行。如需手动启动: ollama serve${NC}"
echo ""
read -rp "  按回车关闭本窗口..."
