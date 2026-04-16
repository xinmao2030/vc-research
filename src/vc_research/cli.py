"""CLI 入口 — vc-research analyze "字节跳动" 生成研报."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from .data_sources import DataAggregator
from .modules import (
    analyze_funding,
    analyze_industry,
    analyze_profile,
    analyze_recommendation,
    analyze_risks,
    analyze_thesis,
    analyze_valuation,
)
from .modules.company_profile import InsufficientDataError
from .report import render_markdown
from .schema import VCReport

app = typer.Typer(
    help="VC Research — 创投企业投资分析系统",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    company: str = typer.Argument(..., help="企业中文名或英文名"),
    output: Path = typer.Option(
        Path("report.md"), "--output", "-o", help="研报输出路径"
    ),
    fixtures_dir: Path = typer.Option(
        None, "--fixtures", help="覆盖默认 fixtures 目录"
    ),
    use_llm: bool = typer.Option(
        False, "--llm", help="启用 Claude 推理层增强 thesis (需 ANTHROPIC_API_KEY)"
    ),
    pdf: bool = typer.Option(False, "--pdf", help="同时生成 PDF"),
) -> None:
    """分析一家企业并生成研报."""
    console.rule(f"[bold cyan]分析: {company}[/bold cyan]")

    agg = DataAggregator(
        use_fixtures=True,
        fixtures_dir=str(fixtures_dir) if fixtures_dir else None,
    )
    raw = agg.fetch(company)

    if raw.is_empty():
        console.print(
            f"[yellow]⚠️  未在 fixtures 中找到 {company} 的数据。[/yellow]\n"
            f"请在 examples/fixtures/{company}.json 创建数据文件,"
            f"或等待 Phase 2 接入真实数据源。"
        )
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/green] 数据源命中: {', '.join(raw.sources_hit)}")

    # 运行 7 大模块
    try:
        profile = analyze_profile(raw)
    except InsufficientDataError as e:
        console.print(f"[red]✗[/red] 数据不足,无法生成研报: {e}")
        raise typer.Exit(code=2)
    console.print("[green]✓[/green] 模块 1: 企业画像")

    funding = analyze_funding(raw)
    console.print(f"[green]✓[/green] 模块 2: 融资轨迹 ({len(funding.rounds)} 轮)")

    thesis = analyze_thesis(raw)
    console.print("[green]✓[/green] 模块 3: 投资依据")

    industry = analyze_industry(raw, profile.industry)
    console.print("[green]✓[/green] 模块 4: 产业趋势")

    valuation = analyze_valuation(funding, thesis, industry=profile.industry)
    console.print(
        f"[green]✓[/green] 模块 5: 估值分析 "
        f"(公允区间 ${valuation.fair_value_low_usd:,.0f} - ${valuation.fair_value_high_usd:,.0f})"
    )

    risks = analyze_risks(raw, funding, thesis)
    console.print(
        f"[green]✓[/green] 模块 6: 风险矩阵 (整体 {risks.overall_level.value})"
    )

    recommendation = analyze_recommendation(thesis, valuation, risks, funding)
    console.print(
        f"[green]✓[/green] 模块 7: 投资建议 — [bold]{recommendation.verdict}[/bold]"
    )

    # LLM 增强 (可选) — 失败时优雅降级到 base 逻辑,不污染 thesis
    if use_llm:
        console.print("[cyan]🤖 Claude Opus 4.6 推理增强...[/cyan]")
        try:
            from .llm import ClaudeAnalyzer, LLMEnhancementError

            analyzer = ClaudeAnalyzer()
            enhanced = analyzer.enhance_thesis(
                profile.model_dump(mode="python"),
                funding.model_dump(mode="python"),
                thesis.growth.model_dump(mode="python"),
            )
            # 合并 — Pydantic 保证字段类型正确,直接赋值即可
            if enhanced.moat:
                thesis.moat = enhanced.moat
            if enhanced.bull:
                thesis.key_bull_points = enhanced.bull
            if enhanced.bear:
                thesis.key_bear_points = enhanced.bear
            if enhanced.team_notes:
                thesis.team_notes = enhanced.team_notes
            console.print("[green]✓[/green] LLM 增强完成")
        except LLMEnhancementError as e:
            console.print(f"[yellow]⚠️  LLM 增强失败,已降级到 base 逻辑: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  LLM 推理异常: {type(e).__name__}: {e}[/yellow]")

    # 汇总报告
    report = VCReport(
        generated_at=date.today(),
        profile=profile,
        funding=funding,
        thesis=thesis,
        industry=industry,
        valuation=valuation,
        risks=risks,
        recommendation=recommendation,
        data_sources=raw.sources_hit,
    )

    md = render_markdown(report)
    output.write_text(md, encoding="utf-8")
    console.rule("[bold green]✓ 研报生成完成[/bold green]")
    console.print(f"📄 Markdown: [cyan]{output}[/cyan]")

    if pdf:
        try:
            from .report.renderer import render_pdf

            pdf_path = output.with_suffix(".pdf")
            render_pdf(report, pdf_path)
            console.print(f"📄 PDF: [cyan]{pdf_path}[/cyan]")
        except Exception as e:
            console.print(f"[yellow]⚠️  PDF 渲染失败: {e}[/yellow]")


@app.command()
def list_examples() -> None:
    """列出 fixtures 里的标杆企业案例."""
    fixtures_dir = Path(__file__).resolve().parents[2] / "examples" / "fixtures"
    if not fixtures_dir.exists():
        console.print(f"[yellow]Fixtures 目录不存在: {fixtures_dir}[/yellow]")
        return
    files = sorted(fixtures_dir.glob("*.json"))
    if not files:
        console.print("[yellow]暂无 fixtures.[/yellow]")
        return
    console.print("[bold]可分析的标杆案例:[/bold]")
    for f in files:
        console.print(f"  • [cyan]{f.stem}[/cyan]")


if __name__ == "__main__":
    app()
