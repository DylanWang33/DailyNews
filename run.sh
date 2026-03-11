#!/bin/bash
# 一键执行：抓取 → 简报 → Git 推送（供 Mac 快捷指令调用）
# 快捷指令没有终端窗口，所有输出会写入本仓库 logs/run.log，请打开该文件查看。

REPO="/Users/kryss/DailyNewsRepo"
LOG="${REPO}/logs/run.log"
mkdir -p "${REPO}/logs"
touch "$LOG" 2>/dev/null
# 仅在「无终端」时重定向到日志（快捷指令无 TTY）；在终端运行则直接输出到屏幕
if [ ! -t 1 ] && [ -w "$LOG" ]; then
  exec >> "$LOG" 2>&1
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始 ====="
cd "$REPO" || { echo "cd 失败"; exit 1; }

if [[ ! -x "${REPO}/venv/bin/python" ]]; then
  echo "错误: 未找到 venv，请先在终端执行: cd $REPO && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

# 将阅读样式同步到 Obsidian 库（若已配置 obsidian_base），便于排版生效
"${REPO}/venv/bin/python" "${REPO}/scripts/install_obsidian_css.py" 2>/dev/null || true

"${REPO}/venv/bin/python" "${REPO}/scripts/fetch_news.py"
exit $?
