# 抓全文（仅允许 http/https，限制超时与长度）

import re
import requests
from bs4 import BeautifulSoup

from config import ALLOWED_URL_SCHEMES, MAX_ARTICLE_LENGTH

def _timeout():
    try:
        from config import get_config
        t = get_config("request_timeout")
        return int(t) if t is not None else 25
    except Exception:
        return 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}


def _is_safe_url(url):
    """只允许 http/https，防止 file:// 或内网请求。"""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return any(url.lower().startswith(s + "://") for s in ALLOWED_URL_SCHEMES)


def fetch_article(url):
    if not _is_safe_url(url):
        print("skip (invalid url):", url[:80])
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=_timeout())
        if r.status_code != 200:
            print("skip:", url[:80], r.status_code)
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.text.strip() if soup.title else "No title"
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs)
        if len(text) < 200:
            print("skip short:", url[:80])
            return None
        text = text[:MAX_ARTICLE_LENGTH]
        return {"title": title, "text": text}
    except Exception as e:
        print("parse error:", url[:80], e)
        return None
