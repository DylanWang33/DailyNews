# DailyNews

DailyNewsRepo
│
scripts/        # 所有程序
sources/        # RSS源
news/           # 生成新闻
entities/       # 实体库
events/         # 事件
briefs/         # 每日简报
cache/          # 去重缓存

数据流：
rss_fetcher
↓
article_parser
↓
summarizer
↓
entity_extractor
↓
event_extractor
↓
importance_ranker
↓
obsidian_writer
↓
brief_generator
↓
git_sync