"""LLM 研究员 — 任意公司名 → 大模型生成结构化 RawCompanyData.

支持任意 LLMProvider (Ollama/DeepSeek/GPT-4o/Kimi 等)。
默认使用 Ollama 本地 Qwen3，无需外部 API key。
产出物直接 routing 到 raw.itjuzi,模块无需改动。

向后兼容: OllamaResearcher 作为 LLMResearcher 的别名保留。
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


def parse_search_input(raw: str) -> tuple[str, dict[str, str]]:
    """解析搜索输入,提取公司名和附加提示(股票代码/交易所).

    支持格式:
      "群核科技 港股00068"     → ("群核科技", {"stock_code": "00068", "exchange": "港股"})
      "群核科技 HK:00068"     → ("群核科技", {"stock_code": "00068", "exchange": "HK"})
      "群核科技 SH:688xxx"    → ("群核科技", {"stock_code": "688xxx", "exchange": "SH"})
      "群核科技 00068.HK"     → ("群核科技", {"stock_code": "00068", "exchange": "HK"})
      "群核科技"              → ("群核科技", {})
    """
    raw = raw.strip()
    hints: dict[str, str] = {}

    # Pattern 1: "XX:NNNNNN" 如 HK:00068, SH:688001, SZ:300001
    m = re.search(r'\b([A-Za-z]{2,6})[:\uff1a](\d{4,6})\b', raw)
    if m:
        hints["exchange"] = m.group(1).upper()
        hints["stock_code"] = m.group(2)
        company = raw[:m.start()].strip() or raw[m.end():].strip()
        return company, hints

    # Pattern 2: "NNNNNN.XX" 如 00068.HK, 688001.SH
    m = re.search(r'\b(\d{4,6})\.([A-Za-z]{2,6})\b', raw)
    if m:
        hints["stock_code"] = m.group(1)
        hints["exchange"] = m.group(2).upper()
        company = raw[:m.start()].strip() or raw[m.end():].strip()
        return company, hints

    # Pattern 3: 中文交易所 + 代码 如 "港股00068", "A股688001", "沪市688001", "深市300001"
    m = re.search(r'(港股|美股|A股|沪市|深市|科创板|创业板|北交所|港交所|纳斯达克|纽交所)(\d{4,6})', raw)
    if m:
        exchange_map = {
            "港股": "HK", "港交所": "HK",
            "美股": "US", "纳斯达克": "NASDAQ", "纽交所": "NYSE",
            "A股": "CN", "沪市": "SH", "深市": "SZ",
            "科创板": "SH", "创业板": "SZ", "北交所": "BJ",
        }
        hints["exchange"] = exchange_map.get(m.group(1), m.group(1))
        hints["stock_code"] = m.group(2)
        company = raw[:m.start()].strip() or raw[m.end():].strip()
        return company, hints

    # Pattern 4: 尾部独立数字代码 如 "群核科技 00068"
    m = re.search(r'\s+(\d{4,6})\s*$', raw)
    if m:
        hints["stock_code"] = m.group(1)
        company = raw[:m.start()].strip()
        return company, hints

    return raw, hints


DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT_S = 600
DEFAULT_CACHE_DIR = Path.home() / ".vc-research" / "llm_cache"
DEFAULT_CACHE_TTL_DAYS = 30

_PROMPT_PART1 = """你是一位资深创投分析师。请为公司 "{company}" 产出企业基础信息的结构化 JSON。
{stock_hint}
分析步骤:
1. 从公司中文名推断赛道。例如 "糖吉医疗"→糖尿病管理/医疗器械。
2. 如果公司在你的训练知识里,使用已知事实。
3. 如果陌生,基于推断的赛道,给出合理数值,在 business_model 标注"(基于赛道推断)"。

直接输出 JSON(不要 markdown 围栏,不要思考过程):

{{
  "legal_name": "完整法人名",
  "founded_date": "YYYY-MM-DD",
  "headquarters": "总部城市",
  "region": "cn",
  "industry": "AI/SaaS/生物医药/硬件/电商/金融科技/新能源/医疗器械/消费/教育/企业服务 之一",
  "sub_industry": "二级细分",
  "business_model": "一句话商业模式",
  "stage": "seed/a/b/c/d/pre-ipo/ipo/strategic 之一",
  "employee_count": 整数,
  "one_liner": "一句话概括公司",
  "website": "官网 URL",
  "founders": [
    {{"name": "姓名", "title": "CEO",
      "background": "籍贯 | 学历 | 职业经历 | 创业经历",
      "equity_pct": 0.15, "still_active": true, "current_role": null}}
  ],
  "executives": [
    {{"name": "姓名", "title": "CFO", "joined": "YYYY",
      "background": "学历 | 职业经历"}}
  ],
  "products": [
    {{"name": "产品名", "category": "硬件/软件/SaaS/平台",
      "description": "产品定位、核心功能、应用场景",
      "specs": {{}}, "launched": "YYYY-MM", "image_url": null,
      "revenue_contribution": "60%"}}
  ],
  "key_customers": [
    {{"name": "客户名", "type": "企业/政府/消费者",
      "cooperation_since": "YYYY",
      "cooperation_detail": "合作内容",
      "result": "合作成果", "annual_value_usd": null}}
  ],
  "milestones": [
    {{"date": "YYYY-MM", "event": "关键事件", "impact": "意义"}}
  ],
  "rounds": [
    {{"stage": "angel", "announce_date": "YYYY-MM-DD", "amount_usd": 2000000,
      "pre_money_valuation_usd": 8000000, "post_money_valuation_usd": 10000000,
      "lead_investors": ["领投机构"], "participants": ["跟投"],
      "share_class": "优先股", "use_of_proceeds": "研发",
      "notes": "", "investor_details": [
        {{"name": "机构名", "type": "VC", "hq": "北京", "aum_usd": 1000000000,
          "founded_year": 2010, "sector_focus": ["AI"],
          "notable_portfolio": ["项目1"], "deal_thesis": "投资逻辑", "is_lead": true}}
      ]}}
  ],
  "financials": {{"burn_rate_usd_monthly": 500000, "cash_usd": 8000000}},
  "extra_risks": [
    {{"category": "监管", "description": "...", "level": "medium", "mitigation": "..."}}
  ]
}}

