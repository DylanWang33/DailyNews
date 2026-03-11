# 主程序，核心 orchestrator。

import os

from rss_fetcher import load_sources, fetch_rss
from article_parser import fetch_article
from summarizer import summarize
from entity_extractor import extract_entities, write_entity
from event_extractor import extract_event
from importance_ranker import score_news
from deduplicator import is_duplicate
from obsidian_writer import write_news
from brief_generator import generate_brief
from git_sync import push

BASE = os.path.dirname(os.path.dirname(__file__))

OBSIDIAN_VAULT = "/Users/kryss/仓库/Dylan/DailyNews"

sources = load_sources(f"{BASE}/sources/rss_sources.yaml")

for s in sources:

    items = fetch_rss(s["url"])

    for i in items:

        if is_duplicate(i["title"]):
            continue

        article = fetch_article(i["link"])

        if not article or not article["text"]:
            continue

        summary = summarize(article["text"])

        entities = extract_entities(article["text"])

        event = extract_event(article["text"])

        score = score_news(article["text"], entities)

        for e in entities:
            write_entity(BASE, e)

        write_news(
            OBSIDIAN_VAULT,
            article["title"],
            summary,
            entities,
            i["link"],
            score
        )

generate_brief(BASE)

push()