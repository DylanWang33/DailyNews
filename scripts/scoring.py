def score_news(article):

    score = 0

    keywords = [
        "war",
        "ai",
        "chip",
        "military",
        "sanction",
        "inflation"
    ]

    text = article["text"].lower()

    for k in keywords:

        if k in text:
            score += 2

    entity_count = len(article["entities"])

    score += entity_count

    return score
