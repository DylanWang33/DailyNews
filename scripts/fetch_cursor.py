# 断点续抓：记录上次抓取位置，下次从该位置继续；全部轮询完后从头开始并依赖去重

import os
import json

from config import PROJECT_ROOT

CURSOR_FILE = os.path.join(PROJECT_ROOT, "cache", "fetch_cursor.json")


def _ensure_dir():
    d = os.path.join(PROJECT_ROOT, "cache")
    os.makedirs(d, exist_ok=True)


def load_cursor(total_sources):
    """返回 (last_source_index, last_item_index)，若已轮询完或文件无效则返回 (0, 0)。"""
    if not os.path.isfile(CURSOR_FILE):
        return 0, 0
    try:
        with open(CURSOR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        si = int(data.get("last_source_index", 0))
        ii = int(data.get("last_item_index", 0))
        if si < 0 or ii < 0 or si >= total_sources:
            return 0, 0
        return si, ii
    except Exception:
        return 0, 0


def save_cursor(source_index, item_index, total_sources):
    """保存游标。若已到最后一源的最后一条，则保存为 (0, 0) 表示下一轮从头开始。"""
    _ensure_dir()
    if source_index >= total_sources - 1 and item_index >= 0:
        source_index, item_index = 0, 0
    with open(CURSOR_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_source_index": source_index, "last_item_index": item_index}, f, ensure_ascii=False)


def save_cursor_after_item(source_index, item_index):
    """每处理完一条后调用，供下次从此之后继续。"""
    _ensure_dir()
    with open(CURSOR_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_source_index": source_index, "last_item_index": item_index}, f, ensure_ascii=False)


def reset_cursor():
    """全部轮询完毕时调用，下次从头开始。"""
    save_cursor_after_item(0, 0)
