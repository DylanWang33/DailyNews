# 每日新闻 + 我的关注：写入 Obsidian markdown
# 特性：增量追加（只写新条目）、卡片式排版、YAML frontmatter

import os
import re
import datetime


def clean_filename(name):
    if not name or not isinstance(name, str):
        return "untitled"
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return (name.strip() or "untitled")[:80]


# ── 格式化单条新闻 ─────────────────────────────────────────────────────────────

def _format_item(number: int, item: dict, include_summary: bool) -> str:
    """
    格式化单条新闻为优化的卡片式 markdown（HTML + CSS）
    视觉层级：
      标题（最大 + 最深色）
      ↓
      摘要（中等大小）
      ↓
      来源信息（最小 + 最浅色）
    """
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    source = (item.get("source") or "").strip()
    title_original = (item.get("title_original") or "").strip()
    summary = (item.get("summary") or "").strip()
    pub_date = (item.get("pub_date") or "").strip()

    if not title:
        return ""

    lines = []
    lines.append("<div class=\"dailynews-card\">")

    # 标题行：最大 + 最深色
    if link:
        lines.append(f"<span class=\"card-title\">{number}. <a href=\"{link}\">{title}</a></span>")
    else:
        lines.append(f"<span class=\"card-title\">{number}. {title}</span>")

    # 原标题（英文源翻译为中文后保留原文）
    if title_original and title_original != title:
        lines.append(f"<span class=\"card-original-title\">{title_original}</span>")

    # 摘要：中等大小
    if include_summary and summary:
        # 限制长度，超长摘要截断
        summary_text = summary[:300].replace("\n", " ")
        lines.append(f"<span class=\"card-summary\">{summary_text}</span>")

    # 元信息行：最小 + 最浅色
    meta = []
    if source:
        meta.append(f"<span class=\"card-meta-item\">📰 {source}</span>")
    if pub_date:
        meta.append(f"<span class=\"card-meta-item\">🕐 {pub_date}</span>")
    if meta:
        lines.append(f"<span class=\"card-meta\">{' '.join(meta)}</span>")

    lines.append("</div>")
    lines.append("")

    return "\n".join(lines)


# ── 解析已有文件中的链接 ───────────────────────────────────────────────────────

def _read_existing_links(filepath: str) -> set:
    """从已有 md 文件中提取所有 markdown 链接 URL，用于增量去重。"""
    if not os.path.isfile(filepath):
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return set(re.findall(r'\]\(([^)\s]+)\)', content))
    except Exception:
        return set()


def _count_existing_items(filepath: str) -> int:
    """统计已有文件中的条目数（用于续号）。"""
    if not os.path.isfile(filepath):
        return 0
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return len(re.findall(r'^\*\*\d+\.', content, re.MULTILINE))
    except Exception:
        return 0


# ── 创建新文件 ─────────────────────────────────────────────────────────────────

def _create_file(filepath: str, items: list, source_name: str, include_summary: bool):
    """创建全新文件，写入 frontmatter + 所有条目。"""
    now_str = datetime.datetime.now().strftime("%H:%M")
    date_str = datetime.date.today().isoformat()
    lines = [
        "---",
        f"source: {source_name}",
        f"date: {date_str}",
        f'updated: "{now_str}"',
        f"count: {len(items)}",
        "---",
        "",
        f"# {source_name}",
        "",
    ]
    for i, item in enumerate(items, 1):
        block = _format_item(i, item, include_summary)
        if block:
            lines.append(block)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── 增量追加到已有文件 ─────────────────────────────────────────────────────────

def _append_to_file(filepath: str, new_items: list, include_summary: bool):
    """向已有文件追加新条目，更新 frontmatter 中的 count 和 updated。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    existing_count = _count_existing_items(filepath)
    now_str = datetime.datetime.now().strftime("%H:%M")

    # 更新 frontmatter
    content = re.sub(r'^count: \d+', f'count: {existing_count + len(new_items)}', content, flags=re.MULTILINE)
    content = re.sub(r'^updated: ".*?"', f'updated: "{now_str}"', content, flags=re.MULTILINE)

    # 在文件末尾追加新条目
    content = content.rstrip() + "\n\n"
    for i, item in enumerate(new_items, existing_count + 1):
        block = _format_item(i, item, include_summary)
        if block:
            content += block + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ── 核心写入函数（增量） ───────────────────────────────────────────────────────

def _write_items_to_file(BASE: str, filepath: str, items: list,
                         title: str = None, include_summary: bool = False):
    """
    增量写入：若文件已存在，只追加链接不在文件中的新条目；
    否则创建新文件。
    """
    base_real = os.path.realpath(BASE)
    if not os.path.realpath(filepath).startswith(base_real):
        return

    source_name = title or ""

    # 读取已有链接，过滤掉重复条目
    existing_links = _read_existing_links(filepath)
    new_items = [it for it in items if (it.get("link") or "") not in existing_links]

    if not new_items:
        return  # 没有新内容，跳过写入

    if os.path.isfile(filepath):
        _append_to_file(filepath, new_items, include_summary)
    else:
        _create_file(filepath, new_items, source_name, include_summary)


# ── 公开写入接口 ───────────────────────────────────────────────────────────────

def write_daily_news(BASE: str, category_items: dict):
    """
    写入 每日新闻/日期/分类/具体网站.md（增量追加，只写新条目）
    category_items: {"新闻": {"求是网": [items], ...}, "科技": {...}, ...}
    """
    today = datetime.date.today().isoformat()
    base_dir = os.path.join(BASE, "每日新闻", today)
    base_real = os.path.realpath(BASE)
    os.makedirs(base_dir, exist_ok=True)

    for category_name, sources in (category_items or {}).items():
        if not isinstance(sources, dict):
            continue
        cat_dir = os.path.join(base_dir, clean_filename(category_name) or "其他")
        if not os.path.realpath(cat_dir).startswith(base_real):
            continue
        os.makedirs(cat_dir, exist_ok=True)

        for source_name, items in sources.items():
            if not items:
                continue
            filepath = os.path.join(cat_dir, f"{clean_filename(source_name) or '未命名'}.md")
            if not os.path.realpath(filepath).startswith(base_real):
                continue
            _write_items_to_file(BASE, filepath, items, title=source_name, include_summary=True)
            print("daily_news saved:", filepath)


def write_my_following(BASE: str, date_str: str, keyword_items: dict):
    """
    写入 我的关注/日期/关键词.md（增量追加）
    keyword_items: {"油价": [items], "美国;伊朗": [items], ...}
    """
    follow_base = os.path.join(BASE, "我的关注", date_str)
    base_real = os.path.realpath(BASE)
    os.makedirs(follow_base, exist_ok=True)

    for keyword, items in (keyword_items or {}).items():
        if not items:
            continue
        filepath = os.path.join(follow_base, f"{clean_filename(keyword) or '未命名'}.md")
        if not os.path.realpath(filepath).startswith(base_real):
            continue
        _write_items_to_file(BASE, filepath, items, title=keyword, include_summary=True)
        print("my_following saved:", filepath)


# 兼容旧名
def write_hot_by_category(BASE, category_items):
    write_daily_news(BASE, category_items)
