# 生成 Obsidian Markdown（路径安全，防止穿越）

import os
import sys
import hashlib
import datetime
import re


def clean_filename(name):
    if not name or not isinstance(name, str):
        return "untitled"
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    return (name.strip() or "untitled")[:120]


def write_news(BASE, title_original, summary, cn_text, original_text, entities, link, score, title_cn_for_filename=None):
    """
    title_original: 原标题（英文或原文），会显示在正文顶部。
    title_cn_for_filename: 用于文件名的中文标题；若为空则用 title_original。
    """
    today = datetime.date.today().isoformat()
    news_dir = os.path.join(BASE, "news", today)
    os.makedirs(news_dir, exist_ok=True)

    base_name = clean_filename(title_cn_for_filename or title_original)
    filename = base_name + ".md"
    filepath = os.path.join(news_dir, filename)
    if os.path.exists(filepath):
        suffix = hashlib.sha256((link or title_original).encode("utf-8")).hexdigest()[:8]
        filename = f"{base_name}_{suffix}.md"
        filepath = os.path.join(news_dir, filename)
    base_real = os.path.realpath(BASE)
    filepath_real = os.path.realpath(filepath)
    if not filepath_real.startswith(base_real):
        return

    entity_links = " ".join([f"[[{e}]]" for e in (entities or []) if e])

    content = f"""# 原标题 / Original

{title_original}

---

source: {link}

score: {score}

entities:
{entity_links}

---

# 中文摘要

{summary or ''}

---

# 中文全文

{cn_text or ''}

---

# 原始英文

{original_text or ''}
"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("saved:", filepath)
    except PermissionError:
        print("Permission denied:", filepath, "- 请在项目根执行: chown -R $(whoami) news && chmod -R u+rwX news", file=sys.stderr)
        raise
