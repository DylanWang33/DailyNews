# 抓全文。 需要安装 pip install newspaper3k

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}


def fetch_article(url):

    try:

        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code != 200:
            print("skip:", url)
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.text if soup.title else "No title"

        paragraphs = soup.find_all("p")

        text = "\n".join([p.get_text() for p in paragraphs])

        if len(text) < 200:
            print("skip short:", url)
            return None

        return {
            "title": title,
            "text": text
        }

    except Exception as e:

        print("parse error:", url, e)

        return None