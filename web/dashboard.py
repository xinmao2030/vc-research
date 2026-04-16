"""增强版 Dashboard — 从 fixtures 实时生成研报 + 术语 hover + 术语表页.

Run:
    python web/dashboard.py                    # localhost:8765
    python web/dashboard.py --port 9000
"""

from __future__ import annotations

import argparse
import html
import re
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

import markdown

from vc_research.data_sources import DataAggregator
from vc_research.data_sources.ollama_researcher import DEFAULT_CACHE_DIR as LLM_CACHE_DIR
from vc_research.modules import (
    analyze_funding,
    analyze_industry,
    analyze_profile,
    analyze_recommendation,
    analyze_risks,
    analyze_thesis,
    analyze_valuation,
)
from vc_research.modules.company_profile import InsufficientDataError
from vc_research.report import render_markdown
from vc_research.report.renderer import _sanitize_html
from vc_research.schema import VCReport

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "examples" / "fixtures"
DOCS_DIR = ROOT / "docs"


# ──────────────────────────── 术语 hover 字典 ────────────────────────────
# key: 匹配词(大小写不敏感),value: 悬停提示
GLOSSARY_HOVER: dict[str, str] = {
    "TAM": "Total Addressable Market — 理论最大市场(整个海洋)",
    "SAM": "Serviceable Addressable Market — 能游到的海域",
    "SOM": "Serviceable Obtainable Market — 3-5 年能抓到的鱼",
    "LTV": "客户生命周期价值 — 一个客户一辈子能赚多少",
    "CAC": "客户获取成本 — 买一个客户要花多少钱",
    "LTV/CAC": "健康比 ≥ 3;< 1 = 赔本赚吆喝",
    "ARR": "年化订阅收入 — 每年雷打不动的租金",
    "MAU": "月活跃用户",
    "DAU": "日活跃用户",
    "GMV": "交易总流水",
    "CAGR": "年复合增长率 — 利滚利增速",
    "P/ARR": "估值/ARR 倍数 — SaaS 常用",
    "护城河": "让对手难以复制的竞争壁垒(网络效应/规模/技术/品牌/切换成本)",
    "稀释": "融资后老股东持股比例变小(蛋糕切分)",
    "跑道": "现金够烧几个月(Runway)",
    "Runway": "现金 ÷ 月烧钱 = 还能撑几个月",
    "优先清算权": "破产/被收购时谁先拿本金(救生艇优先级)",
    "反稀释": "后续融资估值下降时早期投资人的保价险",
    "Pre-money": "融资前的估值",
    "Post-money": "Pre-money + 新融资额",
    "Pre-IPO": "IPO 前的最后一轮融资",
    "Series A": "A 轮 — 产品初验证后首轮机构融资",
    "Series B": "B 轮 — 商业模式验证,扩规模",
    "DCF": "现金流折现法 — 未来租金折回现在",
}

# 按长度降序排,优先匹配长词 (避免 LTV 误匹配到 LTV/CAC)
_GLOSSARY_KEYS = sorted(GLOSSARY_HOVER.keys(), key=len, reverse=True)
_TERM_RE = re.compile(
    "(" + "|".join(re.escape(k) for k in _GLOSSARY_KEYS) + ")",
    re.IGNORECASE,
)


_MERMAID_BLOCK_RE = re.compile(
    r'<div class="mermaid">.*?</div>', re.DOTALL
)


def _inject_tooltips(html_body: str) -> str:
    """把 glossary 里的术语包成 <abbr>,使用浏览器原生 tooltip.

    只替换普通文本内容,不碰 HTML 标签属性 (用简单分段策略避免 <abbr>
    内嵌或破坏标签结构).Mermaid 代码块预先抽出,避免 <abbr> 破坏图表源码。
    """
    # 先保护 mermaid 块
    saved: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        saved.append(m.group(0))
        return f"\x00MERMAID{len(saved) - 1}\x00"

    html_body = _MERMAID_BLOCK_RE.sub(_stash, html_body)

    # 分段: 标签 vs 文本
    parts = re.split(r"(<[^>]+>)", html_body)
    out: list[str] = []
    for p in parts:
        if p.startswith("<"):
            out.append(p)
            continue
        out.append(
            _TERM_RE.sub(
                lambda m: (
                    f'<abbr title="{html.escape(GLOSSARY_HOVER.get(m.group(0)) or GLOSSARY_HOVER.get(_canonical(m.group(0)), ""))}">'
                    f"{m.group(0)}</abbr>"
                ),
                p,
            )
        )
    html_body = "".join(out)

    # 还原 mermaid 块
    for idx, block in enumerate(saved):
        html_body = html_body.replace(f"\x00MERMAID{idx}\x00", block)
    return html_body


