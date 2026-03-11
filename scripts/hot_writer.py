# 每日新闻 + 我的关注：按分类/关键词写入 Obsidian，仅标题+链接（可带摘要）

import os
import datetime
import re


def clean_filename(name):
    if not name or not isinstance(name, str):
        return "untitled"
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    return (name.strip() or "untitled")[:80]


def _write_items_to_file(BASE, filepath, items, title=None, include_summary=False):
    base_real = os.path.realpath(BASE)
    filepath_real = os.path.realpath(filepath)
    if not filepath_real.startswith(base_real):
        return
    lines = []
    if title:
        lines.append(f"# {title}\n")
    for i, item in enumerate(items, 1):
        title_str = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        source = (item.get("source") or "").strip()
        title_original = (item.get("title_original") or "").strip()
        summary = (item.get("summary") or "").strip()
        if not title_str:
            continue
        if link:
            lines.append(f"{i}. [{title_str}]({link})")
        else:
            lines.append(f"{i}. {title_str}")
        if title_original and title_original != title_str:
            lines.append(f"   原标题：{title_original}")
        if include_summary and summary:
            lines.append(f"   {summary[:300]}")
        if source:
            lines.append(f"   来源：{source}")
        lines.append("")
    if not lines:
        return
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_daily_news(BASE, category_items):
    """
    写入 每日新闻/日期/分类标题/具体网站.md（仅标题+链接，无正文抓取）
    category_items: {"新闻": {"求是网": [items], ...}, "科技": {...}, ...}
    """
    today = datetime.date.today().isoformat()
    base_dir = os.path.join(BASE, "每日新闻", today)
    base_real = os.path.realpath(BASE)
    os.makedirs(base_dir, exist_ok=True)
    for category_name, sources in (category_items or {}).items():
        if not isinstance(sources, dict):
            continue
        cat_safe = clean_filename(category_name) or "其他"
        cat_dir = os.path.join(base_dir, cat_safe)
        if not os.path.realpath(cat_dir).startswith(base_real):
            continue
        os.makedirs(cat_dir, exist_ok=True)
        for source_name, items in sources.items():
            if not items:
                continue
            name_safe = clean_filename(source_name) or "未命名"
            filepath = os.path.join(cat_dir, f"{name_safe}.md")
            if not os.path.realpath(filepath).startswith(base_real):
                continue
            _write_items_to_file(BASE, filepath, items, title=source_name, include_summary=True)
            print("daily_news saved:", filepath)


def write_my_following(BASE, date_str, keyword_items):
    """
    写入 我的关注/日期/关键词.md；keyword_items: {"美伊战争": [items], "石油": [items], ...}
    不在 Obsidian 中显示 relevance 标记。
    """
    follow_base = os.path.join(BASE, "我的关注", date_str)
    base_real = os.path.realpath(BASE)
    os.makedirs(follow_base, exist_ok=True)
    for keyword, items in (keyword_items or {}).items():
        if not items:
            continue
        name_safe = clean_filename(keyword) or "未命名"
        filepath = os.path.join(follow_base, f"{name_safe}.md")
        if not os.path.realpath(filepath).startswith(base_real):
            continue
        _write_items_to_file(BASE, filepath, items, title=keyword, include_summary=True)
        print("my_following saved:", filepath)


# 兼容旧名
def write_hot_by_category(BASE, category_items):
    """兼容：写入 每日新闻（原今日热点）。"""
    write_daily_news(BASE, category_items)
