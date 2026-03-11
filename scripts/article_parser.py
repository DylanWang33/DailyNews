# 抓全文。 需要安装 pip install newspaper3k

from newspaper import Article, Config

def fetch_article(url):

    config = Config()

    config.browser_user_agent = "Mozilla/5.0"

    try:

        article = Article(url, config=config)

        article.download()
        article.parse()

        return {
            "title": article.title,
            "text": article.text,
            "authors": article.authors
        }

    except Exception as e:

        print("skip:", url)

        return None