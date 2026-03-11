# 主程序：RSS（feeds-all.opml）→ 每日新闻（仅标题+链接）→ 我的关注（关键词/标签筛选）
# 关键词支持分号：如 "美国;伊朗" 表示必须同时包含美国、伊朗（在 entities/标题/摘要 中）才归入该组

import os
import sys
import re
import warnings
from datetime import date

warnings.filterwarnings("ignore", module="requests")
# 抑制 spacy/argos 等首次加载时的 Language 提示，避免每次运行刷屏
warnings.filterwarnings("ignore", message=".*Language en package.*mwt.*")

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


def _parse_keyword_groups(keywords):
    """
    解析 config 的 keywords。每项可为 "美国;伊朗"（分号分隔多个标签），表示 AND：必须全部命中才归入该组。
    返回 [(group_name, [tag1, tag2, ...]), ...]，group_name 用于文件名/标题。
    """
    if not keywords or not isinstance(keywords, list):
        return []
    out = []
    for k in keywords:
        s = (k if isinstance(k, str) else str(k)).strip()
        if not s:
            continue
        parts = [p.strip() for p in re.split(r"[;；]", s) if p.strip()]
        if not parts:
            continue
        out.append((s, parts))
    return out


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


def _flatten_daily_news(daily_news_by_cat):
    """把 每日新闻 按分类/源 压平为一列表，便于遍历。"""
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
    return flat


def _relevance_to_keyword(keyword, title, summary, translate_zh_to_en_fn):
    """单条与单个关键词的契合度 0~1（仅用标题+摘要）。"""
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


def _tag_in_text(tag, text):
    """标签是否出现在文本中（含空白标准化）。"""
    if not tag or not text:
        return False
    t = (tag or "").strip()
    s = (text or "").replace("\n", " ").strip()
    return t in s or t.lower() in s.lower()


def _all_tags_in_article(tags, title, summary, entity_names):
    """所有标签是否都出现在 标题、摘要、实体名 的并集中。"""
    combined = (title or "") + " " + (summary or "") + " " + " ".join(entity_names or [])
    for tag in tags:
        if not _tag_in_text(tag, combined):
            return False
    return True


def _build_my_following_single_tag(daily_news_flat, group_name, tags, relevance_threshold, translate_zh_to_en_fn):
    """单标签组：仅用标题+摘要契合度，不抓正文。"""
    assert len(tags) == 1
    kw = tags[0]
    out = []
    for item in daily_news_flat:
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        if _relevance_to_keyword(kw, title, summary, translate_zh_to_en_fn) >= relevance_threshold:
            out.append(dict(item))
    return out


def _build_my_following_multi_tag(BASE, daily_news_flat, group_name, tags, date_str):
    """
    多标签组：仅当标题或摘要里出现至少一个标签时才抓正文；提取 entities，要求所有标签都在 entities/标题/摘要 中；
    命中条目使用正文的 extractive 摘要，并写入 entities/日期/。
    """
    from article_parser import fetch_article
    from entity_extractor import extract_entities, write_entity
    from summarizer import summarize

    candidates = []
    for item in daily_news_flat:
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        combined = title + " " + summary
        if any(_tag_in_text(t, combined) for t in tags):
            candidates.append(dict(item))

    result = []
    for item in candidates:
        link = item.get("link") or ""
        if not link:
            continue
        try:
            article = fetch_article(link)
        except Exception:
            continue
        if not article:
            continue
        text = (article.get("text") or "")[:50000]
        title = item.get("title") or article.get("title") or ""
        summary_rss = item.get("summary") or ""
        if not text or len(text) < 100:
            continue
        try:
            entity_names = extract_entities(text)
        except Exception:
            entity_names = []

        if not _all_tags_in_article(tags, title, summary_rss, entity_names):
            continue

        try:
            item["summary"] = summarize(text, sentences=3) or summary_rss or text[:200]
        except Exception:
            item["summary"] = summary_rss or text[:200]

        for e in entity_names:
            try:
                write_entity(BASE, e, date_str)
            except Exception:
                pass
        result.append(item)

    return result


def _build_my_following(daily_news_by_cat, keyword_groups, relevance_threshold, BASE, date_str, translate_zh_to_en_fn):
    """
    合并单标签（标题+摘要契合度）与多标签（抓正文 + entities 全匹配）结果。
    返回 { "组名": [items], ... }。
    """
    flat = _flatten_daily_news(daily_news_by_cat)
    by_group = {}
    for group_name, tags in keyword_groups:
        if len(tags) == 1:
            items = _build_my_following_single_tag(flat, group_name, tags, relevance_threshold, translate_zh_to_en_fn)
        else:
            items = _build_my_following_multi_tag(BASE, flat, group_name, tags, date_str)
        if items:
            by_group[group_name] = items
    return by_group


def main():
    get_project_root()
    BASE = get_obsidian_base()
    raw_keywords = get_config("keywords")
    if isinstance(raw_keywords, str):
        raw_keywords = [raw_keywords] if raw_keywords.strip() else []
    elif not isinstance(raw_keywords, list):
        raw_keywords = []
    keyword_groups = _parse_keyword_groups(raw_keywords)
    relevance_threshold = float(get_config("relevance_threshold") or 0.7)
    date_str = date.today().isoformat()

    # 1) 每日新闻：从 OPML 拉取全部
    daily_news = _fetch_all_daily_news()
    if daily_news:
        write_daily_news(BASE, daily_news)

    # 2) 我的关注：分号表示多标签 AND，多标签时抓正文并用 entities+标题+摘要 全匹配；实体按日期写入 entities/YYYY-MM-DD/
    if daily_news and keyword_groups:
        follow_items = _build_my_following(
            daily_news, keyword_groups, relevance_threshold, BASE, date_str, translate_zh_to_en
        )
        if follow_items:
            write_my_following(BASE, date_str, follow_items)

    try:
        push()
    except Exception as e:
        print("push error:", e)
        raise


if __name__ == "__main__":
    main()
