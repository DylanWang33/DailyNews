# 主程序：RSS（feeds-all.opml）→ 每日新闻（仅标题+链接）→ 我的关注（AI/关键词筛选）
# OpenClaw 集成：
#   - 单标签筛选：batch_is_relevant_llm() 替代字符串匹配，回退到契合度评分
#   - 多标签匹配：all_tags_match_llm() 替代 spacy 实体提取，无需先抓正文
#   - AI 摘要：summarize_with_llm() 替代 sumy LSA，回退到 sumy
#   - 可选标题翻译：translate_titles_with_llm() 替代 argostranslate（需 openclaw_translate: true）

import os
import sys
import re
import warnings
from datetime import date

warnings.filterwarnings("ignore", module="requests")
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
from feed_health import FeedHealthTracker


def _has_cjk(s):
    return bool(s and re.search(r"[\u4e00-\u9fff]", str(s)))


def _read_existing_links_by_source():
    """
    读取本地已存在的链接，按分类/源组织
    返回 { "分类名": { "源名": set(links) } }
    """
    BASE = get_obsidian_base()
    today = str(date.today())
    daily_news_dir = os.path.join(BASE, "每日新闻", today)

    result = {}

    if not os.path.isdir(daily_news_dir):
        return result

    # 遍历所有分类目录
    for cat_dir_name in os.listdir(daily_news_dir):
        cat_path = os.path.join(daily_news_dir, cat_dir_name)
        if not os.path.isdir(cat_path):
            continue

        result[cat_dir_name] = {}

        # 遍历分类下的所有源文件
        for source_file in os.listdir(cat_path):
            if not source_file.endswith(".md"):
                continue

            source_name = source_file[:-3]  # 去掉 .md
            filepath = os.path.join(cat_path, source_file)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                # 提取所有 markdown 链接
                links = set(re.findall(r'\]\(([^)\s]+)\)', content))
                if links:
                    result[cat_dir_name][source_name] = links
            except Exception:
                pass

    return result


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


def _fetch_all_daily_news(health_tracker=None):
    """
    从 OPML 拉取所有源、所有条目，返回 { 分类: { 源名: [items] } }。
    - 智能增量抓取：如果本地已存在该源，检测到已知链接时停止该源的抓取
    - 传入 health_tracker 记录各 URL 的超时/成功状态
    - 英文标题优先 LLM 批量翻译，回退 argostranslate
    """
    categories = load_categories_from_opml()
    if not categories:
        return {}

    # 读取本地已存在的链接（增量模式）
    existing_links = _read_existing_links_by_source()

    all_items_needing_translation = []

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

            # 获取该源的已知链接集合
            known_links = existing_links.get(category_name, {}).get(name, set())
            if known_links:
                print(f"[增量] {category_name}/{name}: 本地已有 {len(known_links)} 条记录")

            for raw in fetch_rss(url, health_tracker=health_tracker):
                link = (raw.get("link") or "").strip()
                title = (raw.get("title") or "").strip()
                if not link or not title or link in seen_links:
                    continue

                # 检测增量边界：如果遇到已知链接，停止该源的抓取
                if link in known_links:
                    if items:
                        print(f"[增量] {category_name}/{name}: ✓ 已到达已存在内容，停止抓取（新增 {len(items)} 条）")
                    break

                seen_links.add(link)
                item = {
                    "title": title,
                    "link": link,
                    "source": name,
                    "title_original": None,
                    "summary": (raw.get("summary") or "").strip(),
                    "pub_date": (raw.get("pub_date") or "").strip(),
                    "_needs_translation": not _has_cjk(title),
                }
                items.append(item)
                if item["_needs_translation"]:
                    all_items_needing_translation.append(item)

            if items:
                by_source[name] = items
        if by_source:
            result[category_name] = by_source

    _translate_titles(all_items_needing_translation)

    for by_source in result.values():
        for items in by_source.values():
            for item in items:
                item.pop("_needs_translation", None)

    return result


def _translate_titles(items_needing_translation):
    """翻译 items 中所有英文标题，直接修改 item dict（in-place）。"""
    if not items_needing_translation:
        return

    # 尝试 LLM 批量翻译（需 openclaw_translate: true）
    try:
        from llm_summary import translate_titles_with_llm
        titles = [it["title"] for it in items_needing_translation]
        translated = translate_titles_with_llm(titles)
        if translated and len(translated) == len(titles):
            for item, zh_title in zip(items_needing_translation, translated):
                if zh_title and zh_title != item["title"]:
                    item["title_original"] = item["title"]
                    item["title"] = zh_title
            return
    except Exception:
        pass

    # 回退：argostranslate 逐条翻译
    for item in items_needing_translation:
        original = item["title"]
        try:
            zh = translate(original) or original
            if zh and zh != original:
                item["title_original"] = original
                item["title"] = zh
        except Exception:
            pass


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
    """单条与单个关键词的契合度 0~1（仅用标题+摘要）。传统方法，LLM 不可用时的回退。"""
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
    """所有标签是否都出现在 标题、摘要、实体名 的并集中（传统方法回退）。"""
    combined = (title or "") + " " + (summary or "") + " " + " ".join(entity_names or [])
    for tag in tags:
        if not _tag_in_text(tag, combined):
            return False
    return True


# ─── 单标签筛选：优先 AI 批量相关性判断，回退字符串匹配 ────────────────────

