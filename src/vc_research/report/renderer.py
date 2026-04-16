"""研报渲染器 — VCReport → Markdown (→ PDF)."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..schema import VCReport


_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(disabled_extensions=("md", "j2")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_markdown(report: VCReport) -> str:
    """渲染为 Markdown 字符串."""
    template = _ENV.get_template("template.md.j2")
    return template.render(**report.model_dump(mode="python"))


def render_pdf(report: VCReport, output_path: Path) -> None:
    """渲染为 PDF (需要 weasyprint)."""
    try:
        import markdown
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError(
            "PDF 渲染需要 `pip install markdown weasyprint`"
        ) from e

    md_text = render_markdown(report)
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    styled = f"""
    <html><head><meta charset="utf-8"><style>
    body {{ font-family: 'PingFang SC', sans-serif; max-width: 800px; margin: 2em auto; line-height: 1.6; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
    blockquote {{ border-left: 4px solid #0366d6; padding: 0.5em 1em; color: #555; }}
    h1, h2, h3 {{ color: #24292e; }}
    </style></head><body>{html}</body></html>
    """
    HTML(string=styled).write_pdf(str(output_path))
