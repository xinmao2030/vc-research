# 故障排查 · FAQ

按现象反查。找不到的话欢迎提 issue: https://github.com/xinmao2030/vc-research/issues

---

## 安装 / 环境

### `command not found: vc-research`

**原因**: 虚拟环境没 activate,或 pip install 没跑。
```bash
source .venv/bin/activate   # 或用 uv
uv sync                     # 重装依赖
```

### `ModuleNotFoundError: No module named 'vc_research'`

**原因**: 没跑 `pip install -e .` 把项目装成可编辑包。
```bash
uv sync   # 或 pip install -e .
```

---

## analyze 命令

### `✗ 数据不足,无法生成研报`

**原因**: 输入的公司名不在 6 家标杆 fixture 中。
```bash
vc-research list-examples  # 看全部 6 家
```
或用 `--live` 启用本地 LLM 实时推断(见 [`live-mode-setup.md`](./live-mode-setup.md))。

### `✗ 估值数据不足: 无 ARR / GMV / TAM / 最近轮次任一估值信号`

**原因** (v0.1.14 新加的硬门): fixture 的 `thesis.growth` / `thesis.market` / `funding.rounds` 全为空。
**解决**: 检查 fixture JSON 至少有一条可用信号:
- `thesis.growth.arr_usd` 或 `gmv_usd`
- `thesis.market.tam_usd`
- `funding.rounds[*].post_money_valuation_usd`

### Fixture JSON 解析失败

**现象**: `json.decoder.JSONDecodeError`
**原因**: JSON 里多了逗号 / 中文标点 / 注释
**解决**: `python -m json.tool examples/fixtures/某.json` 能定位到哪行崩

### 研报金额显示还是 13 位数字

**原因**: v0.1.14 之前版本。升级到 v0.1.14+。
```bash
git pull && uv sync
```

---

## --llm (Claude 增强)

### `ANTHROPIC_API_KEY not set`

```bash
cp .env.example .env
# 编辑 .env,填入真实 key
export ANTHROPIC_API_KEY=sk-ant-xxx   # 或直接 export
```

### `⚠️ LLM 增强失败,已降级到 base 逻辑`

**原因**: 网络 / API 限流 / key 余额不足 — 属于预期降级。
**验证**: 研报依然会生成,只是 `thesis.moat / bull / bear` 走 rule-based 兜底。

---

## --live (Ollama)

### `connection refused http://localhost:11434`

**原因**: Ollama 服务没启动。
```bash
ollama serve  # 保持在一个终端里
```

### `model not found: qwen3:8b`

```bash
ollama pull qwen3:8b
```

详细配置见 [`live-mode-setup.md`](./live-mode-setup.md)。

### 冷启动 > 3 分钟

**原因**: 模型太大 + CPU 太慢。
**缓解**:
- 切 `qwen3:14b`(改 `data_sources/ollama_researcher.py` 的 `MODEL` 常量)
- 只对已 fixture 的公司跑,避免 `--live`

---

## PDF 渲染

### `⚠️ PDF 渲染失败: OSError cannot load library libgobject`

**原因**: macOS 缺 Pango/Cairo 系统库。
```bash
brew install pango cairo glib
```

### 落盘成了 .html 而非 .pdf

**预期行为**: 依赖缺失时自动降级,浏览器"打印为 PDF"即可。

---

## history 命令 (v0.1.12+)

### `⚠️ history 记录失败(不影响研报)`

**原因**: `~/.vc-research/` 权限问题或磁盘满。
```bash
ls -la ~/.vc-research/
df -h ~/
```
研报本身已生成,只是未入库。可重跑一次。

### history 表为空,但我明明生成过研报

**原因**: 使用了自定义 `VC_HISTORY_PATH` 环境变量,但查询时没带。
```bash
# 查自定义路径
VC_HISTORY_PATH=/my/path vc-research history
# 或 unset
unset VC_HISTORY_PATH
```

### 损坏行提示

**现象**: 历史文件有部分行解析失败,但不崩。
**解决**: `history.jsonl` 本来就容错,继续用即可。想清理:
```bash
# 备份后只留能解析的行
jq -c . ~/.vc-research/history.jsonl > /tmp/clean.jsonl 2>/dev/null && \
  mv /tmp/clean.jsonl ~/.vc-research/history.jsonl
```

---

## SEC EDGAR (Phase 2.1)

### SEC API 返回 403

**原因**: 请求头 User-Agent 不符合 SEC 要求(必须含真实邮箱)。
```bash
export SEC_EDGAR_UA="你的名字 your@email.com"
```

### 查中概股(蔚来/百济)时 404

**原因**: 公司名没在 `_COMPANY_TO_CIK` 映射里。
**扩展**: 打开 `src/vc_research/data_sources/sec_edgar_source.py`,加一行:
```python
"新公司名": "0001234567",   # 从 SEC EDGAR 搜 CIK
```

---

## 交叉验证工具

### `tools/cross_verify.py` 的 🔴 false positive

**现象**: 明明 fixture 和 Wiki 内容一致,仍报"不一致"。
**原因**: 中英别名表不覆盖新术语(如"电子价签" vs "Electronic shelf label")。
**解决**: 编辑 `tools/cross_verify.py` 的别名词典,或降级为 🟡 警告。

---

## 其他

- 实在找不到答案 → 提 issue,附 `uv run vc-research --version` + 错误栈 + 输入公司名
- 安全漏洞 → 见 [SECURITY.md](../SECURITY.md)
