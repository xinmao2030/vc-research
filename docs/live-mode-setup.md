# `--live` 模式配置指南

`vc-research analyze --live` 未命中 fixture 时用本地 Qwen3 (via Ollama) 实时推断任意公司。
首次冷启约 60-120 秒,结果缓存 30 天。

---

## 0. 为什么要用 `--live`

默认情况下,`vc-research` 只认 `examples/fixtures/*.json` 里的 6 家标杆公司。输入其他公司名会 exit 1。

`--live` 打开后:
- 未命中 fixture 时调用 `http://localhost:11434/api/chat`(Ollama)
- 本地 Qwen3:32B 推断产出一份简易 `itjuzi` 风格 payload
- 7 模块继续正常跑,研报右下角会标 "🤖 本研报由本地大模型实时推断生成"

**重要前提**: LLM 推断可能虚构或滞后,关键数字(估值/轮次/员工数/TAM)**必须交叉核实**。工具默认挂 `⚠️` 提示。

---

## 1. 安装 Ollama

### macOS

```bash
brew install ollama
```

或从 https://ollama.com/download 下载安装包。

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

## 2. 拉取模型

```bash
ollama pull qwen3:32b
```

- 模型体积约 20 GB
- 首次拉取 5-15 分钟(取决于网速)
- 后续冷启动仅读本地文件,<5 秒

> 💡 如果磁盘空间紧张,可以试 `qwen3:14b`(约 9 GB),准确度会降一档。

---

## 3. 启动 Ollama 服务

```bash
ollama serve
```

默认监听 `http://localhost:11434`。保持这个终端开着,或把 `ollama serve &` 放到你的 `~/.zshrc`。

**验证**:
```bash
curl http://localhost:11434/api/tags
# 应该返回 {"models": [{"name": "qwen3:32b", ...}]}
```

---

## 4. 跑 `--live`

```bash
vc-research analyze "某家非标杆公司" --live -o 某.md
```

**预期**:
```
🤖 Live 模式:未命中 fixtures 将用本地 Qwen3 推断 (首次约 60-120 秒,结果会缓存 30 天)
────── 分析: 某家非标杆公司 ──────
✓ 数据源命中: Ollama · qwen3:32b (LLM 推断, 30 天缓存)
✓ 模块 1: 企业画像
...
```

首次对同一家公司推断约 **60-120 秒**(看模型大小和 CPU)。第二次跑同一家只读缓存,<2 秒。

---

## 5. 缓存管理

缓存位置: `~/.vc-research/llm_cache/<company>.json`

| 操作 | 命令 |
|---|---|
| 查看已缓存公司 | `ls ~/.vc-research/llm_cache/` |
| 清单一家 | `rm ~/.vc-research/llm_cache/某家公司.json` |
| 清全部 | `rm -rf ~/.vc-research/llm_cache/` |
| 调整 TTL (默认 30 天) | `export VC_LLM_CACHE_TTL_DAYS=7` |

---

## 6. 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `connection refused http://localhost:11434` | Ollama 没启 | `ollama serve` |
| `model not found: qwen3:32b` | 模型没拉 | `ollama pull qwen3:32b` |
| 推断 > 5 分钟还没出 | 模型太大 / CPU 太慢 | 切 `qwen3:14b` 或小模型 |
| 推断出的估值明显失真 | LLM 幻觉 | 建议仍走 fixture 补录,或等 Phase 2 真实 API |
| 想用其他模型 (llama3 等) | 需改代码 | 见 `src/vc_research/data_sources/ollama_researcher.py` `MODEL = ...` |

---

## 7. 何时**不**用 `--live`

- 需要权威数据做投资决策 — 先建 fixture,交叉验证 3 家以上权威源
- 追求可重复性 — LLM 输出不稳定,同一 prompt 可能产生不同结果
- 离线环境 — Ollama 也需要本地模型文件

`--live` 是**研究起点**,不是终点。查完后务必落到 fixture 里并做 `tools/cross_verify.py` 校验。
