#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# VC Research 一键安装脚本 (macOS)
# 用法: curl -fsSL <url>/install.sh | bash
#   或: bash install.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── 工具函数 ──
info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✗${NC}  $*"; }
step()    { echo -e "\n${CYAN}${BOLD}[$1/$TOTAL_STEPS] $2${NC}"; }

TOTAL_STEPS=7
INSTALL_DIR="${VC_RESEARCH_DIR:-$HOME/vc-research}"
VENV_DIR="$INSTALL_DIR/.venv"
MIN_PYTHON="3.10"

# ── Banner ──
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       VC Research — 创投企业投资分析系统 安装程序       ║"
echo "║   输入企业名 → 输出 7 层结构化投研报告 (Markdown/PDF)  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ──────────────────────────────────────────────────────────────
# 0. 操作系统检查
# ──────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    error "本脚本仅支持 macOS。Linux 请参考 README.md 手动安装。"
    exit 1
fi

ARCH="$(uname -m)"
info "检测到 macOS $(sw_vers -productVersion) ($ARCH)"

# ──────────────────────────────────────────────────────────────
# 1. Xcode Command Line Tools
# ──────────────────────────────────────────────────────────────
step 1 "检查 Xcode Command Line Tools"

if xcode-select -p &>/dev/null; then
    success "Xcode CLT 已安装"
else
    info "正在安装 Xcode Command Line Tools（弹窗请点击"安装"）..."
    xcode-select --install 2>/dev/null || true
    # 等待安装完成
    echo -e "${YELLOW}    等待 Xcode CLT 安装完成...按回车继续（安装完弹窗后）${NC}"
    read -r
    if ! xcode-select -p &>/dev/null; then
        error "Xcode CLT 安装未完成，请手动运行: xcode-select --install"
        exit 1
    fi
    success "Xcode CLT 安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 2. Homebrew
# ──────────────────────────────────────────────────────────────
step 2 "检查 Homebrew"

# Homebrew 可能在不同位置
if [[ "$ARCH" == "arm64" ]]; then
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PREFIX="/usr/local"
fi

if command -v brew &>/dev/null; then
    success "Homebrew 已安装 ($(brew --version | head -1))"
elif [[ -x "$BREW_PREFIX/bin/brew" ]]; then
    # Homebrew 存在但不在 PATH
    eval "$($BREW_PREFIX/bin/brew shellenv)"
    success "Homebrew 已安装（已加入当前 PATH）"
    warn "建议将以下行加入 ~/.zshrc:"
    echo "    eval \"\$($BREW_PREFIX/bin/brew shellenv)\""
else
    info "正在安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$($BREW_PREFIX/bin/brew shellenv)"
    success "Homebrew 安装完成"
    warn "请将以下行加入 ~/.zshrc 以便后续终端使用:"
    echo "    eval \"\$($BREW_PREFIX/bin/brew shellenv)\""
fi

# ──────────────────────────────────────────────────────────────
# 3. Python 3.10+
# ──────────────────────────────────────────────────────────────
step 3 "检查 Python ≥ $MIN_PYTHON"

