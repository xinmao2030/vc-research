"""Ollama 本地 LLM 研究员 — 任意公司名 → Qwen3 生成结构化 RawCompanyData.

无需外部 API key。默认连 http://localhost:11434,模型 qwen3:32b。

产出物直接 routing 到 raw.itjuzi,模块无需改动。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger(__name__)


DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:32b"
DEFAULT_TIMEOUT_S = 180
DEFAULT_CACHE_DIR = Path.home() / ".vc-research" / "llm_cache"
DEFAULT_CACHE_TTL_DAYS = 30

_PROMPT_TEMPLATE = """你是一位资深创投分析师。请为公司 "{company}" 产出一份结构化 JSON 深度研报。

分析步骤:
1. 从公司中文名推断赛道。例如 "糖吉医疗"→糖尿病管理/医疗器械、
   "云鲸科技"→智能家电、"黑芝麻智能"→自动驾驶芯片。
2. 如果公司在你的训练知识里,使用已知事实(创始人、成立年份、融资等)。
3. 如果陌生,基于推断的赛道,给出该赛道典型早期公司的合理数值。
4. 任何推断,必须在 business_model 或 team_notes 里含 "(基于名字和赛道推断)"。

现在请直接输出以下 JSON(不要加 markdown 围栏,不要输出思考过程):

{{
  "legal_name": "完整法人名",
  "founded_date": "YYYY-MM-DD",
  "headquarters": "总部城市",
  "region": "cn",
  "industry": "AI / SaaS / 生物医药 / 硬件 / 电商 / 金融科技 / 新能源 / 医疗器械 / 消费 / 教育 / 企业服务 之一,**不能为 null**",
  "sub_industry": "二级细分",
  "business_model": "一句话商业模式",
  "stage": "seed / a / b / c / d / pre-ipo / ipo / strategic 之一",
  "employee_count": 整数,
  "one_liner": "一句话概括公司,**不能为 null**",
  "website": "公司官网或主要产品站点 URL",
  "founders": [
    {{"name": "姓名", "title": "CEO", "background": "教育/过往履历/关键成就",
      "equity_pct": 0.15, "still_active": true, "current_role": null}}
  ],
  "executives": [
    {{"name": "姓名", "title": "CTO / COO / CFO 等", "joined": "YYYY",
      "background": "上一家公司/学历/代表成就"}}
  ],
  "products": ["核心产品1", "核心产品2"],
  "key_customers": ["标志性客户或用户群体1", "...2"],
  "milestones": [
    {{"date": "YYYY", "event": "关键非融资里程碑,如产品上线/出海/重大合作"}}
  ],
  "rounds": [
    {{"stage": "angel", "announce_date": "YYYY-MM-DD", "amount_usd": 2000000,
      "pre_money_valuation_usd": 8000000, "post_money_valuation_usd": 10000000,
      "lead_investors": ["机构"], "participants": ["机构A","机构B"],
      "share_class": "普通股 / A 轮优先股",
      "use_of_proceeds": "产品研发 / 市场扩张 / 出海",
      "notes": "备注",
      "investor_details": [
        {{"name": "机构名", "type": "VC", "hq": "北京", "aum_usd": 1000000000,
          "founded_year": 2010, "sector_focus": ["AI","医疗"],
          "notable_portfolio": ["明星项目1","明星项目2"],
          "deal_thesis": "本轮为什么投的一句话逻辑", "is_lead": true}}
      ]}}
  ],
  "thesis": {{
    "team_score": 7,
    "team_notes": "团队点评 headline",
    "team_analysis": "3-5 句话深度分析:创始人执行力/高管互补性/过往胜率/文化",
    "market": {{"tam_usd": 10000000000, "sam_usd": 2000000000, "som_usd": 200000000, "growth_rate": 0.2}},
    "market_analysis": "3-5 句话:TAM/SAM/SOM 推导过程 + 增长驱动 + 渗透率曲线阶段",
    "moat": "护城河描述 headline",
    "moat_analysis": {{
      "network_effect":     {{"score": 0, "evidence": "若无此维度设 score=0 / evidence 留空"}},
      "scale_economy":      {{"score": 0, "evidence": ""}},
      "switching_cost":     {{"score": 0, "evidence": ""}},
      "brand":              {{"score": 0, "evidence": ""}},
      "counter_positioning":{{"score": 0, "evidence": ""}},
      "cornered_resource":  {{"score": 0, "evidence": ""}},
      "process_power":      {{"score": 0, "evidence": ""}}
    }},
    "unit_economics": {{"gross_margin": 0.5, "payback_months": 18, "ltv_cac_ratio": 3.0}},
    "unit_economics_analysis": "3 句话:LTV/CAC/毛利相对行业中位数位置 + 趋势",
    "growth": {{"arr_usd": null, "yoy_growth": 0.5, "retention_m12": null}},
    "growth_analysis": "3 句话:增长质量 / 自然增长占比 / S 曲线阶段",
    "competitors": ["竞品1", "竞品2", "竞品3"],
    "competitors_detailed": [
      {{"name": "竞品1", "hq": "上海", "stage_or_status": "D 轮",
        "valuation_usd": 2000000000, "market_share_pct": 0.15,
        "differentiator": "与本公司核心差异", "threat_level": "high"}}
    ],
    "bull": ["看多 headline 1", "..."],
    "bull_detailed": [
      {{"headline": "看多 headline", "analysis": "2-4 句展开论据",
        "evidence": ["数据点 1", "数据点 2"]}}
    ],
    "bear": ["看空 headline 1", "..."],
    "bear_detailed": [
      {{"headline": "看空 headline", "analysis": "2-4 句展开论据",
        "evidence": ["数据点"]}}
    ]
  }},
  "industry_data": {{
    "funding_total_12m_usd": 5000000000,
    "deal_count_12m": 100,
    "gartner_phase": "成熟期 / 复苏期 / 幻灭期 / 炒作期 / 萌芽期 之一",
    "policy_tailwinds": ["利好1", "利好2"],
    "policy_headwinds": ["利空1"],
    "exit_window": "退出窗口描述",
    "hot_keywords": ["热词1", "热词2", "热词3"],
    "sub_segments": [
      {{"name": "子赛道1", "size_usd": 3000000000, "growth_rate": 0.35,
        "notes": "为什么这个细分有/没有机会"}}
    ],
    "value_chain": {{
      "upstream":   ["原料/元器件/工具供应商"],
      "midstream":  ["本公司所处环节的其他玩家"],
      "downstream": ["渠道/分销/终端客户"]
    }},
    "top_players": [
      {{"name": "行业头部1", "hq": "北京", "stage_or_status": "已上市",
        "valuation_usd": 10000000000, "market_share_pct": 0.25,
        "differentiator": "核心差异"}}
    ],
    "growth_drivers": ["技术/需求/政策/人口 的底层驱动力,3-5 条"],
    "barriers_to_entry": ["资本 / 技术 / 牌照 / 网络效应 门槛,3-5 条"],
    "industry_key_metrics": {{"行业 KPI 名": "当前水平"}}
  }},
  "financials": {{"burn_rate_usd_monthly": 500000, "cash_usd": 8000000}},
  "extra_risks": [
    {{"category": "监管", "description": "...", "level": "medium", "mitigation": "..."}},
    {{"category": "市场", "description": "...", "level": "medium", "mitigation": "..."}}
  ]
}}

