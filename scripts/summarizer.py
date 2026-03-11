# 无 OpenAI key 的摘要（sumy 依赖 NLTK punkt）

import re
import warnings
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

# 避免 LSA 在短文上报警/报错
warnings.filterwarnings("ignore", message=".*Number of words.*lower than number of sentences.*", module="sumy")

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
    word_count = len(re.findall(r"\b\w+\b", text))
    # 句子数不能超过可用词量，否则 LSA 会警告或报错
    sentences = max(1, min(sentences, max(1, word_count // 15)))
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentences)
        result = [str(s) for s in summary]
        return " ".join(result) if result else text[:300]
    except Exception:
        return text[:300]