# 抓 RSS。

import feedparser
import yaml

def load_sources(path):

    with open(path) as f:
        return yaml.safe_load(f)

def fetch_rss(url):

    feed = feedparser.parse(url)

    items = []

    for entry in feed.entries:

        items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published", "")
        })

    return items