要求: founders 至少 2 人, executives 至少 2 人, products 至少 2 个, rounds 至少 3 轮, milestones 至少 4 个。金额用美元数字。"""


_PROMPT_PART2 = """你是一位资深创投分析师。我已有公司 "{company}" 的基础信息,现在请补充投资分析部分。
该公司行业: {industry}, 阶段: {stage}。

直接输出 JSON(不要 markdown 围栏,不要思考过程):

{{
  "thesis": {{
    "team_score": 7,
    "team_notes": "团队点评",
    "team_analysis": "3句话分析",
    "market": {{"tam_usd": 10000000000, "sam_usd": 2000000000, "som_usd": 200000000, "growth_rate": 0.2}},
    "market_analysis": "3句话分析",
    "moat": "护城河描述",
    "moat_analysis": {{
      "network_effect": {{"score": 0, "evidence": ""}},
      "scale_economy": {{"score": 0, "evidence": ""}},
      "switching_cost": {{"score": 0, "evidence": ""}},
      "brand": {{"score": 0, "evidence": ""}},
      "counter_positioning": {{"score": 0, "evidence": ""}},
      "cornered_resource": {{"score": 0, "evidence": ""}},
      "process_power": {{"score": 0, "evidence": ""}}
    }},
    "unit_economics": {{"gross_margin": 0.5, "payback_months": 18, "ltv_cac_ratio": 3.0}},
    "unit_economics_analysis": "3句话",
    "growth": {{"arr_usd": null, "yoy_growth": 0.5, "retention_m12": null}},
    "growth_analysis": "3句话",
    "competitors": ["竞品1", "竞品2", "竞品3"],
    "competitors_detailed": [
      {{"name": "竞品1", "hq": "城市", "stage_or_status": "D轮",
        "valuation_usd": 2000000000, "market_share_pct": 0.15,
        "differentiator": "差异", "threat_level": "high"}}
    ],
    "bull": ["看多1"], "bull_detailed": [{{"headline": "看多", "analysis": "论据", "evidence": ["数据"]}}],
    "bear": ["看空1"], "bear_detailed": [{{"headline": "看空", "analysis": "论据", "evidence": ["数据"]}}]
  }},
  "industry_data": {{
    "funding_total_12m_usd": 5000000000,
    "deal_count_12m": 100,
    "gartner_phase": "成熟期/复苏期/幻灭期/炒作期/萌芽期 之一",
    "policy_tailwinds": ["利好1"], "policy_headwinds": ["利空1"],
    "exit_window": "退出窗口", "hot_keywords": ["热词1", "热词2"],
    "sub_segments": [{{"name": "子赛道", "size_usd": 3000000000, "growth_rate": 0.35, "notes": "说明"}}],
    "value_chain": {{
      "upstream": ["上游"], "midstream": ["中游"], "downstream": ["下游"]
    }},
    "top_players": [{{"name": "头部1", "hq": "北京", "stage_or_status": "已上市",
      "valuation_usd": 10000000000, "market_share_pct": 0.25, "differentiator": "差异"}}],
    "growth_drivers": ["驱动力1", "驱动力2", "驱动力3"],
    "barriers_to_entry": ["门槛1", "门槛2", "门槛3"],
    "industry_key_metrics": {{"KPI": "水平"}}
  }}
}}

