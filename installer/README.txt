╔══════════════════════════════════════════════════════════╗
║       VC Research — 创投企业投资分析系统                ║
║   输入企业名 → 输出 7 层结构化投研报告                 ║
╚══════════════════════════════════════════════════════════╝

安装方法:
  双击「安装 VC Research.command」即可。

安装内容:
  1. Xcode Command Line Tools (编译工具)
  2. Homebrew (macOS 包管理器)
  3. Python 3.12 (运行环境)
  4. pango/cairo (PDF 渲染库)
  5. VC Research 主程序 + 虚拟环境
  6. Ollama (本地 AI 推理引擎)
  7. Qwen3:8b 模型 (约 5GB,首次需联网)

安装完成后:
  source ~/vc-research/activate.sh
  vc-research analyze "影石创新"
  python ~/vc-research/web/dashboard.py

系统要求:
  macOS 12 (Monterey) 或更高版本
  Apple Silicon (M1/M2/M3/M4) 或 Intel Mac
  约 8GB 可用磁盘空间 (含 AI 模型)
  安装过程需联网
