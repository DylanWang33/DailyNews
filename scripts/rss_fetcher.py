# 抓 RSS：从 sources/rss.yaml 或 rss/feeds-all.opml 加载

import os
import re
import html
import xml.etree.ElementTree as ET
import feedparser
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPML_PATH = os.path.join(_ROOT, "rss", "feeds-all.opml")


def load_sources():
    """从 sources/rss.yaml 加载 RSS 源，返回 [{"name": str, "url": str}, ...]。"""
    yaml_path = os.path.join(_ROOT, "sources", "rss.yaml")
    if not os.path.isfile(yaml_path):
        return []
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        return []
    out = []
    for x in data:
        url = (x.get("url") or "").strip()
        if not url:
            continue
        out.append({
            "name": (x.get("name") or url[:50]),
            "url": url,
            "lang": (x.get("lang") or "").strip().lower(),
        })
    # 中文优先
    out.sort(key=lambda s: (0 if s.get("lang") == "zh" else 1))
    return out


def _first_href_from_html(html):
    """从 HTML 片段中取第一个 href 链接（用于新浪等把文章链接放在摘要里的 feed）。"""
    if not html:
        return ""
    m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', html, re.I)
    return (m.group(1).strip() or "") if m else ""


def _entry_best_link(entry, feed_url=""):
    """优先取条目的真实文章链接，避免拿到首页。"""
    link = ""
    links = getattr(entry, "links", []) or []
    for ln in links:
        if isinstance(ln, dict) and ln.get("rel") == "alternate":
            link = (ln.get("href") or "").strip()
            if link and link.startswith("http"):
                return link
        elif isinstance(ln, dict) and not link:
            link = (ln.get("href") or "").strip()
            if link and link.startswith("http"):
                return link
    link = getattr(entry, "link", "") or ""
    if link and link.startswith("http"):
        link = link.strip()
    if not link:
        uid = getattr(entry, "id", "") or ""
        if uid and uid.startswith("http"):
            link = uid.strip()
    if not link or _is_likely_homepage(link):
        for attr in ("summary", "description", "content"):
            raw = getattr(entry, attr, None)
            if hasattr(raw, "value"):
                raw = raw.value
            if raw and isinstance(raw, str):
                fallback = _first_href_from_html(raw)
                if fallback and fallback.startswith("http") and not _is_likely_homepage(fallback):
                    return fallback
    return link.strip() if link else ""


def _is_likely_homepage(url):
    """简单判断是否为站点首页（无路径或路径极短），这类常不是文章页。"""
    if not url:
        return True
    url = url.rstrip("/")
    if not url:
        return True
    parts = url.split("?")[0].rstrip("/").split("/")
    if len(parts) <= 3:
        return True
    return False


def _strip_html(text):
    """简单去掉 HTML 标签，得到纯文本（用于 RSS summary）。"""
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]


def fetch_rss(url):
    """抓取 RSS feed，返回 [{"title","link","published","summary"}, ...]。link 优先为文章页 URL。"""
    if not url or not isinstance(url, str):
        return []
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        summary = ""
        for attr in ("summary", "description", "content"):
            raw = getattr(entry, attr, None)
            if hasattr(raw, "value"):
                raw = raw.value
            if raw and isinstance(raw, str):
                summary = _strip_html(raw)
                break
        items.append({
            "title": getattr(entry, "title", "") or "",
            "link": _entry_best_link(entry, url),
            "published": getattr(entry, "published", "") or "",
            "summary": summary,
        })
    return items


def load_categories_from_opml():
    """从 rss/feeds-all.opml 加载分类与源，返回 { "新闻": [{"name","url"}, ...], "科技": [...], ... }。"""
    if not os.path.isfile(OPML_PATH):
        return {}
    tree = ET.parse(OPML_PATH)
    root = tree.getroot()
    body = root.find(".//body")
    if body is None:
        body = root
    result = {}
    for cat_outline in body:
        if cat_outline.tag != "outline":
            continue
        cat_name = (cat_outline.get("text") or cat_outline.get("title") or "").strip()
        cat_name = html.unescape(cat_name)
        xml_url = (cat_outline.get("xmlUrl") or "").strip()
        if xml_url:
            if cat_name not in result:
                result[cat_name] = []
            result[cat_name].append({
                "name": cat_name,
                "url": xml_url,
            })
        else:
            feeds = []
            for child in cat_outline:
                if child.tag != "outline":
                    continue
                name = (child.get("text") or child.get("title") or "").strip()
                name = html.unescape(name)
                url = (child.get("xmlUrl") or "").strip()
                if url:
                    feeds.append({"name": name, "url": url})
            if feeds and cat_name:
                result[cat_name] = feeds
    return result
