# 抓 RSS：支持 rss.txt（一行一源）与 rss.yaml

import os
import feedparser
import yaml

# 项目根（与 fetch_news 一致）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sources_path():
    return os.path.join(_ROOT, "sources")


def load_sources():
    """
    加载 RSS 源。优先 sources/rss.txt（每行一个 URL，或 name|url），否则 sources/rss.yaml。
    返回 [{"name": str, "url": str}, ...]
    """
    base = _sources_path()
    txt_path = os.path.join(base, "rss.txt")
    yaml_path = os.path.join(base, "rss.yaml")

    # 1) rss.txt：一行一个 URL，或 "显示名|URL"
    if os.path.isfile(txt_path):
        out = []
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    name, url = line.split("|", 1)
                    name, url = name.strip(), url.strip()
                else:
                    url = line
                    name = url[:50]
                if url:
                    out.append({"name": name, "url": url})
        if out:
            return out

    # 2) rss.yaml
    if os.path.isfile(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return [
                {"name": (x.get("name") or x.get("url", "")[:50]), "url": (x.get("url") or "").strip()}
                for x in data
                if (x.get("url") or "").strip()
            ]
    return []


def fetch_rss(url):
    """抓取 RSS feed，返回 [{"title","link","published"}, ...]。"""
    if not url or not isinstance(url, str):
        return []
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        items.append({
            "title": getattr(entry, "title", "") or "",
            "link": getattr(entry, "link", "") or "",
            "published": getattr(entry, "published", "") or "",
        })
    return items
