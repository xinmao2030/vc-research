#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# 一键修复并启动 VC Research Dashboard
# 双击即可: 杀旧进程 → 清缓存 → 重启 Ollama → 启动 Dashboard
# ──────────────────────────────────────────────────────────────
xattr -d com.apple.quarantine "$0" 2>/dev/null || true

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}ℹ${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
fail()    { echo -e "${RED}✗${NC}  $*"; }

INSTALL_DIR="$HOME/vc-research"
VENV_PY="$INSTALL_DIR/.venv/bin/python"

echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  VC Research 一键修复并启动${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""

# ── 1. 杀掉旧 Dashboard ──
info "停止旧 Dashboard..."
lsof -ti:8801 2>/dev/null | xargs kill 2>/dev/null
lsof -ti:8800 2>/dev/null | xargs kill 2>/dev/null
sleep 1
success "旧进程已清理"

# ── 2. 清理 LLM 缓存 (避免旧的错误数据) ──
info "清理 LLM 缓存..."
rm -rf "$HOME/.vc-research/llm_cache"/*
success "缓存已清理"

# ── 3. 检查安装 ──
if [[ ! -f "$VENV_PY" ]]; then
    fail "未找到 Python 环境: $VENV_PY"
    fail "请先双击「完整安装(首次).command」"
    echo ""
    read -n1 -rsp "按任意键退出..."
    exit 1
fi
success "Python 环境正常"

# ── 4. 检查 dashboard.py 版本 ──
if grep -q "_sanitize_llm_data" "$INSTALL_DIR/web/dashboard.py" 2>/dev/null; then
    success "Dashboard 代码已包含类型修复 (v10+)"
else
    fail "Dashboard 代码版本过旧，请先运行「快速安装」"
    echo ""
    read -n1 -rsp "按任意键退出..."
    exit 1
fi

if grep -q "_to_str" "$INSTALL_DIR/src/vc_research/modules/investment_thesis.py" 2>/dev/null; then
    success "分析模块已包含类型防御 (v10+)"
else
    fail "分析模块版本过旧，请先运行「快速安装」"
    echo ""
    read -n1 -rsp "按任意键退出..."
    exit 1
fi

# ── 5. 启动 Ollama ──
info "检查 Ollama..."
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    success "Ollama 已在运行"
else
    info "启动 Ollama..."
    ollama serve >/dev/null 2>&1 &
    sleep 3
    if curl -s --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
        success "Ollama 启动成功"
    else
        fail "Ollama 启动失败，请手动运行: ollama serve"
    fi
fi

# 检查模型
if ollama list 2>/dev/null | grep -q "qwen3"; then
    success "qwen3 模型已安装"
else
    fail "未找到 qwen3 模型，请运行: ollama pull qwen3:8b"
    echo ""
    read -n1 -rsp "按任意键退出..."
    exit 1
fi

# ── 6. 启动 Dashboard ──
info "启动 Dashboard..."
cd "$INSTALL_DIR"
"$VENV_PY" web/dashboard.py --port 8801 --no-browser > /tmp/vc-research-dashboard.log 2>&1 &
DASH_PID=$!

# 等待启动
READY=false
for i in $(seq 1 15); do
    sleep 1
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8801 2>/dev/null | grep -q "200"; then
        READY=true
        break
    fi
    echo -ne "\r  等待启动... ${i}s"
done
echo ""

if $READY; then
    success "Dashboard 启动成功！ PID=$DASH_PID"
    echo ""
    echo -e "${BOLD}打开浏览器...${NC}"
    open "http://localhost:8801"
    echo ""
    echo -e "  ${GREEN}✓${NC} 首页: ${CYAN}http://localhost:8801${NC}"
    echo -e "  ${GREEN}✓${NC} 搜索任意公司名即可生成研报"
    echo -e "  ${GREEN}✓${NC} 首次搜索需 1-2 分钟 (M1 芯片)"
    echo ""
    echo -e "  ${CYAN}关闭方式:${NC} 关闭此终端窗口即可"
    echo ""
    # 保持终端开启，显示日志
    tail -f /tmp/vc-research-dashboard.log 2>/dev/null
else
    fail "Dashboard 启动失败！"
    echo ""
    echo -e "${RED}错误日志:${NC}"
    cat /tmp/vc-research-dashboard.log 2>/dev/null | tail -30
    echo ""
    read -n1 -rsp "按任意键退出..."
fi