def _canonical(term: str) -> str:
    """大小写归一:找到 GLOSSARY_HOVER 里匹配的 key."""
    for k in _GLOSSARY_KEYS:
        if k.lower() == term.lower():
            return k
    return term


# ──────────────────────────── 样式 ────────────────────────────
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

  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1em; margin: 1em 0;
  }
  .card {
    border: 1px solid #e1e4e8; border-radius: 10px;
    padding: 1.2em 1.4em; transition: all .15s;
    background: #fff;
  }
  .card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.1); transform: translateY(-2px); }
  .card a.title { color: #0366d6; font-size: 1.15em; font-weight: 600; text-decoration: none; }
  .card .meta { color: #6a737d; font-size: .85em; margin-top: .4em; }
  .card .badges { margin-top: .6em; display: flex; gap: .4em; flex-wrap: wrap; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: .75em; font-weight: 500;
  }
  .badge.verdict-推荐 { background: #d1f4dd; color: #065f32; }
  .badge.verdict-强烈推荐 { background: #34d058; color: #fff; }
  .badge.verdict-观望 { background: #fff5b1; color: #735c0f; }
  .badge.verdict-回避 { background: #ffeef0; color: #86181d; }
  .badge.risk-low { background: #d1f4dd; color: #065f32; }
  .badge.risk-medium { background: #fff5b1; color: #735c0f; }
  .badge.risk-high { background: #ffdfb6; color: #b24c00; }
  .badge.risk-critical { background: #ffeef0; color: #86181d; }
  .badge.industry { background: #e1e4e8; color: #24292e; }

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
  abbr { cursor: help; text-decoration: underline dotted #0366d6; text-underline-offset: 2px; }
  .mermaid {
    background: #fafbfc; border: 1px solid #e1e4e8; border-radius: 8px;
    padding: 1em; margin: 1.5em 0; text-align: center;
    overflow-x: auto;
  }

  .disclaimer {
    background: #fff8c5; border: 1px solid #d4b808; color: #735c0f;
    padding: .8em 1em; border-radius: 8px; margin: 1.5em 0;
  }

  @media (prefers-color-scheme: dark) {
    body { background: #0d1117; color: #c9d1d9; }
    h1, h2, h3 { color: #f0f6fc; }
    .card { border-color: #30363d; background: #161b22; }
    nav, th { background: transparent; }
    th { background: #161b22; }
    blockquote { background: #161b22; color: #8b949e; }
    code { background: #161b22; }
    .disclaimer { background: #332b00; border-color: #735c0f; color: #e3b341; }
    abbr { text-decoration-color: #58a6ff; }
    .badge.industry { background: #30363d; color: #c9d1d9; }
    .mermaid { background: #161b22; border-color: #30363d; }
  }
</style>
"""

# ──────────────────────────── Mermaid 图表支持 ────────────────────────────
MERMAID_SCRIPT = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  mermaid.initialize({ startOnLoad: true, theme: isDark ? 'dark' : 'default' });
</script>
"""


def _enable_mermaid(html_body: str) -> str:
    """把 <pre><code class="language-mermaid">...</code></pre> 改写成 <div class="mermaid">...</div>
    这样 mermaid.js 的 startOnLoad 会自动渲染。"""
    pattern = re.compile(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        re.DOTALL,
    )
    return pattern.sub(
        lambda m: f'<div class="mermaid">{html.unescape(m.group(1))}</div>',
        html_body,
    )

NAV = """
<nav>
  <a href="/">🏠 首页</a>
  <a href="/glossary">📖 术语表</a>
  <a href="/about">ℹ️ 关于</a>
</nav>
"""


def _page(title: str, body: str) -> bytes:
    html_text = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · VC Research</title>
{STYLE}
</head><body>{NAV}{body}{MERMAID_SCRIPT}</body></html>"""
    return html_text.encode("utf-8")


# ──────────────────────────── 研报生成 (内存) ────────────────────────────
_REPORT_CACHE: dict[str, VCReport] = {}


def _build_report(name: str) -> VCReport | None:
    """从 fixtures 实时构建 VCReport,带进程内缓存."""
    if name in _REPORT_CACHE:
        return _REPORT_CACHE[name]

    raw = DataAggregator(
        use_fixtures=True, enable_llm_research=True
    ).fetch(name)
    if raw.is_empty():
        return None
    try:
        profile = analyze_profile(raw)
    except InsufficientDataError:
        return None
    funding = analyze_funding(raw)
    thesis = analyze_thesis(raw)
    industry = analyze_industry(raw, profile.industry)
    valuation = analyze_valuation(funding, thesis, industry=profile.industry)
    risks = analyze_risks(raw, funding, thesis)
    rec = analyze_recommendation(thesis, valuation, risks, funding)

    report = VCReport(
        generated_at=date.today(),
        profile=profile,
        funding=funding,
        thesis=thesis,
        industry=industry,
        valuation=valuation,
        risks=risks,
        recommendation=rec,
        data_sources=raw.sources_hit,
    )
    _REPORT_CACHE[name] = report
    return report


# ──────────────────────────── 路由 handlers ────────────────────────────
def _index() -> bytes:
    """首页 — 列出 fixtures 下所有公司,实时构建卡片元信息."""
    companies = sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))
    cards = []
    for name in companies:
        report = _build_report(name)
        if report is None:
            continue
        verdict = report.recommendation.verdict
        risk = report.risks.overall_level.value
        industry_str = report.profile.industry
        rounds_n = len(report.funding.rounds)
        valuation_h = report.funding.latest_valuation_usd
        val_text = (
            f"${int(valuation_h):,}" if valuation_h else "估值未披露"
        )
        cards.append(
            f"""<div class="card">
  <a class="title" href="/report/{html.escape(name)}">📊 {html.escape(name)}</a>
  <div class="meta">{html.escape(report.profile.one_liner[:50])}…</div>
  <div class="meta">📈 {rounds_n} 轮 · 最新估值 {val_text}</div>
  <div class="badges">
    <span class="badge industry">{html.escape(industry_str)}</span>
    <span class="badge verdict-{html.escape(verdict)}">{html.escape(verdict)}</span>
    <span class="badge risk-{html.escape(risk)}">风险 {html.escape(risk)}</span>
  </div>
</div>"""
        )

    cards_html = (
        f"<div class='grid'>{''.join(cards)}</div>"
        if cards
        else "<p>暂无 fixtures。</p>"
    )

    available = ", ".join(companies) if companies else "(暂无)"
    body = f"""
<h1>📊 VC Research Dashboard</h1>
<p>创投企业投资分析系统 · 为零基础投资者打造 · 7 层分析框架 ·
  <a href="/glossary">术语不懂?查术语表</a>
</p>

<h2>🔎 查任意公司</h2>
<form action="/search" method="get" style="display:flex;gap:.5em;margin:1em 0;max-width:520px"
      onsubmit="document.getElementById('spinner').style.display='block'">
  <input type="text" name="q" placeholder="输入公司中文名 (如:糖吉医疗、字节跳动)" required
         style="flex:1;padding:.6em .8em;border:1px solid #d0d7de;border-radius:6px;font-size:1em">
  <button type="submit"
         style="padding:.6em 1.2em;background:#0969da;color:#fff;border:0;border-radius:6px;font-size:1em;cursor:pointer">
    生成研报
  </button>
</form>
<div id="spinner" style="display:none;margin:.5em 0 1em;padding:.8em;background:#fff8c5;border-radius:6px;font-size:.95em">
  ⏳ 本地 Qwen3 推断中,预计 60-120 秒。请耐心等待,勿关闭页面。
</div>
<p style="color:#6a737d;font-size:.9em;margin-top:-.5em">
  <b>标杆案例</b> (下方)秒开;<b>其他公司</b>由本地 Qwen3 32B 实时推断(1-2 分钟),
  研报顶部会明确标注"LLM 推断,需交叉核实"。
</p>

<h2>🗂️ 标杆案例 ({len(cards)})</h2>
{cards_html}
<p style="color:#6a737d;font-size:.9em;margin-top:2em">
  💡 点击任意案例查看完整研报,关键术语悬停即显示类比解释。
</p>

<div class="disclaimer" style="margin-top:2.5em">
  ⚠️ <b>免责声明</b>:本系统所有研报仅供学习研究,<b>不构成投资建议</b>。
  数据可能过时或由本地 LLM 推断,决策前请独立核实。
  术语不懂?<a href="/glossary">点这里查术语表</a>。
</div>

<p style="color:#6a737d;font-size:.85em;margin-top:1em;border-top:1px solid #eaecef;padding-top:.8em">
  LLM 缓存目录:<code>~/.vc-research/llm_cache/</code> (TTL 30 天) ·
  <a href="/clear-cache">🧹 清所有 LLM 缓存</a> ·
  <a href="/glossary">📖 术语表</a> ·
  <a href="/about">ℹ️ 关于</a>
</p>
"""
    return _page("首页", body)


def _glossary() -> bytes:
    """渲染 docs/glossary.md."""
    path = DOCS_DIR / "glossary.md"
    if not path.exists():
        return _page("术语表", "<h1>glossary.md 未找到</h1>")
    html_body = markdown.markdown(
        path.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]
    )
    html_body = _sanitize_html(html_body)
    return _page("术语表", html_body)


def _clear_cache() -> bytes:
    """清空 LLM 磁盘缓存 + 进程内研报缓存。"""
    deleted = 0
    if LLM_CACHE_DIR.exists():
        for f in LLM_CACHE_DIR.glob("*.json"):
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass
    # 清掉非 fixtures 的进程缓存(fixtures 秒构建,留着也无妨,但一并清更干净)
    global _REPORT_CACHE
    _REPORT_CACHE = {}
    body = f"""
<h1>🧹 缓存已清</h1>
<p>删除 LLM 磁盘缓存文件: <b>{deleted}</b> 个。</p>
<p>进程内研报缓存已重置。下次访问任一公司都会重新构建。</p>
<p><a href="/">← 返回首页</a></p>
"""
    return _page("清缓存", body)


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
<h2>教育哲学</h2>
<p>连接+流动 · 神经可塑性 · 游戏化 · 刻意练习 — 每份研报都在训练"投前思考框架"。</p>
<h2>版本</h2>
<p>v0.1.0-alpha.3 · Phase 1 骨架 + 教育层注入 + 数据源契约</p>
"""
    return _page("关于", body)


def _report(name: str) -> tuple[bytes, int]:
    report = _build_report(name)
    if report is None:
        available = sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))
        links = " · ".join(
            f'<a href="/report/{html.escape(a)}">{html.escape(a)}</a>' for a in available
        )
        body = f"""
<h1>🤷 {html.escape(name)} · 生成失败</h1>
<div class="disclaimer">
  本地大模型 (Qwen3) 未能产出结构化数据 —— 可能是模型服务未运行,
  或返回格式异常。请检查:
  <ol>
    <li><code>ollama serve</code> 是否在运行 (<code>curl localhost:11434/api/tags</code> 应返回模型列表)</li>
    <li><code>ollama list</code> 是否有 <code>qwen3:32b</code></li>
    <li>查看 dashboard 进程日志 <code>/tmp/vc-dashboard.log</code></li>
  </ol>
</div>
<h2>已收录的标杆案例(可直接查看)</h2>
<p>{links}</p>
<p><a href="/">← 返回首页</a></p>
"""
        return _page(f"{name} · 生成失败", body), 404
    md_text = render_markdown(report)
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html_body = _sanitize_html(html_body)
    html_body = _enable_mermaid(html_body)
    html_body = _inject_tooltips(html_body)
    return _page(name, html_body), 200


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        raw_path = self.path
        path = unquote(raw_path)
        redirect_to: str | None = None

        if path in ("/", ""):
            body, status = _index(), 200
        elif path == "/about":
            body, status = _about(), 200
        elif path == "/glossary":
            body, status = _glossary(), 200
        elif path == "/clear-cache":
            body, status = _clear_cache(), 200
        elif path.startswith("/search"):
            from urllib.parse import parse_qs, urlparse, quote
            q = parse_qs(urlparse(raw_path).query).get("q", [""])[0].strip()
            if q:
                redirect_to = f"/report/{quote(q)}"
                body, status = b"", 302
            else:
                body, status = _page("404", "<h1>请输入公司名</h1>"), 400
        elif path.startswith("/report/"):
            name = path[len("/report/") :]
            body, status = _report(name)
        else:
            body, status = _page("404", "<h1>404</h1>"), 404

        self.send_response(status)
        if redirect_to is not None:
            self.send_header("Location", redirect_to)
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
    print(f"📁 Fixtures dir: {FIXTURES_DIR}")

    if not args.no_browser:
        webbrowser.open(url)

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 bye")


if __name__ == "__main__":
    main()
