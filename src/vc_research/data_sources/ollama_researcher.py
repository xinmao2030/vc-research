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

_PROMPT_TEMPLATE = """你是一位资深创投分析师。请为公司 "{company}" 产出一份结构化 JSON 研报。

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
  "founders": [
    {{"name": "姓名", "title": "CEO", "background": "背景一句话", "equity_pct": 0.15}}
  ],
  "rounds": [
    {{"stage": "angel", "announce_date": "YYYY-MM-DD", "amount_usd": 2000000,
      "post_money_valuation_usd": 10000000, "lead_investors": ["机构"], "notes": "备注"}},
    {{"stage": "a", "announce_date": "YYYY-MM-DD", "amount_usd": 10000000,
      "post_money_valuation_usd": 50000000, "lead_investors": ["机构"], "notes": "备注"}}
  ],
  "thesis": {{
    "team_score": 7,
    "team_notes": "团队点评",
    "market": {{"tam_usd": 10000000000, "sam_usd": 2000000000, "som_usd": 200000000, "growth_rate": 0.2}},
    "moat": "护城河描述",
    "unit_economics": {{"gross_margin": 0.5, "payback_months": 18, "ltv_cac_ratio": 3.0}},
    "growth": {{"arr_usd": null, "yoy_growth": 0.5, "retention_m12": null}},
    "competitors": ["竞品1", "竞品2", "竞品3"],
    "bull": ["看多1", "看多2", "看多3"],
    "bear": ["看空1", "看空2", "看空3"]
  }},
  "industry_data": {{
    "funding_total_12m_usd": 5000000000,
    "deal_count_12m": 100,
    "gartner_phase": "成熟期 / 复苏期 / 幻灭期 / 炒作期 / 萌芽期 之一",
    "policy_tailwinds": ["利好1", "利好2"],
    "policy_headwinds": ["利空1"],
    "exit_window": "退出窗口描述",
    "hot_keywords": ["热词1", "热词2", "热词3"]
  }},
  "financials": {{"burn_rate_usd_monthly": 500000, "cash_usd": 8000000}},
  "extra_risks": [
    {{"category": "监管", "description": "...", "level": "medium", "mitigation": "..."}},
    {{"category": "市场", "description": "...", "level": "medium", "mitigation": "..."}}
  ]
}}

硬性要求:所有字段必须有合理值。所有金额统一用美元 (数字,不带单位)。"""


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
                "options": {"temperature": 0.35, "num_predict": 4096},
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
