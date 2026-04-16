"""类比教学 — 把 VC 专业术语翻译成零基础读者能感知的日常概念.

设计原则 (参考 project_capital_as_energy.md):
- 资金 = 能量流 (流动态→固化态→释放态)
- 融资轮次 = 游戏升级 (每关解锁更大场景)
- 股权稀释 = 蛋糕切分 (蛋糕做大了,每片可能反而更值钱)
- 烧钱速度 = 血条消耗 (跑道=剩余回合)
- 估值倍数 = 餐厅翻台率 (同赛道餐厅对比)
"""

from __future__ import annotations


_ANALOGIES: dict[str, dict[str, str]] = {
    "funding_round": {
        "concept": "融资轮次",
        "analogy": "游戏升级关卡",
        "explain": (
            "每一轮融资就像游戏里打通一关:天使→A→B→C→D→Pre-IPO。"
            "打到哪一关,大致能判断公司的成熟度。"
            "小白要记住:**轮次越后,风险越小,但回报倍数也越小。**"
        ),
    },
    "dilution": {
        "concept": "股权稀释",
        "analogy": "蛋糕切分",
        "explain": (
            "公司是一块蛋糕,融资相当于把蛋糕做大,但要切一小块给新投资人。"
            "创始人手里的那片比例变小了,但整块蛋糕更值钱。"
            "**稀释本身不可怕,蛋糕没变大才可怕。**"
        ),
    },
    "burn_rate": {
        "concept": "烧钱速度",
        "analogy": "血条消耗",
        "explain": (
            "每个月公司亏多少钱就是烧钱速度。"
            "现金 ÷ 月烧钱 = 跑道(还能撑几个月)。"
            "**跑道 < 6 月 = 濒死,12 月 = 警戒,18 月+ = 安全。**"
        ),
    },
    "tam_sam_som": {
        "concept": "TAM / SAM / SOM",
        "analogy": "三层海洋",
        "explain": (
            "TAM = 整个海洋(理论最大市场);"
            "SAM = 你能游到的海域(产品/地域可覆盖);"
            "SOM = 你能抓到的鱼(未来 3-5 年现实份额)。"
            "**投资人最看 SOM,因为那是真金白银的天花板。**"
        ),
    },
    "moat": {
        "concept": "护城河",
        "analogy": "城堡外的水沟",
        "explain": (
            "护城河就是让对手难以进攻的壁垒:"
            "① 网络效应(越多人用越值钱,如微信);"
            "② 规模效应(量大成本低,如京东);"
            "③ 技术专利(如台积电先进制程);"
            "④ 品牌心智(如可口可乐);"
            "⑤ 数据/切换成本(如 SAP)。"
            "**没护城河的公司早晚被价格战拖死。**"
        ),
    },
    "ltv_cac": {
        "concept": "LTV/CAC",
        "analogy": "渔夫 ROI",
        "explain": (
            "CAC = 买鱼饵的钱(获客成本);LTV = 钓上来的鱼能卖多少(客户生命周期价值)。"
            "**健康比例 >= 3 倍**,否则越做越亏。"
            "比例 < 1 = 赔本赚吆喝,必须尽快改善单位经济学。"
        ),
    },
    "valuation_methods": {
        "concept": "估值方法",
        "analogy": "房子评估",
        "explain": (
            "给公司定价就像给一套房定价:"
            "① 可比公司法 = 隔壁小区同户型挂牌价;"
            "② 可比交易法 = 最近成交价;"
            "③ DCF = 未来能收多少租金折回现在;"
            "④ VC 逆推 = 退出时能卖多少倒推今天入场价。"
            "**至少两种方法交叉验证,才不容易被高估迷惑。**"
        ),
    },
    "liquidation_preference": {
        "concept": "优先清算权",
        "analogy": "救生艇优先级",
        "explain": (
            "公司破产/被贱卖时,谁先上救生艇?"
            "1x non-participating = 投资人先拿回本金,剩下大家按股比分;"
            "2x participating = 投资人先拿 2 倍本金,再一起分 — 对创始人很吃亏。"
            "**创始人谈判首要目标:压到 1x non-participating。**"
        ),
    },
}


def explain_with_analogy(concept_key: str) -> str:
    """返回一段类比教学文本."""
    data = _ANALOGIES.get(concept_key)
    if not data:
        return f"(暂无 {concept_key} 的类比教学)"
    return (
        f"💡 **{data['concept']}** ≈ 《{data['analogy']}》\n\n{data['explain']}"
    )


def list_concepts() -> list[str]:
    return list(_ANALOGIES.keys())
