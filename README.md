# DailyNews

每日新闻抓取 → 翻译 → AI 摘要 → Obsidian 笔记与每日简报，并支持 Git 同步。

## 目录结构

```
DailyNewsRepo/
├── config.yaml     # 可选：obsidian_base 指定 Obsidian 库路径，新闻/简报写到此库
├── scripts/        # 所有程序
├── sources/        # RSS 源（仅 rss.yaml）
├── news/           # 按日期生成的新闻（若未配 obsidian_base 则写在本目录）
├── entities/       # 实体库
├── events/         # 事件
├── briefs/         # 每日简报（关键词过滤后的 AI 摘要汇总，始终生成）
├── 今日热点/        # 今日热点/日期/分类（如新闻）/具体网站.md，来自 config hot_categories
├── rss/             # feeds-all.opml，可用 scripts/opml_to_yaml.py 生成 sources/rss.yaml
├── obsidian-snippets/  # 可选：复制到 Obsidian 库 .obsidian/snippets 并启用以优化阅读排版
├── cache/          # 去重缓存 + fetch_cursor.json（断点续抓位置）
├── logs/           # 运行日志（run.sh 的输出，供快捷指令排错）
└── run.sh          # 一键执行（推荐给快捷指令用）
```

## 数据流

```
sources/rss.yaml
        ↓
fetch_news.py
        ↓
今日热点（按分类+源）→ 今日热点/YYYY-MM-DD/分类（如新闻）/具体网站.md；每源最多 15 条，英文标题译中并备注原标题
        ↓
News：中文源优先，再英文源；断点续抓（从上次位置继续，全部轮询完后从头并去重）
        ↓
抓文章 → 关键词过滤（config 中 keywords）→ 翻译 → AI 摘要
        ↓
News/YYYY-MM-DD → briefs/YYYY-MM-DD.md（AI 简报总结，无匹配时也会生成说明）
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

- **每轮篇数上限**：`max_articles_per_run: 30`，达到后自动结束。
- **捕获速度**：`fetch_delay_min` / `fetch_delay_max`（秒）控制请求间隔，默认 0.2～0.5，可调小以加快。
- **文件名**：笔记文件名使用**中文**；正文开头保留 **原标题 / Original**。
- **去重**：按标题 + URL 双重去重；「Subscribe to read」等占位标题自动跳过。
- **关键词过滤**：在 `config.yaml` 中配置 `keywords` 列表（支持中文）。只保留标题或正文（含翻译）命中任一关键词的新闻。若只想要「油价」相关，可只保留 `油价`，其余注释或删除。外文站若无命中，会用中文关键词的英文译词再匹配原文。
- **今日热点**：结构为 `今日热点/日期/分类标题/具体网站.md`（如 `今日热点/2026-03-12/新闻/联合早报.md`）。分类与源在 `config.yaml` 的 `hot_categories` 中配置（新闻、科技、知识、娱乐、财经、生活、外国媒体等），每源最多 `max_hot_items` 条（默认 15）；英文标题会自动译成中文并备注「原标题」。
- **News 顺序与断点续抓**：`rss.yaml` 中**中文源**（`lang: zh`）优先抓取，再抓英文源。每次运行从上次结束位置继续（`cache/fetch_cursor.json`），全部 URL 轮询完后自动从头开始，依赖去重避免重复。
- **Briefs**：关键词过滤后的新闻会在此做 AI 简报总结；即使当日无匹配新闻也会生成一篇说明文件。
- **Obsidian 阅读样式**：见下节「Obsidian 排版」。

## Obsidian 排版（新闻/简报字体与版式）

CSS 片段必须放在**【当前打开的库】** 的 `vault/.obsidian/snippets` 下（即库根目录下的 `.obsidian/snippets`），Obsidian 才能识别。

**若在「代码片段」文件夹里没看到任何 CSS**：说明该库下还没有片段文件，需要先复制进去。

**步骤 1：把片段复制到库内**

在终端执行（片段必须放在**库根** `.obsidian/snippets`，即 `config.yaml` 里 `obsidian_vault_root` 或库根路径，不是 obsidian_base 子目录）：

```bash
# 创建片段目录（库根下 .obsidian/snippets）
mkdir -p "/Users/kryss/仓库/Dylan/.obsidian/snippets"

# 复制 CSS 到该库
cp /Users/kryss/DailyNewsRepo/obsidian-snippets/daily-news-reader.css "/Users/kryss/仓库/Dylan/.obsidian/snippets/daily-news-reader.css"
```

或先安装再复制（会按 config 里的 obsidian_base 自动选路径）：

```bash
cd /Users/kryss/DailyNewsRepo
./venv/bin/python scripts/install_obsidian_css.py
```

**步骤 2：在 Obsidian 里启用**

1. 打开该库（Dylan/DailyNews）。
2. **设置** → **外观** → **CSS 代码片段**。
3. 点 **「重新加载」**，列表中应出现 **daily-news-reader**。
4. 打开 **daily-news-reader** 右侧开关。
5. 看笔记时切到**阅读模式**（右上角书本图标）查看排版效果。

## RSS 源

- **sources/rss.yaml**：主 RSS 源配置，与 **rss/feeds-all.opml** 内容一致。可用 `./venv/bin/python scripts/opml_to_yaml.py` 从 OPML 重新生成 rss.yaml。中文分类下的源带 `lang: zh`，抓取时优先。

## 常见问题 / 排错

- **skip 403 / 401**：部分站点（如 FT、WSJ）需登录或禁止爬虫，属正常，程序会跳过并继续抓下一条。
- **parse error / Read timed out**：单篇超时或解析失败不会影响其余新闻，会继续抓取。可在 `config.yaml` 中调大 `request_timeout`（默认 30 秒）。
- **报错后整轮几乎停止**：已改为单条出错只跳过该条，不中断整轮；简报与 push 也做了保护，仅 push 失败会退出码非 0。

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

- **今日热点有数据但 News 文件夹没有新数据**  
  每轮结束会打印「本轮统计」：检查条数、保存条数、跳过原因（重复 / 关键词未匹配 / 抓取失败或正文过短 / 无效标题）。若「关键词未匹配」很多而保存为 0，说明当前 RSS 条目里几乎没有命中 `config.yaml` 里 `keywords` 的；可暂时将 `keywords` 留空或注释掉以保留全部新闻，或增加/调整关键词。若「抓取失败或正文过短」很多，可能是源站限流或需登录，可稍后再跑或更换 RSS 源。

## Obsidian 与各站排版说明

- 脚本写入的是 **Markdown**，不是网页 HTML，因此无法按「每个源站」单独套用该站的 CSS。`obsidian-snippets/daily-news-reader.css` 提供**统一的阅读版式**（字体、行距、最大宽度等），适用于所有新闻笔记。
- 若要在浏览器里看与官网一致的排版，可在笔记顶部使用「在浏览器中打开」链接查看原文。

## 安全与优化

- 仅允许 `http`/`https` 请求，禁止 `file://` 等。
- 请求超时与正文长度限制，防止卡死与内存滥用。
- 实体/文件名与写入路径做安全处理，防止路径穿越。
- Git 在仓库根执行，无 shell 拼接，失败时退出码非 0 便于排错。
