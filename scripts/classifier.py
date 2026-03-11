# 简单分类器。

def classify(text):

    text = text.lower()

    if "fed" in text or "inflation" in text:
        return "macro"

    if "war" in text or "military" in text:
        return "geopolitics"

    if "ai" in text or "chip" in text:
        return "tech"

    return "general"