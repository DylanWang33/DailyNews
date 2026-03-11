# 今日热点：按分类写入 Obsidian，每类最多 10 条，标题为可点击链接

import os
import datetime
import re


def clean_filename(name):
    if not name or not isinstance(name, str):
        return "untitled"
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    return (name.strip() or "untitled")[:80]


def write_hot_list(BASE, items):
    """
    旧接口：items 为平铺列表，写入单文件（兼容）。
    """
    today = datetime.date.today().isoformat()
    hot_dir = os.path.join(BASE, "今日热点", today)
    os.makedirs(hot_dir, exist_ok=True)
    filepath = os.path.join(hot_dir, "热点.md")
    _write_items_to_file(BASE, filepath, items, title=f"今日热点 {today}")


def _write_items_to_file(BASE, filepath, items, title=None):
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
        if not title_str:
            continue
        if link:
            lines.append(f"{i}. [{title_str}]({link})")
        else:
            lines.append(f"{i}. {title_str}")
        if title_original and title_original != title_str:
            lines.append(f"   原标题：{title_original}")
        if source:
            lines.append(f"   来源：{source}")
        lines.append("")
    if not lines:
        return
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_hot_by_category(BASE, category_items):
    """
    写入 今日热点/日期/分类标题/具体网站.md
    category_items: {"新闻": {"求是网": [items], "联合早报": [items]}, "科技": {"36氪": [items]}, ...}
    即：分类名 -> 源名称 -> 条目列表；英文标题会已译为 title，原标题在 title_original。
    """
    today = datetime.date.today().isoformat()
    hot_base = os.path.join(BASE, "今日热点", today)
    base_real = os.path.realpath(BASE)
    os.makedirs(hot_base, exist_ok=True)
    for category_name, sources in (category_items or {}).items():
        if not isinstance(sources, dict):
            continue
        cat_safe = clean_filename(category_name) or "其他"
        cat_dir = os.path.join(hot_base, cat_safe)
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
            _write_items_to_file(BASE, filepath, items, title=source_name)
            print("hot saved:", filepath)
