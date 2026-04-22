# VC Research — 创投企业投资分析系统

> 输入企业名称，自动输出结构化创投研报。
> 让零基础投资者也能看懂一家初创公司的"钱从哪来、值多少、风险在哪"。
>
> **面向一级市场**：VC / 天使 / 战投评估未上市（Pre-IPO）企业的投资决策支持工具，不提供二级市场股票买卖建议。

## 🎯 项目目标

为创投小白（VC/PE 新手、天使投资个人、行业研究者）打造一个 **输入企业名 → 输出投研报告** 的分析助手。继承 `portfolio-manager` / `crypto-trader` 的教育哲学：**改造零基础投资者大脑，形成投资自觉**。

## 📐 七层分析框架

| # | 模块 | 回答的核心问题 |
|---|------|----------------|
| 1 | 企业画像 (Company Profile) | 这家公司是谁？做什么？谁在做？ |
| 2 | 融资轨迹 (Funding Rounds) | 融过多少？什么估值？谁投的？稀释到哪了？ |
| 3 | 投资依据 (Investment Thesis) | 凭什么值得投？团队/市场/技术/单位经济学 |
| 4 | 产业趋势 (Industry Trends) | 这个赛道现在热吗？冷吗？处于哪个周期？ |
| 5 | 估值分析 (Valuation) | 现在这个估值合理吗？几种方法交叉验证 |
| 6 | 风险矩阵 (Risk Matrix) | 会踩什么坑？现金跑道够吗？ |
| 7 | 投资建议 (Recommendation) | 投 or 不投？定价区间？条款建议？ |

## 🧠 教育属性（Education Layer）

沿用 `crypto-trader` 的 **闯关式学习**：
- 每个模块必须"解锁"才能看下一模块（强化认知路径）
- **估值滑块**：拖动 TAM/增长率/折现率，直观感受估值敏感性
- **类比教学**：融资轮次 = 游戏升级；股权稀释 = 蛋糕切分；烧钱速度 = 血条消耗

## 🏗️ 技术架构

```
输入: 企业名称 (e.g. "影石创新")
  │
  ▼
┌─────────────────────────────────────┐
│ 数据采集层 (data_sources/)          │
│  • 国内: 企查查 / IT桔子 / 36氪     │
│  • 海外: Crunchbase / PitchBook     │
│  • 新闻/专利/招聘 (补充信号)         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 分析层 (modules/)                    │
│  ① 画像  ② 融资  ③ 依据  ④ 趋势     │
│  ⑤ 估值  ⑥ 风险  ⑦ 建议              │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ LLM 推理层 (llm/)                    │
│  • Claude Opus 4.6 生成投资逻辑     │
│  • 向量检索对标公司                  │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 输出层 (report/)                     │
│  • Markdown → PDF 研报              │
│  • Next.js 交互式 Dashboard         │
└─────────────────────────────────────┘
```

## 🚀 发展路径 (Roadmap)

- **Phase 1** (已完成): 七层分析骨架 + 教育层 + CLI + Markdown/PDF 输出
- **Phase 2.1** (已完成 v0.1.10-alpha): SEC EDGAR + HKEX symbology + 并行交叉验证工具
- **Phase 2.2** (进行中): 标杆案例切换至 6 家 2025 新上市代表 — 影石创新 / 澜起科技 / 银诺医药 / 必贝特医药 / 汉朔科技 / 强一股份(v0.1.11)
- **Phase 3**: Claude 4.6 深度推理 + 向量检索对标
- **Phase 4**: Next.js Web Dashboard + 个性化(风险偏好 / 赛道标签匹配)

## 📂 目录结构

```
vc-research/
├── src/vc_research/
│   ├── cli.py                # CLI 入口: vc-research analyze "影石创新"
│   ├── data_sources/         # 数据采集 (国内+海外)
│   ├── modules/              # 7 大分析模块
│   ├── llm/                  # Claude 推理封装
│   ├── report/               # 研报模板 + 渲染
│   ├── db/                   # PostgreSQL schema
│   └── education/            # 闯关/类比教学
├── examples/                 # 标杆案例研报
├── tests/
└── web/                      # Next.js Dashboard (Phase 4)
```

## 📚 标杆案例(v0.1.11)

覆盖 2024-2026 年 **6 家具代表性的 IPO / Pre-IPO 公司**,刻意选取不同行业 + 不同上市地 + 不同估值阶段以训练多角度判断。

> **注**: 标杆企业均已 IPO,作为"**从 VC 轮到上市的成功轨迹**"教学样本——帮助用户理解 VC 在企业未上市前如何评估与参投,而非推荐现价买卖。

