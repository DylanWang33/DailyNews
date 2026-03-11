# Bloomberg 抓取模块

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

def fetch_bloomberg(url):

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code != 200:
            print("skip:", url)
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.find("title").text.strip()

        # 多个正文选择器
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
            # fallback
            paragraphs = soup.find_all("p")
        else:
            paragraphs = article.find_all("p")

        text = "\n".join(p.get_text(strip=True) for p in paragraphs)

        if len(text) < 300:
            print("skip short:", url)
            return None

        return {
            "title": title,
            "text": text,
            "url": url
        }

    except Exception as e:
        print("bloomberg error:", e)
        return None