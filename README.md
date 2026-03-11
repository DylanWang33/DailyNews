# DailyNews

从 **rss/feeds-all.opml** 拉取全部 RSS，生成 **每日新闻**（仅标题+链接，点击在浏览器中查看正文），再按 **config 关键词** 筛选出 **我的关注**，并推送到 Git。

## 目录结构

```
DailyNewsRepo/
├── config.yaml       # obsidian_base、keywords、relevance_threshold
├── scripts/          # 所有程序
├── rss/              # feeds-all.opml（唯一 RSS 源定义）
├── 每日新闻/          # 每日新闻/日期/分类/具体网站.md（仅标题+链接）
├── 我的关注/          # 我的关注/日期/关键词.md（契合度≥阈值的条目）
├── obsidian-snippets/ # 可选：复制到库 .obsidian/snippets 优化阅读
├── logs/             # run.sh 输出日志
└── run.sh            # 一键执行
```

## 数据流

```
rss/feeds-all.opml
        ↓
fetch_news.py
        ↓
每日新闻：拉取所有分类、所有源、所有条目（不限制条数），仅标题+链接+RSS 摘要
        → 每日新闻/YYYY-MM-DD/分类/具体网站.md（英文标题可译成中文显示）
        ↓
我的关注：从当日「每日新闻」中按 config 的 keywords 筛选
        契合度 = 标题 + RSS 摘要 与关键词的匹配（中文关键词会译英再匹配外文）
        契合度 ≥ relevance_threshold（默认 0.7）则归入该关键词
        → 我的关注/YYYY-MM-DD/关键词.md
        ↓
git push
```

- **不抓取正文**：不再请求文章页面，不生成 News 文件夹、不翻译正文、不生成简报。
- **契合度**：仅用 RSS 的标题和摘要（description/summary）计算，不访问原文；契合度标记不写入 Obsidian，仅用于筛选。

## 执行方式

### Mac 快捷指令

```bash
/bin/bash /Users/kryss/DailyNewsRepo/run.sh
```

或直接：

```bash
/Users/kryss/DailyNewsRepo/venv/bin/python /Users/kryss/DailyNewsRepo/scripts/fetch_news.py
```

日志路径：`/Users/kryss/DailyNewsRepo/logs/run.log`

### 终端

```bash
cd /Users/kryss/DailyNewsRepo
./run.sh
```

## 配置（config.yaml）

- **obsidian_base**：每日新闻、我的关注写入的目录（一般为 Obsidian 库内子文件夹）。
- **keywords**：关键词列表，如 `油价`、`美伊战争`；从每日新闻中筛选出契合度 ≥ 阈值的条目，写入「我的关注」对应日期的 `关键词.md`。
- **relevance_threshold**：0～1，默认 `0.7`；标题+摘要与关键词的匹配度 ≥ 此值才归入我的关注。中文关键词会译成英文后再匹配英文标题/摘要。

## RSS 源

- **rss/feeds-all.opml**：所有 RSS 源，按分类（新闻、科技、知识、娱乐、财经、生活、外国媒体等）组织。脚本直接读取 OPML，**不限制每条数量**，全部拉取。

## 常见问题

- **Permission denied**：对 `每日新闻`、`我的关注`、`logs` 等目录执行 `chown`/`chmod` 确保当前用户可写。
- **我的关注为空**：检查 `keywords` 是否配置、`relevance_threshold` 是否过高；当前仅用标题和 RSS 摘要匹配，若摘要过短可适当调低阈值或增加关键词。

## Obsidian 排版

将 `obsidian-snippets/daily-news-reader.css` 复制到库根下 `.obsidian/snippets/`，在 Obsidian 设置 → 外观 → CSS 代码片段 中重新加载并启用。正文需在浏览器中打开链接查看。
