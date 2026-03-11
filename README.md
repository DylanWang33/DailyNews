# DailyNews

每日新闻抓取 → 翻译 → AI 摘要 → Obsidian 笔记与每日简报，并支持 Git 同步。

## 目录结构

```
DailyNewsRepo/
├── config.yaml     # 可选：obsidian_base 指定 Obsidian 库路径，新闻/简报写到此库
├── scripts/        # 所有程序
├── sources/        # RSS 源（rss.txt 或 rss.yaml）
├── news/           # 按日期生成的新闻（若未配 obsidian_base 则写在本目录）
├── entities/       # 实体库
├── events/         # 事件
├── briefs/         # 每日简报
├── cache/          # 去重缓存
├── logs/           # 运行日志（run.sh 的输出，供快捷指令排错）
└── run.sh          # 一键执行（推荐给快捷指令用）
```

## 数据流

```
sources/rss.txt 或 rss.yaml
        ↓
fetch_news.py
        ↓
抓文章（通用 + Bloomberg 专用）
        ↓
翻译 → AI 摘要
        ↓
News/YYYY-MM-DD → Briefs/YYYY-MM-DD.md
        ↓
与 Obsidian 双向链接：新闻 → 翻译 → AI 分析 → 知识图谱
        ↓
git_sync 推送
```

## 执行方式

### 方式一：Mac 快捷指令（推荐）

在快捷指令里用**一条命令**即可（无需先 `cd`，脚本会自动切到项目根）：

```bash
/Users/kryss/DailyNewsRepo/venv/bin/python /Users/kryss/DailyNewsRepo/scripts/fetch_news.py
```

或使用封装脚本（推荐，会写日志便于排错）：

```bash
/Users/kryss/DailyNewsRepo/run.sh
```

若快捷指令里执行后「没任何效果」：快捷指令没有终端窗口，脚本会把**所有输出写入日志**。请打开下面文件查看是否执行成功、是否有报错：

- **日志路径**：`/Users/kryss/DailyNewsRepo/logs/run.log`

可把「打开文件」加入快捷指令，在「运行脚本」之后打开 `logs/run.log`。若仍不执行，可在「运行 Shell 脚本」里改用显式 bash：`/bin/bash /Users/kryss/DailyNewsRepo/run.sh`

### 方式二：终端

```bash
cd /Users/kryss/DailyNewsRepo
./venv/bin/python scripts/fetch_news.py
# 或
./run.sh
```

### 关联到 Obsidian 仓库

新闻和简报默认写在 DailyNewsRepo 内。若要写入你的 Obsidian 库（如 `~/仓库/Dylan/DailyNews/`），在**项目根目录**新建或编辑 `config.yaml`：

```yaml
obsidian_base: /Users/kryss/仓库/Dylan/DailyNews
```

之后运行脚本，会在此库下生成 `news/YYYY-MM-DD/*.md` 和 `briefs/YYYY-MM-DD.md`，即可在 Obsidian 中做双向链接。

也可用环境变量：`DAILY_NEWS_OBSIDIAN_BASE=/path/to/vault`（优先级低于 config.yaml）。

- **每轮篇数上限**：在 `config.yaml` 中可设置 `max_articles_per_run: 30`（默认 30），达到后自动结束并生成简报、推送，无需手动停止。
- **文件名**：笔记文件名使用**中文**（原标题翻译）；正文开头会保留 **原标题 / Original**，便于查看英文或原文标题。
- **去重**：按标题 + URL 双重去重；「Subscribe to read」等付费墙占位标题会自动跳过。

## RSS 源

- **sources/rss.txt**：存在时优先使用。每行一个 URL，或 `显示名|URL`，`#` 开头为注释。
- **sources/rss.yaml**：当 rss.txt 不存在时使用，格式为 `- name: xxx\n  url: https://...`。

已在 rss.yaml / rss.txt 中预置多路源（Reuters、Bloomberg、BBC、FT、CNN、NPR、Guardian、CNBC、TechCrunch、HN 等），可按需增删。

## 常见问题 / 排错

- **`Permission denied`（logs/run.log 或 news/ 下文件）**  
  若曾用 `sudo` 运行过，目录可能属主为 root。在项目根执行：
  ```bash
  cd /Users/kryss/DailyNewsRepo
  sudo chown -R $(whoami) logs news briefs cache entities
  chmod -R u+rwX logs news briefs cache entities
  ```
- **NLTK tokenizers are missing**  
  首次运行会自动下载；若失败，可手动执行：
  ```bash
  ./venv/bin/python -c "import nltk; nltk.download('punkt_tab'); nltk.download('punkt')"
  ```

## 安全与优化

- 仅允许 `http`/`https` 请求，禁止 `file://` 等。
- 请求超时与正文长度限制，防止卡死与内存滥用。
- 实体/文件名与写入路径做安全处理，防止路径穿越。
- Git 在仓库根执行，无 shell 拼接，失败时退出码非 0 便于排错。
