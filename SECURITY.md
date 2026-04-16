# Security Policy

## Supported Versions

当前仅对 `main` 最新 tag 提供安全修复。

| 版本 | 状态 |
|---|---|
| 0.1.x (最新) | ✅ 接受漏洞报告 |
| < 0.1.12 | ❌ 不再维护,请升级 |

## 报告漏洞

如果发现安全问题**请不要直接提 public Issue**,而是:

1. 通过 GitHub 的 "Report a vulnerability" 功能私下提交:
   https://github.com/xinmao2030/vc-research/security/advisories/new
2. 或发邮件至 `xinmao2030@gmail.com`,标题前缀 `[vc-research security]`

报告请包含:
- 漏洞描述 + 复现步骤
- 影响版本范围
- 受影响的文件/模块 (file:line 级定位最佳)
- 建议的修复方向 (可选)

## 响应时间

- 48 小时内确认收到
- 7 天内给出评估 + 修复计划
- 高危漏洞 14 天内发布补丁

## 常见敏感边界

- **本地文件**: `~/.vc-research/` 下的 `history.jsonl` / `llm_cache/` 仅存元数据,不含原始凭证
- **API key**: `ANTHROPIC_API_KEY` 仅从 `.env` / 环境变量读取,不落盘
- **HTML 消毒**: `src/vc_research/report/renderer.py` 的正则白名单是兜底,
  Phase 2+ 会换成 `nh3` 严格解析

## 致谢

感谢所有为 vc-research 安全做贡献的研究者。
