"""最小 Dashboard — 浏览 examples/reports/ 下的研报.

Phase 4 Web Dashboard 的 MVP 起点: 纯 Python stdlib + markdown,
无需 Next.js / 数据库,启动即可用。

Run:
    python web/dashboard.py                    # localhost:8765
    python web/dashboard.py --port 9000
"""

from __future__ import annotations

import argparse
import html
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

import markdown

REPORTS_DIR = Path(__file__).resolve().parent.parent / "examples" / "reports"

STYLE = """
<style>
  :root { color-scheme: light dark; }
  body {
    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    max-width: 960px; margin: 2em auto; padding: 0 1.5em;
    line-height: 1.7; color: #222;
  }
  nav { padding: 1em 0; border-bottom: 1px solid #e1e4e8; margin-bottom: 2em; }
  nav a { margin-right: 1em; color: #0366d6; text-decoration: none; font-weight: 500; }
  nav a:hover { text-decoration: underline; }
  .card {
    border: 1px solid #e1e4e8; border-radius: 10px;
    padding: 1.2em 1.5em; margin: 1em 0;
    transition: all .15s;
  }
  .card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.08); transform: translateY(-2px); }
  .card a { color: #0366d6; font-size: 1.15em; font-weight: 600; text-decoration: none; }
  .card .meta { color: #6a737d; font-size: .9em; margin-top: .3em; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #f6f8fa; font-weight: 600; }
  blockquote {
    border-left: 4px solid #0366d6; padding: .5em 1em;
    color: #555; background: #f6f8fa; margin: 1em 0;
  }
  h1, h2, h3 { color: #24292e; }
  h1 { border-bottom: 2px solid #0366d6; padding-bottom: .3em; }
  h2 { border-bottom: 1px solid #eaecef; padding-bottom: .3em; margin-top: 2em; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: .9em; }
  .disclaimer {
    background: #fff8c5; border: 1px solid #d4b808; color: #735c0f;
    padding: .8em 1em; border-radius: 8px; margin: 1.5em 0;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #f0f6fc; }
    .card { border-color: #30363d; }
    nav, th { background: transparent; }
    th { background: #161b22; }
    blockquote { background: #161b22; color: #8b949e; }
    code { background: #161b22; }
  }
</style>
"""

NAV = """
<nav>
  <a href="/">🏠 首页</a>
  <a href="/about">ℹ️ 关于</a>
  <a href="https://github.com/" target="_blank">📦 源码</a>
</nav>
"""


def _page(title: str, body: str) -> bytes:
    html_text = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · VC Research</title>
{STYLE}
</head><body>{NAV}{body}</body></html>"""
    return html_text.encode("utf-8")


def _index() -> bytes:
    reports = sorted(REPORTS_DIR.glob("*.md"))
    cards = "\n".join(
        f"""<div class="card">
          <a href="/report/{html.escape(r.stem)}">📊 {html.escape(r.stem)}</a>
          <div class="meta">{r.stat().st_size // 1024} KB · 最后修改 {_mtime(r)}</div>
        </div>"""
        for r in reports
    ) or "<p>暂无研报。运行 <code>vc-research analyze &quot;字节跳动&quot;</code> 生成第一份。</p>"

    body = f"""
    <h1>📊 VC Research Dashboard</h1>
    <p>创投企业投资分析系统 · 输入企业名 → 输出结构化研报</p>
    <div class="disclaimer">⚠️ 本系统所有研报仅供学习研究,<b>不构成投资建议</b>。数据可能过时,决策前请独立核实。</div>
    <h2>🗂️ 研报列表 ({len(reports)})</h2>
    {cards}
    """
    return _page("首页", body)


def _about() -> bytes:
    body = """
    <h1>ℹ️ 关于 VC Research</h1>
    <p>创投企业投资分析系统 — 为零基础投资者打造的 AI 投研助手。</p>
    <h2>7 层分析框架</h2>
    <ol>
      <li>🏢 企业画像</li>
      <li>💰 融资轨迹</li>
      <li>🎯 投资依据 (Thesis)</li>
      <li>🌊 产业趋势</li>
      <li>💎 估值分析</li>
      <li>⚠️ 风险矩阵</li>
      <li>🎯 投资建议</li>
    </ol>
    <h2>版本</h2>
    <p>v0.1.0 · Phase 1 骨架</p>
    """
    return _page("关于", body)


def _report(name: str) -> tuple[bytes, int]:
    path = REPORTS_DIR / f"{name}.md"
    if not path.exists():
        return _page("404", "<h1>研报不存在</h1>"), 404
    md_text = path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return _page(name, html_body), 200


def _mtime(p: Path) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = unquote(self.path)
        if path == "/" or path == "":
            body, status = _index(), 200
        elif path == "/about":
            body, status = _about(), 200
        elif path.startswith("/report/"):
            name = path[len("/report/") :]
            body, status = _report(name)
        else:
            body, status = _page("404", "<h1>404</h1>"), 404

        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://localhost:{args.port}"
    print(f"🚀 VC Research Dashboard → {url}")
    print(f"📁 Reports dir: {REPORTS_DIR}")

    if not args.no_browser:
        webbrowser.open(url)

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 bye")


if __name__ == "__main__":
    main()
