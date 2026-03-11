# 主程序，核心 orchestrator。

import os

from rss_fetcher import load_sources, fetch_rss
from article_parser import fetch_article
from summarizer import summarize
from translator import translate
from entity_extractor import extract_entities, write_entity
from event_extractor import extract_event
from importance_ranker import score_news
from deduplicator import is_duplicate
from obsidian_writer import write_news
from brief_generator import generate_brief
from git_sync import push
from bloomberg_parser import fetch_bloomberg


BASE = "/Users/kryss/仓库/Dylan/DailyNews"


def main():

    sources = load_sources("sources/rss.yaml")

    for s in sources:

        items = fetch_rss(s["url"])

        for i in items:

            title = i.get("title")
            link = i.get("link")

            if not title or not link:
                continue

            if is_duplicate(title):
                continue

            article = fetch_article(link)

            if not article:
                continue

            text = article.get("text")

            if not text or len(text) < 200:
                continue

            # ===== 中文全文翻译 =====
            try:
                cn_text = translate(text)
            except Exception as e:
                print("translate error:", e)
                cn_text = ""

            # ===== 英文摘要 =====
            try:
                summary_en = summarize(text)
            except Exception as e:
                print("summary error:", e)
                summary_en = text[:300]

            # ===== 中文摘要翻译 =====
            try:
                summary_cn = translate(summary_en)
            except Exception as e:
                print("summary translate error:", e)
                summary_cn = summary_en

            # ===== 实体抽取 =====
            try:
                entities = extract_entities(text)
            except Exception as e:
                print("entity error:", e)
                entities = []

            # ===== 事件抽取 =====
            try:
                event = extract_event(text)
            except Exception as e:
                print("event error:", e)
                event = None

            # ===== 新闻评分 =====
            try:
                score = score_news(text, entities)
            except Exception:
                score = 0

            # ===== 写入实体库 =====
            for e in entities:
                write_entity(BASE, e)

            # ===== 写入 Obsidian =====
            write_news(
                BASE,
                article["title"],
                summary_cn,
                cn_text,
                text,
                entities,
                link,
                score
            )

    generate_brief(BASE)

    push()


if __name__ == "__main__":
    main()