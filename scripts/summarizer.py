#无 OpenAI key 的摘要。

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

def summarize(text, sentences=5):

    parser = PlaintextParser.from_string(text, Tokenizer("english"))

    summarizer = LsaSummarizer()

    summary = summarizer(parser.document, sentences)

    result = []

    for s in summary:
        result.append(str(s))

    return " ".join(result)