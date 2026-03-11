import feedparser
import datetime

rss_sources = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.reutersagency.com/feed/"
]

today = datetime.date.today()

filename = f"news/{today}.md"

content = f"# {today} 新闻简报\n\n"

for url in rss_sources:
    feed = feedparser.parse(url)

    for entry in feed.entries[:3]:
        content += f"## {entry.title}\n"
        content += f"来源: {url}\n"
        content += f"链接: {entry.link}\n\n"
        content += f"{entry.summary}\n\n---\n\n"

with open(filename, "w") as f:
    f.write(content)
