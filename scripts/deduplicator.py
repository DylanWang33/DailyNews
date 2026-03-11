# 去重：标题 + URL 双重去重，标题规范化，避免重复与 paywall 占位

import hashlib
import os
import re
import json

from config import PROJECT_ROOT

CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "hash_db.json")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _normalize(s):
    """统一空白、去除首尾，便于同一标题不同写法判为重复"""
    if not s or not isinstance(s, str):
        return ""
    return re.sub(r"\s+", " ", s.strip())


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def save_cache(cache):
    _ensure_cache_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(cache), f, ensure_ascii=False)


def is_duplicate(title, url=None):
    """
    基于标题和 URL 去重：任一已出现过则视为重复。
    标题会做规范化（空白、首尾）再算 hash。
    """
    cache = load_cache()
    norm_title = _normalize(title)
    if norm_title:
        h_title = hashlib.sha256(norm_title.encode("utf-8")).hexdigest()
        if h_title in cache:
            return True
    if url and isinstance(url, str) and url.strip():
        h_url = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
        if h_url in cache:
            return True

    # 新项：写入缓存
    if norm_title:
        cache.add(hashlib.sha256(norm_title.encode("utf-8")).hexdigest())
    if url and isinstance(url, str) and url.strip():
        cache.add(hashlib.sha256(url.strip().encode("utf-8")).hexdigest())
    save_cache(cache)
    return False


# 通用/付费墙标题：这类标题不同文章相同，直接跳过不抓
SKIP_TITLES = frozenset({
    "subscribe to read",
    "subscribe to read.",
    "sign in",
    "log in",
    "loading...",
    "breaking news",
    "no title",
})


def should_skip_title(title):
    """过滤无信息量的通用标题，减少重复与噪音"""
    if not title or not isinstance(title, str):
        return True
    t = _normalize(title).lower()
    if not t or len(t) < 3:
        return True
    if t in SKIP_TITLES:
        return True
    return False
