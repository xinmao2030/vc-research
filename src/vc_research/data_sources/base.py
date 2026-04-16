"""DataSource 抽象协议 — Phase 2 接入真实 API 的统一入口.

设计目标:
    - 每个数据源 (fixtures / IT桔子 / Crunchbase / 企查查) 都实现同一协议
    - DataAggregator 按优先级顺序调用各 source,把返回结果合并进 RawCompanyData
    - 新增数据源时只加一个 class,不动 aggregator
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DataSource(Protocol):
    """通用数据源协议.

    实现方返回一个 dict (与 fixtures JSON 结构同构) 或 None (未命中).
    dict 需要能 round-trip 到 RawCompanyData 的某个字段 (itjuzi/crunchbase/qichacha).
    """

    name: str

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        """查询企业数据,命中返回 dict,未命中返回 None.

        约定:
            - 不得抛异常代替 "未命中" (正常路径不靠 except)
            - API 认证失败/限流/网络异常 才抛异常 (由 aggregator 决定是否降级)
        """
        ...
