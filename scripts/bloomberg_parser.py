# Bloomberg 专用解析（仅允许 http/https，统一超时）

import requests
from bs4 import BeautifulSoup

from config import ALLOWED_URL_SCHEMES, get_config, MAX_ARTICLE_LENGTH

def _timeout():
    t = get_config("request_timeout")
    return int(t) if t is not None else 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def _is_safe_url(url):
    if not url or not isinstance(url, str):
        return False
    return any(url.strip().lower().startswith(s + "://") for s in ALLOWED_URL_SCHEMES)


def fetch_bloomberg(url):
    if not _is_safe_url(url):
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=_timeout())
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else "No title"
        selectors = [
            "div[data-component='ArticleBody']",
            "div.body-copy-v2",
            "section.body-copy",
        ]
        article = None
        for sel in selectors:
            article = soup.select_one(sel)
            if article:
                break
        if not article:
            paragraphs = soup.find_all("p")
        else:
            paragraphs = article.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs)
        if len(text) < 300:
            return None
        text = text[:MAX_ARTICLE_LENGTH]
        return {"title": title, "text": text, "url": url}
    except Exception as e:
        print("bloomberg error:", e)
        return None
