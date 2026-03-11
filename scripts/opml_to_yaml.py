# 将 rss/feeds-all.opml 转为 sources/rss.yaml（保留所有源，中文分类标 lang: zh）

import os
import xml.etree.ElementTree as ET
import html

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPML_PATH = os.path.join(_REPO, "rss", "feeds-all.opml")
YAML_PATH = os.path.join(_REPO, "sources", "rss.yaml")

# 中文分类（OPML 里 outline 的 text）：这些分类下的源标 lang: zh
ZH_CATEGORIES = {
    "新闻", "科技", "知识", "娱乐", "财经", "生活", "编程", "外国媒体", "公众号"
}


def _collect_outlines(parent, parent_title=""):
    out = []
    for child in parent:
        if child.tag != "outline":
            continue
        title = (child.get("title") or child.get("text") or "").strip()
        title = html.unescape(title)
        xml_url = (child.get("xmlUrl") or "").strip()
        if xml_url:
            out.append((title, xml_url, parent_title))
        else:
            cat = (child.get("text") or child.get("title") or "").strip()
            cat = html.unescape(cat)
            out.extend(_collect_outlines(child, cat))
    return out


def main():
    tree = ET.parse(OPML_PATH)
    root = tree.getroot()
    body = root.find(".//body")
    if body is None:
        body = root
    items = _collect_outlines(body)
    os.makedirs(os.path.dirname(YAML_PATH), exist_ok=True)
    lines = [
        "# RSS 源（由 rss/feeds-all.opml 生成，与 OPML 内容一致）",
        "# 中文分类下源带 lang: zh，抓取时优先。",
        "",
    ]
    for title, url, parent in items:
        name = title.replace("'", "'").replace("&amp;", "&")
        entry = f"- name: \"{name}\"\n  url: {url}"
        if parent and parent in ZH_CATEGORIES:
            entry += "\n  lang: zh"
        lines.append(entry)
        lines.append("")
    with open(YAML_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Written", len(items), "feeds to", YAML_PATH)


if __name__ == "__main__":
    main()
