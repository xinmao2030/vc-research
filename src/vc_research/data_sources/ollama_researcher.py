"""Ollama 本地 LLM 研究员 — 任意公司名 → Qwen3 生成结构化 RawCompanyData.

无需外部 API key。默认连 http://localhost:11434,模型 qwen3:8b (可通过 OLLAMA_MODEL 环境变量切换)。

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
DEFAULT_TIMEOUT_S = 300
DEFAULT_CACHE_DIR = Path.home() / ".vc-research" / "llm_cache"
DEFAULT_CACHE_TTL_DAYS = 30

_PROMPT_TEMPLATE = """你是一位资深创投分析师。请为公司 "{company}" 产出一份结构化 JSON 深度研报。
{stock_hint}
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
    {{"name": "姓名", "title": "CEO",
      "background": "籍贯xx省xx市 | 本科xx大学xx专业(YYYY届) | 硕士/博士xx大学xx方向(YYYY) | 曾任xx公司xx职位(YYYY-YYYY),主导了xx项目 | YYYY年创办本公司,核心成就:xxx",
      "equity_pct": 0.15, "still_active": true, "current_role": null}},
    {{"name": "联创姓名", "title": "CTO",
      "background": "籍贯xx | 本科清华大学计算机(2005) | 博士MIT EECS(2010) | 曾任Google高级工程师(2010-2015) | 曾任xx公司技术VP(2015-2019) | 2019年加入,主导核心技术架构",
      "equity_pct": 0.10, "still_active": true, "current_role": null}}
  ],
  "executives": [
    {{"name": "姓名", "title": "CFO", "joined": "YYYY",
      "background": "籍贯xx | 本科xx大学金融(YYYY) | MBA沃顿商学院(YYYY) | 曾任xx投行MD(YYYY-YYYY) | 曾任xx公司CFO(YYYY-YYYY) | 主导完成x轮融资共$xM"}}
  ],
  "products": [
    {{"name": "产品名称", "category": "硬件/软件/SaaS/平台",
      "description": "3-5句话详细介绍:产品定位、核心功能、技术规格/参数、应用场景、与竞品差异",
      "specs": {{"关键参数1": "值", "关键参数2": "值"}},
      "launched": "YYYY-MM",
      "image_url": "产品官网图片URL(若无则 null)",
      "revenue_contribution": "占总收入比例估算,如 60%"}}
  ],
  "key_customers": [
    {{"name": "客户/用户群名称", "type": "企业/政府/消费者",
      "cooperation_since": "YYYY",
      "cooperation_detail": "2-3句话:合作背景、具体项目内容、采购/部署规模",
      "result": "合作成果:降本xx%/产能提升xx%/覆盖xx用户/续约情况",
      "annual_value_usd": null}}
  ],
  "milestones": [
    {{"date": "YYYY-MM", "event": "关键事件详述(1-2句):产品发布/出海/重大合作/资质认证/专利/奖项等",
      "impact": "对公司发展的意义"}}
  ],
  "rounds": [
    {{"stage": "angel", "announce_date": "YYYY-MM-DD", "amount_usd": 2000000,
      "pre_money_valuation_usd": 8000000, "post_money_valuation_usd": 10000000,
      "lead_investors": ["领投机构"], "participants": ["跟投A","跟投B"],
      "share_class": "普通股 / A 轮优先股",
      "use_of_proceeds": "产品研发 / 市场扩张 / 出海",
      "notes": "备注",
      "investor_details": [
        {{"name": "领投机构", "type": "VC", "hq": "北京", "aum_usd": 1000000000,
          "founded_year": 2010, "sector_focus": ["AI","医疗"],
          "notable_portfolio": ["明星项目1","明星项目2"],
          "deal_thesis": "本轮为什么投的一句话逻辑", "is_lead": true}},
        {{"name": "跟投A", "type": "PE", "hq": "上海", "aum_usd": 5000000000,
          "founded_year": 2005, "sector_focus": ["医疗","消费"],
          "notable_portfolio": ["代表项目1","代表项目2"],
          "deal_thesis": "跟投逻辑:协同/赛道布局/创始人背景", "is_lead": false}},
        {{"name": "跟投B", "type": "CVC", "hq": "深圳", "aum_usd": 3000000000,
          "founded_year": 2015, "sector_focus": ["硬件","新能源"],
          "notable_portfolio": ["已投项目1"],
          "deal_thesis": "产业协同/供应链整合", "is_lead": false}}
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
- **founders 和 executives 的 background 必须包含完整履历**,用 " | " 分隔,依次写:
  籍贯(省市) | 本科学校+专业(毕业年) | 硕士/博士学校+方向(毕业年,若有) | 每段职业经历:公司+职位(起止年)+核心贡献 | 创业经历/加入本公司的时间和角色。
  不了解的信息基于赛道和职位合理推断,在末尾标注"(部分信息基于赛道推断)"。
  founders 至少列出 2 人(CEO + 联创/CTO);executives 至少列出 3 人(CFO/COO/CTO/首席科学家等)。
- moat_analysis 7 个维度必须全部出现;确实无此优势就填 score=0、evidence=""。
- **rounds 是本报告最重要的部分**:
  - 至少输出 3 轮融资(天使轮/Pre-A/A轮/B轮/C轮...),即使不确定具体信息也要基于赛道和阶段合理推断。
  - 每轮必须填写: stage, announce_date, amount_usd, pre_money_valuation_usd, post_money_valuation_usd, lead_investors, participants。
  - 每轮的 investor_details 必须包含**所有投资方**(领投+跟投)的完整档案,每家机构都要填: name/type(VC/PE/CVC/天使/战投/政府基金)/hq/aum_usd/founded_year/sector_focus(≥2个)/notable_portfolio(≥2个已投项目)/deal_thesis(本轮投资逻辑,1-2句)/is_lead。不了解的机构基于名字和类型合理推断,在 deal_thesis 标注"(推断)"。
  - share_class 和 use_of_proceeds 每轮必填。
  - 推断的数据在 notes 里标注"(基于赛道典型值推断)"。
- **products 必须详细**:
  - 至少列出 2-3 个核心产品/业务线。
  - 每个产品的 description 至少 3 句话,涵盖:核心功能、技术规格/参数(如精度/速度/分辨率等)、目标客户、与竞品差异。
  - specs 字典列出关键技术参数(如负载/精度/速度/续航/尺寸)。
  - image_url 填产品官网图片链接,无法确认则填 null。
- **key_customers 必须具体**:
  - 至少列出 3 个标志性客户或用户群。
  - cooperation_detail 必须写清:什么时候开始合作、具体项目内容、采购/部署规模。
  - result 写明合作成果和进展:效率提升/成本节省/规模扩展/续约情况。
- **milestones 必须覆盖至 2025-2026 年最新事件**:
  - 至少 5 个关键里程碑,从成立到最近。
  - 每条都要有 impact 说明对公司发展的意义。
- **thesis(投资依据)必须结合企业自身真实情况**:
  - team_analysis 引用具体创始人经历和团队组合优势。
  - market_analysis 引用具体市场数据(TAM 来源、渗透率、增速)。
  - moat_analysis 7 维度的 evidence 必须引用该企业的具体产品/技术/客户/专利,不能泛泛而谈。
  - unit_economics_analysis 引用具体毛利率/客单价/回收周期。
  - bull_detailed 和 bear_detailed 的 evidence 列举具体数据点和事实。
  - competitors_detailed 至少 3 家,每家写清估值/市场份额/与本公司的核心差异。
- sub_segments 至少 3 条(大赛道切成可投资细分)。
- growth_drivers / barriers_to_entry 各至少 3 条。"""


class OllamaResearcher:
    """用本地 Ollama 运行的大模型做"任意公司结构化抽取"。"""

    name = "itjuzi"  # 路由目标: payload 填入 raw.itjuzi,复用现有分析模块
    provenance = "ollama/qwen3:8b"

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

        user_prompt = _PROMPT_TEMPLATE.format(company=company_name, stock_hint=stock_hint) + "\n/no_think"
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