硬性要求:
- 所有金额统一用美元(数字,不带单位)。
- moat_analysis 7 个维度必须全部出现;确实无此优势就填 score=0、evidence=""。
- investor_details 至少覆盖领投方;若不了解具体机构档案,仍要给出合理推断并在 deal_thesis 里标注"(推断)"。
- sub_segments 至少 3 条(大赛道切成可投资细分)。
- growth_drivers / barriers_to_entry 各至少 3 条。"""


class OllamaResearcher:
    """用本地 Ollama 运行的大模型做"任意公司结构化抽取"。"""

    name = "itjuzi"  # 路由目标: payload 填入 raw.itjuzi,复用现有分析模块
    provenance = "ollama/qwen3:32b"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        cache_dir: Path | None = None,
        cache_ttl_days: int | None = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.base_url = (
            base_url or os.getenv("OLLAMA_URL", DEFAULT_URL)
        ).rstrip("/")
        self.timeout_s = timeout_s
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        ttl_env = os.getenv("VC_LLM_CACHE_TTL_DAYS")
        if cache_ttl_days is not None:
            self.cache_ttl_days = cache_ttl_days
        elif ttl_env and ttl_env.isdigit():
            self.cache_ttl_days = int(ttl_env)
        else:
            self.cache_ttl_days = DEFAULT_CACHE_TTL_DAYS

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        cached = self._load_cache(company_name)
        if cached is not None:
            logger.info("LLM cache hit: %s", company_name)
            return cached

        user_prompt = _PROMPT_TEMPLATE.format(company=company_name) + "\n/no_think"
        raw = self._call_ollama(user_prompt)
        if not raw:
            return None
        data = self._parse_json(raw)
        if not data:
            return None
        # 视作"无数据"的兜底:核心字段全空
        if not data.get("industry") and not data.get("one_liner"):
            logger.info("Ollama 对 %s 返回空壳,视作未命中", company_name)
            return None
        self._save_cache(company_name, data)
        return data

    # ──────────────────────────── cache ────────────────────────────
    def _cache_path(self, company: str) -> Path:
        safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", company).strip("_") or "_"
        model_key = self.model.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{model_key}__{safe}.json"

    def _load_cache(self, company: str) -> dict[str, Any] | None:
        path = self._cache_path(company)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("缓存文件坏 %s: %s", path, e)
            return None
        ts = entry.get("cached_at", 0)
        age_days = (time.time() - ts) / 86400
        if age_days > self.cache_ttl_days:
            logger.info("缓存 %s 超过 %d 天,视作过期", company, self.cache_ttl_days)
            return None
        return entry.get("payload")

    def _save_cache(self, company: str, payload: dict[str, Any]) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(company)
            path.write_text(
                json.dumps(
                    {
                        "company": company,
                        "model": self.model,
                        "cached_at": time.time(),
                        "payload": payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("写缓存失败 %s: %s", company, e)

    # ──────────────────────────── internals ────────────────────────────
    def _call_ollama(self, prompt: str) -> str | None:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.35, "num_predict": 8192},
            }
        ).encode("utf-8")
        req = urlrequest.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urlerror.URLError, TimeoutError, OSError) as e:
            logger.warning("Ollama 连接失败: %s", e)
            return None
        except json.JSONDecodeError as e:
            logger.warning("Ollama 响应非 JSON: %s", e)
            return None
        return payload.get("response")

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        """宽容解析: 剥离 <think>...</think> / markdown fence / 前后噪声."""
        stripped = text.strip()
        if "<think>" in stripped and "</think>" in stripped:
            stripped = stripped.split("</think>", 1)[1].strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
            if stripped.endswith("```"):
                stripped = stripped[: -3].strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.warning("LLM 响应无法定位 JSON 区间")
            return None
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as e:
            logger.warning("LLM JSON 解析失败: %s", e)
            return None