# 版本比较函数
version_gte() {
    # $1 >= $2 ?
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

PYTHON_CMD=""

# 优先查找 brew 安装的 python3
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
    PYTHON_VER=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
    success "Python $PYTHON_VER ($PYTHON_CMD)"
else
    info "未找到 Python ≥ $MIN_PYTHON，正在通过 Homebrew 安装 python@3.12..."
    brew install python@3.12
    PYTHON_CMD="$(brew --prefix python@3.12)/bin/python3.12"
    if [[ ! -x "$PYTHON_CMD" ]]; then
        PYTHON_CMD="python3.12"
    fi
    PYTHON_VER=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
    success "Python $PYTHON_VER 安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 4. 系统依赖 (PDF 渲染可选)
# ──────────────────────────────────────────────────────────────
step 4 "安装系统依赖 (pango/cairo — PDF 渲染用)"

BREW_DEPS=(pango cairo glib gdk-pixbuf libffi)
MISSING_DEPS=()
for dep in "${BREW_DEPS[@]}"; do
    if ! brew list "$dep" &>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [[ ${#MISSING_DEPS[@]} -eq 0 ]]; then
    success "系统依赖已就绪 (${BREW_DEPS[*]})"
else
    info "正在安装: ${MISSING_DEPS[*]}"
    brew install "${MISSING_DEPS[@]}"
    success "系统依赖安装完成"
fi

# ──────────────────────────────────────────────────────────────
# 5. 克隆/更新项目
# ──────────────────────────────────────────────────────────────
step 5 "获取 VC Research 源码"

REPO_URL="https://github.com/xinmao2030/vc-research.git"

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "已有本地仓库，正在拉取最新代码..."
    git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || {
        warn "git pull 失败（可能有本地修改），跳过更新"
    }
    success "代码已是最新"
else
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "$INSTALL_DIR 已存在但不是 git 仓库"
        echo -e "    ${YELLOW}是否删除并重新克隆? [y/N]${NC} "
        read -r confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            error "请手动处理 $INSTALL_DIR 后重试"
            exit 1
        fi
    fi
    info "正在克隆到 $INSTALL_DIR ..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    success "源码克隆完成"
fi

# ──────────────────────────────────────────────────────────────
# 6. Python 虚拟环境 + 依赖安装
# ──────────────────────────────────────────────────────────────
step 6 "创建虚拟环境并安装依赖"

if [[ -d "$VENV_DIR" ]]; then
    info "虚拟环境已存在，更新依赖..."
else
    info "创建虚拟环境: $VENV_DIR"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 升级 pip (避免旧版 pip 问题)
info "升级 pip..."
pip install --upgrade pip --quiet 2>/dev/null

# 安装项目 (editable mode)
info "安装 vc-research 及其依赖..."
pip install -e "$INSTALL_DIR" --quiet 2>&1 | grep -v "already satisfied" || true

# 验证安装
if command -v vc-research &>/dev/null; then
    success "vc-research 命令已可用"
else
    # 可能需要用完整路径
    if [[ -x "$VENV_DIR/bin/vc-research" ]]; then
        success "vc-research 安装在 $VENV_DIR/bin/vc-research"
    else
        error "vc-research 安装失败，请检查错误日志"
        exit 1
    fi
fi

# ──────────────────────────────────────────────────────────────
# 7. Ollama + Qwen3 模型 (Live 模式)
# ──────────────────────────────────────────────────────────────
step 7 "安装 Ollama + Qwen3 模型 (任意企业分析)"

OLLAMA_INSTALLED=false

if command -v ollama &>/dev/null; then
    success "Ollama 已安装 ($(ollama --version 2>&1 | head -1))"
    OLLAMA_INSTALLED=true
else
    echo ""
    info "Ollama 是本地 AI 推理引擎，用于分析 fixtures 之外的任意企业。"
    echo -e "    ${YELLOW}是否安装 Ollama? (推荐，约 500MB) [Y/n]${NC} "
    read -r install_ollama
    if [[ ! "$install_ollama" =~ ^[Nn]$ ]]; then
        info "正在安装 Ollama..."
        brew install ollama
        success "Ollama 安装完成"
        OLLAMA_INSTALLED=true
    else
        warn "跳过 Ollama 安装。仅可分析 6 家标杆案例���不支持搜索任意企业。"
    fi
fi

if $OLLAMA_INSTALLED; then
    # 确保 Ollama 服务运行
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        info "启动 Ollama 服务..."
        ollama serve &>/dev/null &
        sleep 3
    fi

    # 检查 qwen3:8b 模型
    if ollama list 2>/dev/null | grep -q "qwen3:8b"; then
        success "qwen3:8b 模型已就绪"
    else
        echo ""
        info "需要下载 qwen3:8b 模型（约 5GB，首次下载较慢）"
        echo -e "    ${YELLOW}是否现在下载? [Y/n]${NC} "
        read -r pull_model
        if [[ ! "$pull_model" =~ ^[Nn]$ ]]; then
            info "正在拉取 qwen3:8b（请耐心等待）..."
            ollama pull qwen3:8b
            success "qwen3:8b 模型下载完成"
        else
            warn "跳过模型下载。使用 --live 模式前请手动运行: ollama pull qwen3:8b"
        fi
    fi
fi

# ──────────────────────────────────────────────────────────────
# 完成！
# ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║              ✅ VC Research 安装完成！                   ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}📖 快速开始:${NC}"
echo ""
echo -e "  ${CYAN}# 1. 激活环境${NC}"
echo -e "  source $VENV_DIR/bin/activate"
echo ""
echo -e "  ${CYAN}# 2. 分析标杆企业 (无需网络/Ollama)${NC}"
echo -e "  vc-research analyze \"影石创新\" -o report.md"
echo -e "  vc-research list-examples"
echo ""
echo -e "  ${CYAN}# 3. 搜索任意企业 (需要 Ollama 运行)${NC}"
echo -e "  vc-research analyze \"字节跳动\" --live -o report.md"
echo ""
echo -e "  ${CYAN}# 4. 打开 Web Dashboard (浏览器自动打开)${NC}"
echo -e "  python $INSTALL_DIR/web/dashboard.py"
echo ""
echo -e "  ${CYAN}# 5. 生成 PDF 研报${NC}"
echo -e "  vc-research analyze \"银诺医药\" --pdf -o report.pdf"
echo ""
echo -e "${BOLD}💡 提示:${NC}"
echo -e "  • 每次使用前先激活环境: ${CYAN}source $VENV_DIR/bin/activate${NC}"
echo -e "  • 或添加快捷��式到 ~/.zshrc:"
echo -e "    ${CYAN}alias vcr='source $VENV_DIR/bin/activate && vc-research'${NC}"
echo ""

# 写入快捷激活脚本
cat > "$INSTALL_DIR/activate.sh" << 'ACTIVATE_EOF'
#!/usr/bin/env bash
# 快捷激活 vc-research 环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
echo "✓ vc-research 环境已激活。输入 vc-research --help 查看帮助。"
ACTIVATE_EOF
chmod +x "$INSTALL_DIR/activate.sh"

echo -e "  • 快捷激活: ${CYAN}source $INSTALL_DIR/activate.sh${NC}"
echo ""