要求: moat_analysis 7维度全部出现, competitors_detailed 至少 3 家, sub_segments 至少 3 条。"""


class LLMResearcher:
    """用任意 LLMProvider 做"任意公司结构化抽取"。

    默认使用 OllamaProvider (本地 Qwen3)。
    可传入 DeepSeek/GPT-4o/Kimi 等 provider 做云端推断。
    """

    name = "itjuzi"  # 路由目标: payload 填入 raw.itjuzi,复用现有分析模块

    def __init__(
        self,
        provider=None,  # LLMProvider | None — 不加类型注解避免循环导入
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        cache_dir: Path | None = None,
        cache_ttl_days: int | None = None,
    ):
        self._provider = provider
        # 向后兼容: 无 provider 时保持原有 Ollama 行为
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

    @property
    def provenance(self) -> str:
        if self._provider:
            return f"{self._provider.name}/{self._provider.model_id}"
        return f"ollama/{self.model}"

    _SAFE_EXCHANGE = re.compile(r'^[A-Z]{2,10}$')
    _SAFE_CODE = re.compile(r'^\d{4,6}$')

    def fetch(self, company_name: str, *, hints: dict[str, str] | None = None) -> dict[str, Any] | None:
        # 输入清洗: 限长 + 去除可能的 prompt 注入字符
        company_name = re.sub(r'[\n\r"\\]', '', company_name)[:80].strip()
        if not company_name:
            logger.warning("空公司名,跳过 LLM 调用")
            return None

        cached = self._load_cache(company_name)
        if cached is not None:
            logger.info("LLM cache hit: %s", company_name)
            return cached

        # 构建股票代码提示,帮助 LLM 准确定位公司 (严格校验防止注入)
        stock_hint = ""
        if hints:
            parts = []
            ex = hints.get("exchange", "")
            code = hints.get("stock_code", "")
            if ex and self._SAFE_EXCHANGE.match(ex):
                parts.append(f"交易所: {ex}")
            if code and self._SAFE_CODE.match(code):
                parts.append(f"股票代码: {code}")
            if parts:
                stock_hint = (
                    "\n⚠️ 重要提示: 该公司的上市/股票信息为 "
                    + ", ".join(parts)
                    + "。请严格基于此股票代码对应的公司进行分析,不要混淆同名公司。\n"
                )

        # ── Part 1: 企业基础信息 ──
        logger.info("Part 1/2: 企业基础信息 — %s", company_name)
        prompt1 = _PROMPT_PART1.format(company=company_name, stock_hint=stock_hint) + "\n/no_think"
        raw1 = self._call_llm(prompt1)
        if not raw1:
            return None
        data = self._parse_json(raw1)
        if not isinstance(data, dict):
            logger.warning("Part1 未返回 dict: %s", type(data))
            return None
        if not data.get("industry") and not data.get("one_liner"):
            logger.info("Ollama 对 %s Part1 返回空壳,视作未命中", company_name)
            return None

        # ── Part 2: 投资分析 + 行业数据 ──
        logger.info("Part 2/2: 投资分析 — %s", company_name)
        prompt2 = _PROMPT_PART2.format(
            company=company_name,
            industry=data.get("industry", "未知"),
            stage=data.get("stage", "未知"),
        ) + "\n/no_think"
        raw2 = self._call_llm(prompt2)
        if raw2:
            part2 = self._parse_json(raw2)
            if part2 and isinstance(part2, dict):
                # 只合并 dict 类型的值,防止 LLM 返回字符串覆盖
                for k, v in part2.items():
                    if isinstance(v, (dict, list)):
                        data[k] = v
                    elif k not in data:
                        data[k] = v

        self._backfill_investor_details(data)
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

    # ──────────────────────────── post-processing ────────────────────
    @staticmethod
    def _backfill_investor_details(data: dict[str, Any]) -> None:
        """确保每轮融资的 investor_details 至少包含 lead_investors."""
        for r in data.get("rounds", []):
            details = r.get("investor_details") or []
            detail_names = {d.get("name", "").lower() for d in details}
            # 从 lead_investors 回填缺失的 investor_details
            for inv in r.get("lead_investors", []):
                if inv.lower() not in detail_names:
                    details.append({
                        "name": inv,
                        "type": "VC",
                        "hq": "",
                        "aum_usd": None,
                        "sector_focus": [],
                        "notable_portfolio": [],
                        "deal_thesis": "(数据待补充)",
                        "is_lead": True,
                    })
            # 从 participants 回填
            for inv in r.get("participants", []):
                if inv.lower() not in detail_names:
                    details.append({
                        "name": inv,
                        "type": "VC",
                        "hq": "",
                        "aum_usd": None,
                        "sector_focus": [],
                        "notable_portfolio": [],
                        "deal_thesis": "(数据待补充)",
                        "is_lead": False,
                    })
                    detail_names.add(inv.lower())
            r["investor_details"] = details

    # ──────────────────────────── internals ────────────────────────────
    def _call_llm(self, prompt: str) -> str | None:
        """调用 LLM — 优先使用 provider，兜底走原生 Ollama HTTP."""
        if self._provider:
            try:
                return self._provider.complete("", prompt, max_tokens=8192)
            except Exception as e:
                logger.warning("LLM provider 调用失败: %s", e)
                return None

        # 原生 Ollama HTTP 调用 (向后兼容)
        return self._call_ollama_raw(prompt)

    def _call_ollama_raw(self, prompt: str) -> str | None:
        """原生 Ollama /api/generate 调用."""
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


# 向后兼容别名
OllamaResearcher = LLMResearcher
