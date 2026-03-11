# 主程序：RSS → 抓文 → 关键词过滤 → 翻译 → AI摘要 → News/YYYY-MM-DD → Briefs + 今日热点

import os
import sys
import time
import random
import re
import warnings

# 抑制 requests 的 urllib3/chardet 版本警告，避免刷屏
warnings.filterwarnings("ignore", module="requests")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.getcwd() != _REPO_ROOT:
    os.chdir(_REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_project_root, get_obsidian_base, get_config, get_fetch_delay
from rss_fetcher import load_sources, fetch_rss
from article_parser import fetch_article
from summarizer import summarize
from translator import translate, translate_zh_to_en
from entity_extractor import extract_entities, write_entity
from event_extractor import extract_event
from importance_ranker import score_news
from deduplicator import is_duplicate, should_skip_title
from obsidian_writer import write_news
from brief_generator import generate_brief
from hot_writer import write_hot_by_category
from git_sync import push
from bloomberg_parser import fetch_bloomberg
from fetch_cursor import load_cursor, save_cursor_after_item, reset_cursor


def _delay():
    lo, hi = get_fetch_delay()
    time.sleep(random.uniform(lo, hi))


def _fetch_article_safe(link):
    link_lower = (link or "").lower()
    if "bloomberg.com" in link_lower:
        return fetch_bloomberg(link)
    return fetch_article(link)


def _has_cjk(s):
    return bool(s and re.search(r"[\u4e00-\u9fff]", str(s)))


def _matches_keywords(keywords, title_original, text, title_cn, cn_text):
    """是否命中任一关键词：先匹配原文+中文，若无且关键词为中文则用英文译词再匹配原文。"""
    if not keywords or not isinstance(keywords, list):
        return True
    keywords = [str(k).strip() for k in keywords if k]
    if not keywords:
        return True
    for kw in keywords:
        if not kw:
            continue
        if kw in (title_original or ""):
            return True
        if kw in (text or ""):
            return True
        if kw in (title_cn or ""):
            return True
        if kw in (cn_text or ""):
            return True
    for kw in keywords:
        if not kw or not _has_cjk(kw):
            continue
        en_kw = translate_zh_to_en(kw)
        if not en_kw:
            continue
        if en_kw.lower() in (title_original or "").lower():
            return True
        if en_kw.lower() in (text or "").lower():
            return True
    return False


def _fetch_hot_by_category():
    """按 config 的 hot_categories 抓取，返回 { 分类: { 源名称: [items] } }；英文标题译成中文并保留原标题。"""
    hot_categories = get_config("hot_categories")
    max_per = get_config("max_hot_items") or 15
    if not hot_categories or not isinstance(hot_categories, dict) or max_per <= 0:
        return {}
    result = {}
    for category_name, sources in hot_categories.items():
        if not isinstance(sources, list):
            continue
        by_source = {}
        for s in sources:
            name = (s.get("name") or "").strip() or (s.get("url") or "")[:30]
            url = (s.get("url") or "").strip()
            if not url:
                continue
            if name not in by_source:
                by_source[name] = []
            seen = {it["link"] for it in by_source[name]}
            for item in fetch_rss(url):
                if len(by_source[name]) >= max_per:
                    break
                link = (item.get("link") or "").strip()
                title = (item.get("title") or "").strip()
                if not link or not title:
                    continue
                if link in seen:
                    continue
                seen.add(link)
                display_title = title
                title_original = ""
                if not _has_cjk(title):
                    try:
                        display_title = translate(title)
                        if display_title:
                            title_original = title
                    except Exception:
                        pass
                by_source[name].append({
                    "title": display_title or title,
                    "link": link,
                    "source": name,
                    "title_original": title_original or None,
                })
        by_source = {k: v[:max_per] for k, v in by_source.items() if v}
        if by_source:
            result[category_name] = by_source
    return result


def main():
    get_project_root()
    BASE = get_obsidian_base()
    max_articles = get_config("max_articles_per_run") or 30
    keywords = get_config("keywords")
    if isinstance(keywords, str):
        keywords = [keywords] if keywords.strip() else []
    elif not isinstance(keywords, list):
        keywords = []

    # 今日热点：按源名称（如 知乎每日精选）写入，英文标题译中并备注原标题
    hot_by_cat = _fetch_hot_by_category()
    if hot_by_cat:
        write_hot_by_category(BASE, hot_by_cat)

    sources = load_sources()
    collected = []
    saved_count = 0
    last_s, last_i = load_cursor(len(sources))
    stats = {"skip_title": 0, "dup": 0, "fetch_fail": 0, "short": 0, "keyword": 0, "checked": 0}

    for source_idx, s in enumerate(sources):
        if saved_count >= max_articles:
            break
        url = (s.get("url") or "").strip()
        if not url:
            continue

        items = fetch_rss(url)
        for item_idx, i in enumerate(items):
            if saved_count >= max_articles:
                break
            if (source_idx, item_idx) <= (last_s, last_i):
                continue
            stats["checked"] += 1
            title = i.get("title") or ""
            link = i.get("link") or ""
            if not title or not link:
                continue
            if should_skip_title(title):
                stats["skip_title"] += 1
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
                continue
            if is_duplicate(title, link):
                stats["dup"] += 1
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
                continue

            _delay()
            article = _fetch_article_safe(link)
            if not article:
                stats["fetch_fail"] += 1
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
                continue

            text = (article.get("text") or "")[:500_000]
            if not text or len(text) < 200:
                stats["short"] += 1
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
                continue

            try:
                try:
                    cn_text = translate(text)
                except Exception as e:
                    print("translate error:", link[:60], e)
                    cn_text = ""

                try:
                    summary_en = summarize(text)
                except Exception as e:
                    print("summary error:", link[:60], e)
                    summary_en = text[:300]

                try:
                    summary_cn = translate(summary_en) if summary_en else ""
                except Exception as e:
                    print("summary translate error:", link[:60], e)
                    summary_cn = summary_en or ""

                title_original = article.get("title", title)
                try:
                    title_cn = translate(title_original) if title_original else ""
                except Exception:
                    title_cn = ""

                if not _matches_keywords(keywords, title_original, text, title_cn, cn_text):
                    stats["keyword"] += 1
                    save_cursor_after_item(source_idx, item_idx)
                    if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                        reset_cursor()
                    continue

                try:
                    entities = extract_entities(text)
                except Exception as e:
                    print("entity error:", link[:60], e)
                    entities = []
                try:
                    event = extract_event(text)
                except Exception as e:
                    print("event error:", link[:60], e)
                    event = None
                try:
                    score = score_news(text, entities)
                except Exception:
                    score = 0

                for e in entities:
                    try:
                        write_entity(BASE, e)
                    except Exception:
                        pass

                write_news(
                    BASE,
                    title_original,
                    summary_cn,
                    cn_text,
                    text,
                    entities,
                    link,
                    score,
                    title_cn_for_filename=title_cn or None,
                )
                saved_count += 1
                collected.append({
                    "title": title_original,
                    "summary": summary_cn or summary_en,
                    "url": link,
                })
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
            except Exception as e:
                print("article error (skip, continue):", link[:60], e)
                save_cursor_after_item(source_idx, item_idx)
                if source_idx == len(sources) - 1 and item_idx == len(items) - 1:
                    reset_cursor()
                continue

    print("本轮统计: 检查 {} 条, 保存 {} 条 | 跳过: 重复 {}, 关键词未匹配 {}, 抓取失败/短 {}, 无效标题 {}".format(
        stats["checked"], saved_count, stats["dup"], stats["keyword"],
        stats["fetch_fail"] + stats["short"], stats["skip_title"]))
    if saved_count == 0 and stats["checked"] > 0 and keywords:
        print("提示: 当前仅保留标题/正文含关键词的新闻。若需全部保留，请将 config.yaml 中 keywords 留空或注释掉。")

    try:
        generate_brief(BASE, collected)
    except Exception as e:
        print("brief error:", e)
    try:
        push()
    except Exception as e:
        print("push error:", e)
        raise


if __name__ == "__main__":
    main()
