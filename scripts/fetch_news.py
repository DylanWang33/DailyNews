# 主程序：RSS（feeds-all.opml）→ 每日新闻（仅标题+链接）→ 我的关注（按关键词筛选，契合度≥70%）

import os
import sys
import re
import warnings

warnings.filterwarnings("ignore", module="requests")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.getcwd() != _REPO_ROOT:
    os.chdir(_REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_project_root, get_obsidian_base, get_config
from rss_fetcher import load_categories_from_opml, fetch_rss
from translator import translate, translate_zh_to_en
from hot_writer import write_daily_news, write_my_following
from git_sync import push


def _has_cjk(s):
    return bool(s and re.search(r"[\u4e00-\u9fff]", str(s)))


def _fetch_all_daily_news():
    """从 OPML 拉取所有源、所有条目，返回 { 分类: { 源名: [items] } }；英文标题可译成中文显示。"""
    categories = load_categories_from_opml()
    if not categories:
        return {}
    result = {}
    for category_name, sources in categories.items():
        if not isinstance(sources, list):
            continue
        by_source = {}
        for s in sources:
            name = (s.get("name") or "").strip() or (s.get("url") or "")[:30]
            url = (s.get("url") or "").strip()
            if not url:
                continue
            items = []
            seen_links = set()
            for raw in fetch_rss(url):
                link = (raw.get("link") or "").strip()
                title = (raw.get("title") or "").strip()
                if not link or not title or link in seen_links:
                    continue
                seen_links.add(link)
                display_title = title
                title_original = ""
                if not _has_cjk(title):
                    try:
                        display_title = translate(title) or title
                        if display_title:
                            title_original = title
                    except Exception:
                        pass
                items.append({
                    "title": display_title or title,
                    "link": link,
                    "source": name,
                    "title_original": title_original or None,
                    "summary": (raw.get("summary") or "").strip(),
                })
            if items:
                by_source[name] = items
        if by_source:
            result[category_name] = by_source
    return result


def _relevance_to_keyword(keyword, title, summary, translate_zh_to_en_fn):
    """
    计算单条与关键词的契合度 0~1。标题命中权重大，摘要次之；中文关键词会译成英文再匹配英文标题/摘要。
    """
    text = (title or "") + " " + (summary or "")
    if not keyword or not text.strip():
        return 0.0
    score = 0.0
    kw_lower = keyword.strip().lower()
    title_lower = (title or "").lower()
    summary_lower = (summary or "").lower()
    if kw_lower in title_lower or keyword.strip() in (title or ""):
        score += 0.7
    if kw_lower in summary_lower or keyword.strip() in (summary or ""):
        score += 0.3
    if score >= 0.7:
        return min(1.0, score)
    if _has_cjk(keyword):
        en_kw = translate_zh_to_en_fn(keyword.strip())
        if en_kw:
            en_kw_lower = en_kw.lower()
            if en_kw_lower in title_lower or en_kw in (title or ""):
                score += 0.7
            if en_kw_lower in summary_lower or en_kw in (summary or ""):
                score += 0.3
    return min(1.0, score)


def _build_my_following(daily_news_by_cat, keywords, relevance_threshold, translate_zh_to_en_fn):
    """
    从当日 每日新闻 数据中按关键词筛选，契合度 >= relevance_threshold 的归入 我的关注。
    返回 { "关键词": [items], ... }。
    """
    if not keywords or not isinstance(keywords, list):
        return {}
    keywords = [str(k).strip() for k in keywords if k]
    if not keywords:
        return {}
    flat = []
    for cat_name, sources in (daily_news_by_cat or {}).items():
        for source_name, items in (sources or {}).items():
            for it in items:
                flat.append({
                    "title": it.get("title") or "",
                    "link": it.get("link") or "",
                    "source": it.get("source") or "",
                    "title_original": it.get("title_original"),
                    "summary": it.get("summary") or "",
                })
    by_keyword = {kw: [] for kw in keywords}
    for item in flat:
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        for kw in keywords:
            r = _relevance_to_keyword(kw, title, summary, translate_zh_to_en_fn)
            if r >= relevance_threshold:
                by_keyword[kw].append(item)
    return {k: v for k, v in by_keyword.items() if v}


def main():
    get_project_root()
    BASE = get_obsidian_base()
    keywords = get_config("keywords")
    if isinstance(keywords, str):
        keywords = [keywords] if keywords.strip() else []
    elif not isinstance(keywords, list):
        keywords = []
    relevance_threshold = float(get_config("relevance_threshold") or 0.7)

    # 1) 每日新闻：从 OPML 拉取全部，不限制条数
    daily_news = _fetch_all_daily_news()
    if daily_news:
        write_daily_news(BASE, daily_news)

    # 2) 我的关注：从当日 每日新闻 中按关键词筛选（契合度 >= relevance_threshold）
    if daily_news and keywords:
        follow_items = _build_my_following(daily_news, keywords, relevance_threshold, translate_zh_to_en)
        if follow_items:
            from datetime import date
            write_my_following(BASE, date.today().isoformat(), follow_items)

    try:
        push()
    except Exception as e:
        print("push error:", e)
        raise


if __name__ == "__main__":
    main()
