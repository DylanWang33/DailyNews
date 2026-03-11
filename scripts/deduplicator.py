# 去重系统

import hashlib
import os
import json

CACHE_FILE = "cache/hash_db.json"

def load_cache():

    if not os.path.exists(CACHE_FILE):
        return set()

    with open(CACHE_FILE) as f:
        return set(json.load(f))


def save_cache(cache):

    with open(CACHE_FILE,"w") as f:
        json.dump(list(cache),f)


def is_duplicate(title):

    cache = load_cache()

    h = hashlib.md5(title.encode()).hexdigest()

    if h in cache:
        return True

    cache.add(h)

    save_cache(cache)

    return False