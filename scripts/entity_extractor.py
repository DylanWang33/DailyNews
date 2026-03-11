# 实体识别 + 安全写入（防止路径穿越）

import os
import re
import spacy

nlp = spacy.load("en_core_web_sm")

# 文件名非法字符，实体名只保留安全字符
SAFE_ENTITY_PATTERN = re.compile(r"[^\w\u4e00-\u9fff\-\.\s]")


def _sanitize_entity_for_path(name):
    """避免 ../ 等路径穿越，只保留安全字符。"""
    if not name or not isinstance(name, str):
        return "unknown"
    s = SAFE_ENTITY_PATTERN.sub("", name.strip())
    return s[:100] or "unknown"


def extract_entities(text):
    if not text:
        return []
    doc = nlp(text[:50000])
    entities = []
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "ORG", "GPE"):
            entities.append(ent.text)
    return list(set(entities))


def write_entity(base, entity):
    safe_name = _sanitize_entity_for_path(entity)
    path = os.path.join(base, "entities", safe_name + ".md")
    # 确保路径仍在 base 下
    base_real = os.path.realpath(base)
    path_real = os.path.realpath(path)
    if not path_real.startswith(base_real):
        return
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {entity}\n\nentity type: unknown\n")
