# 无 OpenAI key 的摘要（sumy 依赖 NLTK punkt）

import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

# 确保 NLTK 分词数据存在（sumy 依赖，首次运行会自动下载）
def _ensure_nltk():
    for name in ("punkt_tab", "punkt"):
        try:
            nltk.download(name, quiet=True)
        except Exception:
            pass

_ensure_nltk()


def summarize(text, sentences=5):
    if not text or not isinstance(text, str):
        return ""
    text = text[:100_000]
    parser = PlaintextParser.from_string(text, Tokenizer("english"))

    summarizer = LsaSummarizer()

    summary = summarizer(parser.document, sentences)

    result = []

    for s in summary:
        result.append(str(s))

    return " ".join(result)