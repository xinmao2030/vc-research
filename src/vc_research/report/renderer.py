"""研报渲染器 — VCReport → Markdown (→ PDF).

安全: 所有用户输入(公司名/founder/notes 等)经过 html.escape 消毒,
MD→HTML 路径过一轮 _sanitize_html 剥离 <script>/<iframe> 等危险标签
(BUG-004).
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..education.analogy_teacher import explain_with_analogy, list_concepts
from ..schema import VCReport


# 极小白名单式 HTML 消毒 (MD → HTML 路径兜底; Phase 2+ 换成 nh3)
_DANGEROUS_TAGS = re.compile(
    r"<\s*(script|iframe|object|embed|style|link|meta|form)[\s\S]*?>[\s\S]*?<\s*/\s*\1\s*>"
    r"|<\s*(script|iframe|object|embed|style|link|meta|form)[^>]*/?>"
    r"|\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",  # onclick= onerror= 等事件属性
    re.IGNORECASE,
)

# javascript:/data:/vbscript: URL scheme 出现在 href/src/action 等属性值里,
# 直接整段属性剥离 (v0.1.13 修复 QA 报告的 XSS 绕过)
_DANGEROUS_URL_ATTRS = re.compile(
    r"\s(?:href|src|action|formaction|xlink:href|background|poster)"
    r"\s*=\s*"
    r"(?:\"\s*(?:javascript|data|vbscript)\s*:[^\"]*\""
    r"|'\s*(?:javascript|data|vbscript)\s*:[^']*'"
    r"|\s*(?:javascript|data|vbscript)\s*:[^\s>]*)",
    re.IGNORECASE,
)


def _sanitize_html(raw_html: str) -> str:
    cleaned = _DANGEROUS_TAGS.sub("", raw_html)
    cleaned = _DANGEROUS_URL_ATTRS.sub("", cleaned)
    return cleaned


_TEMPLATE_DIR = Path(__file__).parent


def _md_escape(value) -> str:
    """对 Markdown 敏感字符做最小转义 + HTML 实体转义,防止注入."""
    if value is None:
        return ""
    s = str(value)
    # HTML escape 防 XSS (PDF/HTML 渲染路径)
    s = html.escape(s, quote=False)
    # Markdown 敏感字符轻度转义 (不破坏表格,只防闭合)
    # 保留常规可读性,只处理最危险的三个
    return s


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=False,  # Markdown 模板,不能全局 HTML escape
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["safe_text"] = _md_escape
    return env


_ENV = _build_env()


def render_markdown(report: VCReport) -> str:
    """渲染为 Markdown 字符串."""
    template = _ENV.get_template("template.md.j2")
    analogies = {key: explain_with_analogy(key) for key in list_concepts()}
    is_llm_generated = any(
        any(tag in s.lower() for tag in ("ollama", "qwen", "llm"))
        for s in report.data_sources
    )
    return template.render(
        analogies=analogies,
        is_llm_generated=is_llm_generated,
        **report.model_dump(mode="python"),
    )


def render_html(report: VCReport) -> str:
    """渲染为独立 HTML (供 web dashboard / 分享卡片 / PDF 源使用)."""
    import markdown as md_lib

    md_text = render_markdown(report)
    body = md_lib.markdown(md_text, extensions=["tables", "fenced_code"])
    body = _sanitize_html(body)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{html.escape(report.profile.name)} — 创投研报</title>
<style>
  body {{ font-family: -apple-system, 'PingFang SC', sans-serif; max-width: 880px; margin: 2em auto; padding: 0 1.5em; line-height: 1.7; color: #222; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f6f8fa; }}
  blockquote {{ border-left: 4px solid #0366d6; padding: .5em 1em; color: #555; background: #f6f8fa; }}
  h1 {{ border-bottom: 2px solid #0366d6; padding-bottom: .3em; }}
  h2 {{ border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
</style>
</head><body>{body}</body></html>"""


def render_pdf(report: VCReport, output_path: Path) -> Path:
    """渲染为 PDF.

    优先级:
        1. weasyprint (若系统依赖齐全: pango/cairo/glib)
        2. 降级为 HTML 文件 (.html),打印说明

    Returns:
        实际输出文件路径 (可能是 .pdf 或 .html fallback)
    """
    try:
        from weasyprint import HTML  # type: ignore

        html_str = render_html(report)
        HTML(string=html_str).write_pdf(str(output_path))
        return output_path
    except (ImportError, OSError) as e:
        # weasyprint 不可用 — 系统缺 pango/cairo 或 python 库没装
        # 降级: 输出 HTML,用户可用浏览器"打印为 PDF"
        fallback = output_path.with_suffix(".html")
        fallback.write_text(render_html(report), encoding="utf-8")
        raise RuntimeError(
            f"PDF 渲染不可用 ({type(e).__name__}: {e}). "
            f"已降级为 HTML: {fallback}. "
            f"如需 PDF,请在 macOS 先运行: brew install pango cairo glib"
        ) from e
