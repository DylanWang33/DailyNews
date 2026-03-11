# 今日热点（趋势分析，捕捉真正有价值的文章）

from collections import Counter
import jieba


def analyze(articles):

    words = []

    for art in articles:
        ws = jieba.lcut(art["summary"])
        words.extend(ws)

    freq = Counter(words)

    return freq.most_common(20)