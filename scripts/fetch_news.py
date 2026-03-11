# 主程序：RSS → 抓文 → 翻译 → AI摘要 → News/YYYY-MM-DD → Briefs/YYYY-MM-DD.md
# 与 Obsidian 双向链接：新闻 → 翻译 → AI分析 → 知识图谱

import os
import sys
import time
import random

# 确保从项目根运行（快捷指令可能从任意目录触发）
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.getcwd() != _REPO_ROOT:
    os.chdir(_REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_project_root, get_obsidian_base, get_config, REQUEST_TIMEOUT, FETCH_DELAY_MIN, FETCH_DELAY_MAX
from rss_fetcher import load_sources, fetch_rss
from article_parser import fetch_article
from summarizer import summarize
from translator import translate
from entity_extractor import extract_entities, write_entity
from event_extractor import extract_event
from importance_ranker import score_news
from deduplicator import is_duplicate, should_skip_title
from obsidian_writer import write_news
from brief_generator import generate_brief
from git_sync import push
from bloomberg_parser import fetch_bloomberg


def _delay():
    """反爬延迟"""
    time.sleep(random.uniform(FETCH_DELAY_MIN, FETCH_DELAY_MAX))


def _fetch_article_safe(link):
    """按域名选择解析器：Bloomberg 用专用解析，其余用通用"""
    link_lower = (link or "").lower()
    if "bloomberg.com" in link_lower:
        return fetch_bloomberg(link)
    return fetch_article(link)


def main():
    get_project_root()
    BASE = get_obsidian_base()
    max_articles = get_config("max_articles_per_run") or 30  # 每轮最多保存篇数，达到后自动结束

    sources = load_sources()
    collected = []
    saved_count = 0

    for s in sources:
        if saved_count >= max_articles:
            break
        url = (s.get("url") or "").strip()
        if not url:
            continue

        items = fetch_rss(url)
        for i in items:
            if saved_count >= max_articles:
                break
            title = i.get("title") or ""
            link = i.get("link") or ""
            if not title or not link:
                continue
            if should_skip_title(title):
                continue
            if is_duplicate(title, link):
                continue

            _delay()
            article = _fetch_article_safe(link)
            if not article:
                continue

            text = (article.get("text") or "")[:500_000]
            if not text or len(text) < 200:
                continue

            # 中文全文翻译
            try:
                cn_text = translate(text)
            except Exception as e:
                print("translate error:", e)
                cn_text = ""

            # 英文摘要
            try:
                summary_en = summarize(text)
            except Exception as e:
                print("summary error:", e)
                summary_en = text[:300]

            # 中文摘要
            try:
                summary_cn = translate(summary_en) if summary_en else ""
            except Exception as e:
                print("summary translate error:", e)
                summary_cn = summary_en or ""

            # 实体 / 事件 / 评分
            try:
                entities = extract_entities(text)
            except Exception as e:
                print("entity error:", e)
                entities = []
            try:
                event = extract_event(text)
            except Exception as e:
                print("event error:", e)
                event = None
            try:
                score = score_news(text, entities)
            except Exception:
                score = 0

            for e in entities:
                write_entity(BASE, e)

            title_original = article.get("title", title)
            try:
                title_cn = translate(title_original) if title_original else ""
            except Exception:
                title_cn = ""

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

    generate_brief(BASE, collected)
    push()


if __name__ == "__main__":
    main()
