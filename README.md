# DailyNews

从 **rss/feeds-all.opml** 拉取全部 RSS，生成 **每日新闻**（仅标题+链接，点击在浏览器中查看正文），再按 **config 关键词** 筛选出 **我的关注**，并推送到 Git。

## 目录结构

```
DailyNewsRepo/
├── config.yaml       # obsidian_base、keywords、relevance_threshold
├── scripts/          # 所有程序
├── rss/              # feeds-all.opml（唯一 RSS 源定义）
├── 每日新闻/          # 每日新闻/日期/分类/具体网站.md（仅标题+链接）
├── 我的关注/          # 我的关注/日期/关键词.md（单关键词契合度 或 多标签全匹配）
├── entities/          # 实体按日期 entities/YYYY-MM-DD/，便于按日删除释放空间
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
        - 单个关键词：仅用标题 + RSS 摘要契合度 ≥ relevance_threshold 即归入
        - 分号多标签（如 美国;伊朗）：必须**全部**标签都出现在该文的 entities/标题/摘要 中才归入；会抓取正文、提取实体、并用 sumy 做摘要
        → 我的关注/YYYY-MM-DD/关键词.md
        ↓
实体按日期写入 entities/YYYY-MM-DD/，需要释放空间时可直接删除某日文件夹
        ↓
git push
```

- **分号 = AND**：`美国;伊朗` 表示「美国」与「伊朗」两个标签都要匹配（在实体、标题或摘要中），只含一个不会放入。
- **实体按日**：实体笔记写在 `entities/YYYY-MM-DD/` 下，删除某日即释放该日实体，不影响其他日期。

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
- **keywords**：关键词列表。单个词如 `油价` 用标题+摘要契合度筛选。**分号表示多标签 AND**，如 `美国;伊朗` 表示须同时包含美国、伊朗（在 entities/标题/摘要 中）才归入该组，此时会抓正文、提取实体并做摘要。
- **relevance_threshold**：0～1，默认 `0.7`；仅对**单关键词**生效；多标签组不看此值，必须全标签命中。

## RSS 源

- **rss/feeds-all.opml**：所有 RSS 源，按分类（新闻、科技、知识、娱乐、财经、生活、外国媒体等）组织。脚本直接读取 OPML，**不限制每条数量**，全部拉取。

## 常见问题

- **Permission denied**：对 `每日新闻`、`我的关注`、`logs` 等目录执行 `chown`/`chmod` 确保当前用户可写。
- **我的关注为空**：单关键词时检查 `relevance_threshold`；多标签（如 `美国;伊朗`）时需正文中同时出现所有标签，且会抓取正文（可能较慢或部分站点失败）。

## AI 驱动（OpenClaw 集成）

配置 `openclaw_base_url` 后，以下环节自动切换为 AI 驱动：

| 环节 | 未配置（传统） | 配置后（AI） |
|------|----------------|--------------|
| 单标签筛选 | 标题+摘要字符串匹配 | LLM 批量语义相关性判断 |
| 多标签匹配 | 抓正文 → spacy 实体提取 → 字符串检测 | LLM 直接判断（无需抓正文，更快） |
| 摘要生成 | sumy LSA 抽取式 | LLM 生成式（可指定中文、突出重点） |
| 标题翻译（可选） | argostranslate | LLM 批量翻译（需 `openclaw_translate: true`） |

OpenClaw 支持多种后端：本地 Ollama（免费、隐私）、OpenAI、Claude 等。详见 [docs/openclaw-集成分析.md](docs/openclaw-集成分析.md)。

未配置 `openclaw_base_url` 时行为与之前完全一致（sumy 摘要、字符串匹配）。

## Obsidian 排版

将 `obsidian-snippets/daily-news-reader.css` 复制到库根下 `.obsidian/snippets/`，在 Obsidian 设置 → 外观 → CSS 代码片段 中重新加载并启用。正文需在浏览器中打开链接查看。
