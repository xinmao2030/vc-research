"""CLI 入口 — vc-research analyze "字节跳动" 生成研报."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from .data_sources import DataAggregator
from .education.quest_unlock import QuestProgress
from .history import load_history, record_report
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
from .modules.valuation import InsufficientValuationError
from .utils import format_money_cn, format_money_en
from .report import render_markdown
from .schema import VCReport

app = typer.Typer(
    help="VC Research — 一级市场创投分析系统（评估未上市 / Pre-IPO 企业）",
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
    live: bool = typer.Option(
        False,
        "--live",
        help="未命中 fixtures 时用本地 Qwen3 (Ollama) 实时推断任意公司",
    ),
    pdf: bool = typer.Option(False, "--pdf", help="同时生成 PDF"),
) -> None:
    """分析一家企业并生成研报."""
    console.rule(f"[bold cyan]分析: {company}[/bold cyan]")
    console.print(
        "[dim]⚠️  免责声明: 本工具产出仅供学习研究,不构成投资建议。"
        "数据可能滞后,重大决策请结合多源验证。[/dim]"
    )

    quest = QuestProgress.load(company)
    console.print(f"[magenta]🎮 闯关进度:[/magenta] {quest.status_bar()}")

    agg = DataAggregator(
        use_fixtures=True,
        fixtures_dir=str(fixtures_dir) if fixtures_dir else None,
        enable_llm_research=live,
    )
    if live:
        console.print(
            "[cyan]🤖 Live 模式:未命中 fixtures 将用本地 Qwen3 推断 "
            "(首次约 60-120 秒,结果会缓存 30 天)[/cyan]"
        )
    raw = agg.fetch(company)

    if raw.is_empty():
        msg = (
            f"请在 examples/fixtures/{company}.json 创建数据文件,"
            f"或用 --live 启用本地 LLM 实时推断。"
            if not live
            else "本地 Qwen3 也未能产出数据,请检查 ollama serve 是否运行。"
        )
        console.print(f"[yellow]⚠️  未找到 {company} 的数据。[/yellow]\n{msg}")
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/green] 数据源命中: {', '.join(raw.sources_hit)}")

    def _tick(key: str, label: str, detail: str = "") -> None:
        tail = f" {detail}" if detail else ""
        console.print(f"[green]✓[/green] {label}{tail}")
        unlocked = quest.complete(key)
        if unlocked:
            console.print(f"   [dim magenta]{unlocked}[/dim magenta]")

    # 运行 7 大模块
    try:
        profile = analyze_profile(raw)
    except InsufficientDataError as e:
        console.print(f"[red]✗[/red] 数据不足,无法生成研报: {e}")
        raise typer.Exit(code=2)
    _tick("profile", "模块 1: 企业画像")

    funding = analyze_funding(raw)
    _tick("funding", "模块 2: 融资轨迹", f"({len(funding.rounds)} 轮)")

    thesis = analyze_thesis(raw)
    _tick("thesis", "模块 3: 投资依据")

    industry = analyze_industry(raw, profile.industry)
    _tick("industry", "模块 4: 产业趋势")

    try:
        valuation = analyze_valuation(funding, thesis, industry=profile.industry)
    except InsufficientValuationError as e:
        console.print(f"[red]✗[/red] 估值数据不足: {e}")
        raise typer.Exit(code=3)
    _tick(
        "valuation",
        "模块 5: 估值分析",
        f"(公允区间 {format_money_cn(valuation.fair_value_low_usd)} — {format_money_cn(valuation.fair_value_high_usd)})",
    )

    risks = analyze_risks(raw, funding, thesis)
    _tick("risks", "模块 6: 风险矩阵", f"(整体 {risks.overall_level.value})")

    recommendation = analyze_recommendation(thesis, valuation, risks, funding)
    _tick(
        "recommendation",
        "模块 7: 投资建议",
        f"— [bold]{recommendation.verdict}[/bold]",
    )
    quest.save()

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

    try:
        record_report(
            company=company,
            verdict=recommendation.verdict,
            latest_valuation=int(funding.latest_valuation_usd) if funding.latest_valuation_usd else None,
            fair_value_low=int(valuation.fair_value_low_usd) if valuation.fair_value_low_usd else None,
            fair_value_high=int(valuation.fair_value_high_usd) if valuation.fair_value_high_usd else None,
            risk_level=risks.overall_level.value,
            rounds=len(funding.rounds),
            report_path=output,
            sources_hit=raw.sources_hit,
            use_llm=use_llm,
            live=live,
        )
    except Exception as e:
        console.print(f"[yellow]⚠️  history 记录失败(不影响研报): {e}[/yellow]")

    console.rule("[bold green]✓ 研报生成完成[/bold green]")
    console.print(f"🎮 闯关进度: {quest.status_bar()}")
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


@app.command()
def history(
    company: str = typer.Argument(None, help="只看某家公司的历史 (可选)"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示最新 N 条"),
    full_path: bool = typer.Option(False, "--full-path", help="显示完整报告路径"),
) -> None:
    """列出已生成的研报记录 (类似标杆案例表格,直观查询历史分析结果)."""
    from rich.table import Table

    rows = load_history(limit=limit, company=company)
    if not rows:
        hint = f"还没有 {company} 的记录" if company else "还没有任何研报记录"
        console.print(f"[yellow]{hint}。先运行 `vc-research analyze <公司名>` 生成一份。[/yellow]")
        return

    verdict_color = {"推荐": "green", "观望": "yellow", "回避": "red"}
    risk_color = {"low": "green", "medium": "yellow", "high": "orange1", "critical": "red"}

    def _fmt_usd(v: int | None) -> str:
        return format_money_en(v)

    table = Table(title=f"📊 研报历史 · 最近 {len(rows)} 条", show_lines=False)
    table.add_column("时间 (UTC)", style="dim", no_wrap=True)
    table.add_column("公司", style="cyan", no_wrap=True)
    table.add_column("裁决", no_wrap=True)
    table.add_column("估值", justify="right")
    table.add_column("公允区间", justify="right")
    table.add_column("风险", no_wrap=True)
    table.add_column("轮次", justify="right")
    table.add_column("增强", no_wrap=True)
    table.add_column("报告", style="dim", overflow="fold")

    for r in rows:
        ts = r.get("ts", "")[:16].replace("T", " ")
        vc = verdict_color.get(r.get("verdict", ""), "white")
        rc = risk_color.get(r.get("risk_level", ""), "white")
        enh_flags = []
        if r.get("use_llm"):
            enh_flags.append("🤖LLM")
        if r.get("live"):
            enh_flags.append("🔴live")
        enh = " ".join(enh_flags) or "—"
        path_str = r.get("report_path", "")
        if not full_path and path_str:
            path_str = Path(path_str).name
        table.add_row(
            ts,
            r.get("company", "?"),
            f"[{vc}]{r.get('verdict', '?')}[/{vc}]",
            _fmt_usd(r.get("latest_valuation")),
            f"{_fmt_usd(r.get('fair_value_low'))} - {_fmt_usd(r.get('fair_value_high'))}",
            f"[{rc}]{r.get('risk_level', '?')}[/{rc}]",
            str(r.get("rounds", 0)),
            enh,
            path_str,
        )
    console.print(table)
    console.print(
        f"[dim]数据源: ~/.vc-research/history.jsonl (共 {len(rows)} 条显示)。"
        "用 --limit N 扩大窗口,--full-path 看完整路径。[/dim]"
    )


if __name__ == "__main__":
    app()
