# RSS 抓取：从 rss/feeds-all.opml 加载，使用 requests 显式超时，
# 过滤 24h 外的旧文章，清除乱码标题/摘要，记录健康状态

import os
import re
import html
import calendar
import datetime
import xml.etree.ElementTree as ET
import feedparser
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPML_PATH = os.path.join(_ROOT, "rss", "feeds-all.opml")
_FETCH_TIMEOUT = 15   # requests 超时秒数
_MAX_AGE_HOURS = 24   # 只保留 24 小时内的文章

try:
    import requests as _requests
except ImportError:
    _requests = None


# ── 乱码检测 ──────────────────────────────────────────────────────────────────

def _is_garbled(text: str) -> bool:
    """
    检测文本是否为乱码（编码错误、非法字符堆积等）。
    统计"合法"字符（中日韩、ASCII 可打印、常见扩展拉丁）占比，
    低于 50% 则视为乱码。
    """
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    if not text:
        return False
    good = 0
    for ch in text:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF        # 中文
                or 0x3400 <= cp <= 0x4DBF     # 扩展 CJK
                or 0x20 <= cp <= 0x7E          # ASCII 可打印
                or 0x00C0 <= cp <= 0x024F      # 扩展拉丁
                or 0x3040 <= cp <= 0x30FF      # 日文假名
                or 0xAC00 <= cp <= 0xD7A3      # 朝鲜语
                or ch in " \t\n\r，。！？、""''【】《》·…—～"):
            good += 1
    return (good / len(text)) < 0.5


def _clean_text(text: str) -> str:
    """去除文本中的乱码字符（保留合法字符），返回清洁文本。"""
    if not text:
        return ""
    result = []
    for ch in text:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF
                or 0x3400 <= cp <= 0x4DBF
                or 0x20 <= cp <= 0x7E
                or 0x00C0 <= cp <= 0x024F
                or 0x3040 <= cp <= 0x30FF
                or 0xAC00 <= cp <= 0xD7A3
                or ch in "，。！？、""''【】《》·…—～\n"):
            result.append(ch)
    cleaned = "".join(result).strip()
    # 如果清洁后内容太短（< 原文 30%），可能是整体乱码
    if len(cleaned) < len(text.strip()) * 0.3:
        return ""
    return cleaned


# ── 发布时间解析 ───────────────────────────────────────────────────────────────

def _parse_entry_time(entry) -> datetime.datetime | None:
    """从 feedparser entry 提取发布时间（UTC），无法解析时返回 None。"""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                ts = calendar.timegm(t)
                return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            except Exception:
                pass
    return None


def _format_pub_date(entry) -> str:
    """返回人类可读的发布时间字符串（本地时区），用于显示。"""
    dt = _parse_entry_time(entry)
    if dt is None:
        return ""
    local_dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    delta = now - local_dt
    if delta.total_seconds() < 3600:
        mins = int(delta.total_seconds() / 60)
        return f"{mins}分钟前"
    if delta.days == 0:
        return local_dt.strftime("%H:%M")
    return local_dt.strftime("%m-%d %H:%M")


# ── 链接提取 ──────────────────────────────────────────────────────────────────

def _first_href_from_html(html_text):
    if not html_text:
        return ""
    m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', html_text, re.I)
    return (m.group(1).strip() or "") if m else ""


def _entry_best_link(entry, feed_url=""):
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
    if not url:
        return True
    url = url.rstrip("/")
    if not url:
        return True
    parts = url.split("?")[0].rstrip("/").split("/")
    return len(parts) <= 3


def _strip_html(text):
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]


# ── 核心抓取函数 ───────────────────────────────────────────────────────────────

def fetch_rss(url, health_tracker=None):
    """
    抓取 RSS feed：
    - 使用 requests 显式超时，记录健康状态
    - 只返回 24 小时内的条目（无发布时间的条目保留）
    - 过滤乱码标题，清洁乱码摘要
    返回 [{"title","link","published","pub_date","summary"}, ...]
    """
    if not url or not isinstance(url, str):
        return []

    feed = None
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now_utc - datetime.timedelta(hours=_MAX_AGE_HOURS)

    # ── 请求 ──
    if _requests:
        try:
            resp = _requests.get(
                url, timeout=_FETCH_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DailyNews/1.0)"},
                allow_redirects=True,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            if health_tracker:
                health_tracker.record(url, "ok")
        except _requests.exceptions.Timeout:
            if health_tracker:
                health_tracker.record(url, "timeout")
        except Exception:
            if health_tracker:
                health_tracker.record(url, "error")

    if feed is None:
        try:
            feed = feedparser.parse(url)
            if health_tracker and feed.entries:
                health_tracker.record(url, "ok")
        except Exception:
            return []

    if not feed or not feed.entries:
        return []

    # ── 解析条目 ──
    items = []
    for entry in feed.entries:
        title = (getattr(entry, "title", "") or "").strip()

        # 乱码标题 → 跳过整条
        if _is_garbled(title):
            continue
        # 含部分乱码字符 → 清洁
        if any(ord(c) > 0x10000 or (0x0080 <= ord(c) < 0x00C0) for c in title):
            title = _clean_text(title)
            if not title:
                continue

        # 发布时间过滤（仅过滤有明确时间且超过 24h 的）
        pub_time = _parse_entry_time(entry)
        if pub_time is not None and pub_time < cutoff:
            continue

        # 摘要
        summary = ""
        for attr in ("summary", "description", "content"):
            raw = getattr(entry, attr, None)
            if hasattr(raw, "value"):
                raw = raw.value
            if raw and isinstance(raw, str):
                summary = _strip_html(raw)
                break
        # 乱码摘要 → 清空（保留文章）
        if _is_garbled(summary):
            summary = ""
        elif summary:
            summary = _clean_text(summary) or summary

        items.append({
            "title": title,
            "link": _entry_best_link(entry, url),
            "published": getattr(entry, "published", "") or "",
            "pub_date": _format_pub_date(entry),
            "summary": summary,
        })

    return items


# ── OPML 加载 ─────────────────────────────────────────────────────────────────

def load_categories_from_opml():
    """从 rss/feeds-all.opml 加载分类与源，返回 { "新闻": [{"name","url"}, ...], ... }。"""
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
        cat_name = html.unescape((cat_outline.get("text") or cat_outline.get("title") or "").strip())
        xml_url = (cat_outline.get("xmlUrl") or "").strip()
        if xml_url:
            result.setdefault(cat_name, []).append({"name": cat_name, "url": xml_url})
        else:
            feeds = []
            for child in cat_outline:
                if child.tag != "outline":
                    continue
                name = html.unescape((child.get("text") or child.get("title") or "").strip())
                url = (child.get("xmlUrl") or "").strip()
                if url:
                    feeds.append({"name": name, "url": url})
            if feeds and cat_name:
                result[cat_name] = feeds
    return result
