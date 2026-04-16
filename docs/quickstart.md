# 快速开始 · vc-research

> **目标读者**: 完全没用过本工具的零基础投资者。10 分钟内产出第一份研报。

---

## 0. 你需要的前置条件

- macOS 或 Linux(Windows 用 WSL)
- Python 3.10 及以上 — `python3 --version` 检查
- 5 分钟

**不需要**: 编程经验 / API key / 付费账号(使用内置 fixtures)

---

## 1. 安装(约 2 分钟)

```bash
cd ~ && git clone <repo> vc-research && cd vc-research
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

> 🍎 macOS 如果后面要导出 PDF,顺手装一下 weasyprint 的系统依赖:
> `brew install pango cairo glib`
> 不装也没关系,研报会自动降级成 HTML。

---

## 2. 第一份研报(30 秒)

```bash
vc-research list-examples
```

你会看到六家 2025 IPO 标杆案例: **影石创新 / 澜起科技 / 银诺医药 / 比贝特医药 / 汉朔科技 / 强一股份**。

任选一家生成研报:

```bash
vc-research analyze "影石创新" -o 影石.md
```

**预期输出**(约 1 秒):

```
────────────── 分析: 影石创新 ──────────────
⚠️  免责声明: 本工具产出仅供学习研究,不构成投资建议。
🎮 闯关进度: 🏢⬜ 💰🔒 🎯🔒 🌊🔒 💎🔒 ⚠️🔒 🎯🔒 (0/7)
✓ 数据源命中: fixtures
✓ 模块 1: 企业画像
   🔓 解锁新模块: 💰 融资轨迹 — 看钱从哪来,估值怎么变
✓ 模块 2: 融资轨迹 (6 轮)
   🔓 解锁新模块: 🎯 投资依据 — ...
...
────────── ✓ 研报生成完成 ──────────
🎮 闯关进度: 🏢✅ 💰✅ 🎯✅ 🌊✅ 💎✅ ⚠️✅ 🎯✅ (7/7)
📄 Markdown: 影石.md
```

用 VS Code / Typora / 其他 Markdown 阅读器打开 `影石.md`。

---

## 3. 研报怎么读(按章节)

| 章节 | 零基础提问 | 对应章节 |
|------|-----------|----------|
| 🏢 企业画像 | "这家公司是谁?" | 模块 1 |
| 💰 融资轨迹 | "融了多少轮?当前值多少钱?" | 模块 2 |
| 🎯 投资依据 | "凭什么值得投?" | 模块 3 |
| 🌊 产业趋势 | "赛道是热是冷?" | 模块 4 |
| 💎 估值分析 | "当前估值合理吗?" | 模块 5 |
| ⚠️ 风险矩阵 | "会踩什么坑?" | 模块 6 |
| 🎯 投资建议 | "投还是不投?" | 模块 7 |

遇到不懂的术语(TAM/LTV/MOAT/Runway...),打开 [glossary.md](./glossary.md) 查询。

---

## 4. 进阶用法

### 导出 PDF

```bash
vc-research analyze "比贝特医药" -o 比贝特.md --pdf
```

系统依赖缺失会自动降级到 `.html`,浏览器"打印为 PDF"即可。

### 调用 Claude LLM 增强(可选,需 API key)

```bash
cp .env.example .env   # 编辑填入 ANTHROPIC_API_KEY
vc-research analyze "银诺医药" -o 银诺.md --llm
```

没有 key 也没关系,所有分析的 base 逻辑都已实现。

### 启动 Web Dashboard

```bash
python web/dashboard.py
# 浏览器访问 http://localhost:8765
```

---

## 5. 常见错误 & 解决

| 现象 | 原因 | 解决 |
|------|------|------|
| `company: command not found` | 没 activate venv | `source .venv/bin/activate` |
| `未在 fixtures 中找到 xxx` | 不在 6 家标杆中 | 跑 `vc-research list-examples` 看全部 6 家;Phase 2 会接入真实数据源 |
| `--pdf` 报错 libgobject | 缺 pango/cairo | `brew install pango cairo glib` |
| `ANTHROPIC_API_KEY` 未设置 | 用了 `--llm` | 去掉 `--llm` 或补 `.env` |
| 研报金额看不懂(13 位数字) | 原始精度数据 | 后续版本会显示 `$180B` |

---

## 6. 下一步建议的学习路径

1. ✅ 现在: 生成 6 家标杆研报,对比看 3 大赛道(消费电子 / 医药 / 半导体硬件)
2. 🕒 用 `vc-research history` 查看你已生成的全部研报(裁决/估值/公允区间一表对比)
3. 📖 读 [glossary.md](./glossary.md) — 理解核心术语
4. 🏗️ 读 [architecture.md](./architecture.md) — 看工具如何工作
5. 🔧 贡献 fixtures: 写一份你熟悉的公司的 JSON,放到 `examples/fixtures/`

**核心心法**:
> 研报不是结论,是思考框架。每看一份,在大脑里多走一次"钱从哪来 → 值多少 → 风险在哪"的神经通路。