def _build_my_following_single_tag(daily_news_flat, group_name, tags, relevance_threshold, translate_zh_to_en_fn):
    """
    单标签组：
    - 若 OpenClaw 已配置，用 batch_is_relevant_llm() 进行 AI 语义相关性判断（更准确，识别同义表达）
    - 否则回退：标题+摘要字符串契合度评分 ≥ relevance_threshold
    """
    assert len(tags) == 1
    kw = tags[0]

    # AI 路径：批量相关性判断
    try:
        from llm_summary import batch_is_relevant_llm
        flags = batch_is_relevant_llm(daily_news_flat, kw)
        if flags is not None:
            print(f"  [AI筛选] 关键词「{kw}」：共 {len(daily_news_flat)} 篇 → AI 判定相关 {sum(flags)} 篇")
            return [dict(item) for item, flag in zip(daily_news_flat, flags) if flag]
    except Exception:
        pass

    # 传统回退：字符串契合度
    out = []
    for item in daily_news_flat:
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        if _relevance_to_keyword(kw, title, summary, translate_zh_to_en_fn) >= relevance_threshold:
            out.append(dict(item))
    return out


# ─── 多标签筛选：优先 AI 主题匹配（无需抓正文），回退实体提取 ───────────────

def _build_my_following_multi_tag(BASE, daily_news_flat, group_name, tags, date_str):
    """
    多标签组（AND 逻辑）：
    - AI 路径：先用 all_tags_match_llm() 在标题+RSS摘要上判断（快速，无需抓正文）
              命中后才抓正文生成 AI 摘要（summarize_with_llm）
    - 传统回退（LLM 不可用时）：抓正文 → spacy 实体提取 → 全标签字符串匹配 → sumy 摘要
    """
    from summarizer import summarize

    # 第一步：预筛选（任意标签出现在标题/摘要中才进入候选）
    candidates = []
    for item in daily_news_flat:
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        combined = title + " " + summary
        if any(_tag_in_text(t, combined) for t in tags):
            candidates.append(dict(item))

    print(f"  [多标签「{group_name}」] 预筛候选：{len(candidates)} 篇")

    # 判断 LLM 是否可用
    llm_available = False
    try:
        from llm_summary import _get_config
        cfg = _get_config()
        llm_available = bool((cfg.get("openclaw_base_url") or "").strip())
    except Exception:
        pass

    result = []
    for item in candidates:
        link = item.get("link") or ""
        title = item.get("title") or ""
        summary_rss = item.get("summary") or ""

        if llm_available:
            # ── AI 路径 ─────────────────────────────────────────────────────
            try:
                from llm_summary import all_tags_match_llm, summarize_with_llm
                match = all_tags_match_llm(title, summary_rss, tags)
            except Exception:
                match = None

            if match is False:
                continue  # LLM 确认不相关，跳过
            elif match is True:
                # LLM 确认相关，抓正文生成高质量 AI 摘要
                article_text = ""
                if link:
                    try:
                        from article_parser import fetch_article
                        article = fetch_article(link)
                        article_text = (article.get("text") or "")[:50000] if article else ""
                    except Exception:
                        pass
                try:
                    llm_sum = summarize_with_llm(
                        article_text or summary_rss,
                        topic_hint=group_name,
                        max_sentences=3
                    )
                    item["summary"] = llm_sum or (summarize(article_text, sentences=3) if article_text else summary_rss) or summary_rss
                except Exception:
                    item["summary"] = summarize(article_text, sentences=3) if article_text else summary_rss
                result.append(item)
                continue
            # match is None：LLM 调用失败，降级到传统方法

        # ── 传统回退路径（LLM 不可用或单次调用失败） ─────────────────────────
        if not link:
            continue
        try:
            from article_parser import fetch_article
            article = fetch_article(link)
        except Exception:
            continue
        if not article:
            continue
        text = (article.get("text") or "")[:50000]
        title = item.get("title") or article.get("title") or ""
        if not text or len(text) < 100:
            continue

        try:
            from entity_extractor import extract_entities, write_entity
            entity_names = extract_entities(text)
        except Exception:
            entity_names = []

        if not _all_tags_in_article(tags, title, summary_rss, entity_names):
            continue

        # 摘要：尝试 LLM，回退 sumy
        try:
            from llm_summary import summarize_with_llm
            llm_sum = summarize_with_llm(text, topic_hint=group_name, max_sentences=3)
            item["summary"] = llm_sum or summarize(text, sentences=3) or summary_rss or text[:200]
        except Exception:
            try:
                item["summary"] = summarize(text, sentences=3) or summary_rss or text[:200]
            except Exception:
                item["summary"] = summary_rss or text[:200]

        for e in entity_names:
            try:
                from entity_extractor import write_entity
                write_entity(BASE, e, date_str)
            except Exception:
                pass
        result.append(item)

    return result


def _build_my_following(daily_news_by_cat, keyword_groups, relevance_threshold, BASE, date_str, translate_zh_to_en_fn):
    """
    合并单标签（AI相关性/字符串匹配）与多标签（AI主题判断/实体提取）结果。
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

    # 1) 每日新闻：从 OPML 拉取全部，同步记录 URL 健康状态
    health = FeedHealthTracker()
    daily_news = _fetch_all_daily_news(health_tracker=health)
    if daily_news:
        write_daily_news(BASE, daily_news)

    # 健康检查：删除连续超时的失效源（有足够正常请求才操作）
    dead = health.get_dead_urls()
    if dead:
        health.prune_opml(dead)

    # 2) 我的关注：AI 筛选（OpenClaw 可用时）或传统关键词匹配（回退）
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
