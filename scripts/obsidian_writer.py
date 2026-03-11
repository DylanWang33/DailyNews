# 生成 obsidian Markdown

import os

def write_news(base, title, summary, entities, link, score):

    folder = f"{base}/news"

    os.makedirs(folder, exist_ok=True)

    safe_title = title.replace("/", "")

    file = f"{folder}/{safe_title}.md"

    entity_links = " ".join([f"[[{e}]]" for e in entities])

    md = f"""
# {title}

score: {score}

{entity_links}

{summary}

source: {link}
"""

    with open(file, "w", encoding="utf-8") as f:
        f.write(md)

    print("created:", file)