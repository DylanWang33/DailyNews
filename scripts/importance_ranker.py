# 重要度评分系统

def score_news(text, entities):

    score = 0

    keywords = [
        "war",
        "sanctions",
        "inflation",
        "interest rate",
        "ai",
        "semiconductor"
    ]

    for k in keywords:

        if k in text.lower():
            score += 2

    if len(entities) > 5:
        score += 1

    if "president" in text.lower():
        score += 2

    return score