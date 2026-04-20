#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# 生成 "VC Research.app" macOS 应用 — 双击打开 Dashboard
# 由安装器自动调用，也可手动运行: bash create_app.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="${1:-$HOME/vc-research}"
APP_DIR="$HOME/Applications/VC Research.app"

# 也放一份到桌面
DESKTOP_APP="$HOME/Desktop/VC Research.app"

# ── 构建 .app 目录结构 ──
create_app() {
    local target="$1"
    rm -rf "$target"
    mkdir -p "$target/Contents/MacOS"
    mkdir -p "$target/Contents/Resources"

    # ── 启动脚本 ──
    cat > "$target/Contents/MacOS/launch" << LAUNCH_EOF
#!/usr/bin/env bash
# VC Research Dashboard Launcher
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"

INSTALL_DIR="$INSTALL_DIR"
VENV_DIR="\$INSTALL_DIR/.venv"
LOG_FILE="/tmp/vc-research-dashboard.log"

# 确保 Ollama 运行
if command -v ollama &>/dev/null; then
    if ! curl -s http://localhost:11434/api/tags &>/dev/null 2>&1; then
        ollama serve &>/dev/null &
        sleep 2
    fi
fi

# 激活虚拟环境并启动 Dashboard
if [[ -f "\$VENV_DIR/bin/activate" ]]; then
    source "\$VENV_DIR/bin/activate"
    python "\$INSTALL_DIR/web/dashboard.py" > "\$LOG_FILE" 2>&1 &
    DASHBOARD_PID=\$!

    # 等待服务启动
    for i in \$(seq 1 10); do
        if curl -s http://localhost:8765 &>/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done

    # 打开浏览器
    open "http://localhost:8765"

    # 显示通知
    osascript -e 'display notification "Dashboard 已在浏览器中打开\nhttp://localhost:8765" with title "VC Research" subtitle "创投分析系统已启动"' 2>/dev/null || true

    # 等待 Dashboard 进程结束
    wait \$DASHBOARD_PID 2>/dev/null || true
else
    osascript -e 'display alert "VC Research 未安装" message "请先运行安装程序:\n双击 安装 VC Research.command" as critical' 2>/dev/null
fi
LAUNCH_EOF
    chmod +x "$target/Contents/MacOS/launch"

    # ── Info.plist ──
    cat > "$target/Contents/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIdentifier</key>
    <string>com.xinmao.vc-research</string>
    <key>CFBundleName</key>
    <string>VC Research</string>
    <key>CFBundleDisplayName</key>
    <string>VC Research</string>
    <key>CFBundleVersion</key>
    <string>0.1.16</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.16</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
    <key>NSHumanReadableCopyright</key>
    <string>VC Research - 创投企业投资分析系统</string>
</dict>
</plist>
PLIST_EOF

    # ── 生成应用图标 (使用 macOS 内置工具生成简单图标) ──
    # 用 Python 生成一个简单的 PNG 图标，再转成 icns
    local ICON_DIR="/tmp/vc-research-icon.iconset"
    rm -rf "$ICON_DIR"
    mkdir -p "$ICON_DIR"

    # 尝试用 Python + PIL 生成图标
    python3 - "$ICON_DIR" << 'ICON_PYTHON' 2>/dev/null || true
import sys, os
try:
    from PIL import Image, ImageDraw, ImageFont
    iconset = sys.argv[1]
    sizes = [16,32,64,128,256,512]
    for s in sizes:
        img = Image.new('RGBA', (s, s), (30, 58, 138, 255))
        draw = ImageDraw.Draw(img)
        # 白色圆角矩形背景
        margin = s // 8
        draw.rounded_rectangle([margin, margin, s-margin, s-margin],
                               radius=s//6, fill=(255,255,255,240))
        # 绘制 "VC" 文字
        font_size = s // 3
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), "VC", font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text(((s-tw)//2, (s-th)//2 - s//10), "VC", fill=(30,58,138,255), font=font)
        # 小号 R
        small_size = s // 5
        try:
            sfont = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", small_size)
        except:
            sfont = font
        draw.text(((s-small_size//2)//2, s//2 + s//10), "R", fill=(59,130,246,255), font=sfont)
        img.save(os.path.join(iconset, f"icon_{s}x{s}.png"))
        img2 = img.resize((s*2, s*2), Image.LANCZOS)
        img2.save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
    print("icon generated")
except ImportError:
    print("PIL not available, skip icon")
ICON_PYTHON

    # 转换为 icns
    if [[ -f "$ICON_DIR/icon_256x256.png" ]]; then
        iconutil -c icns "$ICON_DIR" -o "$target/Contents/Resources/AppIcon.icns" 2>/dev/null || true
    fi
    rm -rf "$ICON_DIR"
}

# ── 创建应用 ──
mkdir -p "$HOME/Applications"
create_app "$APP_DIR"
create_app "$DESKTOP_APP"

echo "✓ VC Research.app 已创建:"
echo "  • $APP_DIR"
echo "  • $DESKTOP_APP"
echo "  双击即可打开 Dashboard (浏览器自动跳转)"
