# 生成 obsidian Markdown

import os
import datetime
import re


def clean_filename(name):

    name = re.sub(r"[\\/*?:\"<>|]", "", name)

    return name[:120]


def write_news(BASE, title, summary, cn_text, original_text, entities, link, score):

    today = datetime.date.today().isoformat()

    news_dir = os.path.join(BASE, "news", today)

    os.makedirs(news_dir, exist_ok=True)

    filename = clean_filename(title) + ".md"

    filepath = os.path.join(news_dir, filename)

    entity_links = " ".join([f"[[{e}]]" for e in entities])

    content = f"""
# {title}

source: {link}

score: {score}

entities:
{entity_links}

---

# 中文摘要

{summary}

---

# 中文全文

{cn_text}

---

# 原始英文

{original_text}

"""

    with open(filepath, "w", encoding="utf-8") as f:

        f.write(content)

    print("saved:", filepath)