| 公司 | 赛道 | 上市 | 代码 | 裁决 | 看点 |
|------|------|------|------|------|------|
| 影石创新 (Insta360) | 消费电子 · 全景相机 | 2025-06 科创板 | 688775.SH | 观望 | 全球全景相机份额 67%;GoPro 337 调查胜诉 |
| 澜起科技 (Montage) | 半导体 · 内存接口芯片 | 2019-07 科创板 + 2026-01 A+H | 688008.SH / 2827.HK | 观望 | DDR5/CXL 全球 Top 3;DRAM 周期依赖 |
| 银诺医药 (Innogen) | 医药 · GLP-1 长效 | 2025-08 港股 18A | 2591.HK | 推荐 | 依苏帕格鲁肽α 半衰期 204h;首日 +206% |
| 必贝特医药 (BeBetter) | 医药 · HDAC 小分子 | 2025-10 科创板 | 688759.SH | 推荐 | 双靶点 BEBT-908;Pre-IPO 估值 38 亿元 |
| 汉朔科技 (Hanshow) | 硬件 · 电子价签 ESL | 2025-03 创业板 | 301275.SZ | 回避 | 沃尔玛/Carrefour 客户;94% 海外收入 |
| 强一股份 (Maxone) | 半导体 · MEMS 探针卡 | 2025-12 科创板 | 688809.SH | 回避 | 晶圆测试国产替代;Yole 全球第 9 |

每家 fixture 都已通过 `tools/cross_verify.py` 并行交叉校核多源公开信息。研报样本见 `examples/reports/*.md`。

## 🏃 快速开始

### 一键安装 (macOS)

```bash
# 方式 1: 克隆后本地运行
git clone https://github.com/xinmao2030/vc-research.git
bash vc-research/install.sh

# 方式 2: 已有项目目录
cd ~/vc-research
bash install.sh
```

安装脚本会自动完成：Xcode CLT → Homebrew → Python 3.10+ → 系统依赖 → 虚拟环境 → Ollama + Qwen3 模型。全程引导，无需手动配置。

### 安装完成后

```bash
# 激活环境
source ~/vc-research/activate.sh

# 分析标杆企业 (秒出,无需网络)
vc-research analyze "影石创新" -o report.md
vc-research list-examples

# 搜索任意企业 (需 Ollama 运行)
vc-research analyze "字节跳动" --live -o report.md

# Web Dashboard (浏览器自动打开 localhost:8800)
python ~/vc-research/web/dashboard.py

# 生成 PDF 研报
vc-research analyze "银诺医药" --pdf
```

### 手动安装

<details>
<summary>如果一键脚本不适用,点击展开手动步骤</summary>

```bash
# 1. 系统依赖 (PDF 渲染用,可选)
brew install pango cairo glib gdk-pixbuf libffi

# 2. Python 环境
cd ~/vc-research
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 3. Ollama (任意企业分析用,可选)
brew install ollama
ollama serve &
ollama pull qwen3:8b

# 4. 验证
vc-research analyze "影石创新" -o report.md
```

**Linux** (Debian/Ubuntu):
```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libffi-dev
```
</details>

## 🔑 环境变量

```bash
cp .env.example .env
# 编辑填入 ANTHROPIC_API_KEY (使用 --llm 时必需)
```

| 变量 | 用途 | 默认值 | 必须? |
|------|------|--------|-------|
| `ANTHROPIC_API_KEY` | Claude 推理增强 | — | 仅 `--llm` 时 |
| `OLLAMA_MODEL` | 本地模型切换 | `qwen3:8b` | 否 |
| `OLLAMA_URL` | Ollama 服务地址 | `http://localhost:11434` | 否 |

## 🧪 运行测试

```bash
source ~/vc-research/activate.sh
pytest tests/ -v
```

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| `--pdf` 报 `libgobject` 缺失 | `brew install pango cairo glib gdk-pixbuf libffi` |
| `ANTHROPIC_API_KEY` 未设置 | 去掉 `--llm` 标志或在 `.env` 中设置 |
| `--live` 报连接超时 | 确认 Ollama 运行中: `ollama serve &` |
| 搜索企业很慢 (>2分钟) | 首次推理需模型冷启动,后续有 30 天缓存 |
| `externally-managed-environment` | 使用虚拟环境: `source activate.sh` |
| Apple Silicon 装包失败 | 确保用 Homebrew 版 Python,非系统自带 |

## 📜 设计原则

1. **连接+流动**: 企业信息→融资轨迹→估值→建议，形成闭环认知
2. **神经可塑性**: 每份研报强化一次"投前思考框架"
3. **刻意练习**: 标杆案例库让用户反复对标，形成直觉
