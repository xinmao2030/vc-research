#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# 生成 "VC Research.app" — 原生 AppleScript 应用
# 双击打开 Dashboard (自动启动 Ollama + 浏览器)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="${1:-$HOME/vc-research}"
APP_NAME="VC Research"
DESKTOP_APP="$HOME/Desktop/${APP_NAME}.app"
TMPSCRIPT="/tmp/vc-research-app.applescript"

# ── 写 AppleScript 到临时文件 ──
cat > "$TMPSCRIPT" << APPLESCRIPT_DONE
on run
    set installDir to "${INSTALL_DIR}"
    set venvPython to installDir & "/.venv/bin/python"
    set dashboardPy to installDir & "/web/dashboard.py"
    set logFile to "/tmp/vc-research-dashboard.log"
    set brewPath to "/opt/homebrew/bin:/usr/local/bin"

    -- 杀掉旧 Dashboard 进程(确保加载最新代码)
    try
        do shell script "lsof -ti:8801 2>/dev/null | xargs kill 2>/dev/null; true"
        delay 1
    end try

    -- 启动 Ollama (如果没在运行)
    try
        do shell script "export PATH=" & quoted form of brewPath & ":\$PATH; curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1 || (ollama serve >/dev/null 2>&1 &); sleep 3; true"
    end try

    -- 启动 Dashboard
    try
        do shell script quoted form of venvPython & " " & quoted form of dashboardPy & " > " & quoted form of logFile & " 2>&1 &"
    on error errMsg
        display alert "VC Research" message "Dashboard failed: " & errMsg as critical
        return
    end try

    -- 等待就绪
    set dashReady to false
    repeat 20 times
        delay 0.5
        try
            set chk to do shell script "curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://localhost:8801 2>/dev/null || echo 000"
            if chk is "200" then
                set dashReady to true
                exit repeat
            end if
        end try
    end repeat

    open location "http://localhost:8801"

    if dashReady then
        display notification "Dashboard running at localhost:8801" with title "VC Research"
    end if
end run
APPLESCRIPT_DONE

# ── 编译为 .app ──
rm -rf "$DESKTOP_APP"
osacompile -o "$DESKTOP_APP" "$TMPSCRIPT"
rm -f "$TMPSCRIPT"

# ── 修改 Info.plist ──
PLIST="$DESKTOP_APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName '${APP_NAME}'" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string '${APP_NAME}'" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier 'com.xinmao.vc-research'" "$PLIST" 2>/dev/null || true

# ── 生成图标 ──
ICON_DIR="/tmp/vc-research-icon.iconset"
rm -rf "$ICON_DIR"
mkdir -p "$ICON_DIR"

"$INSTALL_DIR/.venv/bin/python" - "$ICON_DIR" << 'ICON_PY' 2>/dev/null || true
import sys, os, struct, zlib
iconset = sys.argv[1]
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def make_solid_png(w, h, r, g, b):
    raw = b''
    for _ in range(h):
        raw += b'\x00' + bytes([r, g, b, 255]) * w
    compressed = zlib.compress(raw)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

for s in [16, 32, 128, 256, 512]:
    if HAS_PIL:
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        m = max(s // 10, 1)
        draw.rounded_rectangle([m, m, s - m, s - m], radius=s // 5, fill=(37, 99, 235, 255))
        fs = s * 4 // 10
        try: font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", fs)
        except: font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "VCR", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((s - tw) // 2, (s - th) // 2 - s // 12), "VCR", fill=(255, 255, 255, 255), font=font)
        fs2 = s // 7
        try: font2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", fs2)
        except: font2 = font
        bbox2 = draw.textbbox((0, 0), "Research", font=font2)
        draw.text(((s - bbox2[2] + bbox2[0]) // 2, (s - th) // 2 + th - s // 16), "Research", fill=(191, 219, 254, 255), font=font2)
        img.save(os.path.join(iconset, f"icon_{s}x{s}.png"))
        img.resize((s * 2, s * 2), Image.LANCZOS).save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
    else:
        for scale, suffix in [(1, ""), (2, "@2x")]:
            sz = s * scale
            with open(os.path.join(iconset, f"icon_{s}x{s}{suffix}.png"), 'wb') as f:
                f.write(make_solid_png(sz, sz, 37, 99, 235))
print("ok")
ICON_PY

if ls "$ICON_DIR"/icon_*.png &>/dev/null; then
    iconutil -c icns "$ICON_DIR" -o "$DESKTOP_APP/Contents/Resources/applet.icns" 2>/dev/null && \
        echo "✓ 图标已生成" || true
fi
rm -rf "$ICON_DIR"

# ── 重新签名（PlistBuddy/图标修改会破坏 osacompile 的 adhoc 签名）──
codesign --force --sign - "$DESKTOP_APP" 2>/dev/null || true

# ── 移除 macOS 隔离标记（防止"已损坏"弹窗）──
xattr -cr "$DESKTOP_APP" 2>/dev/null || true

# ── 复制到 ~/Applications ──
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/${APP_NAME}.app"
cp -R "$DESKTOP_APP" "$HOME/Applications/${APP_NAME}.app"
codesign --force --sign - "$HOME/Applications/${APP_NAME}.app" 2>/dev/null || true
xattr -cr "$HOME/Applications/${APP_NAME}.app" 2>/dev/null || true

echo "✓ ${APP_NAME}.app 已创建:"
echo "  • $DESKTOP_APP"
echo "  • $HOME/Applications/${APP_NAME}.app"
