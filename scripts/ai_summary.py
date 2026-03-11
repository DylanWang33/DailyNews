# AI自动总结

from transformers import pipeline

summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"
)

def summarize(text):

    if len(text) > 3000:
        text = text[:3000]

    result = summarizer(
        text,
        max_length=120,
        min_length=40,
        do_sample=False
    )

    return result[0]["summary_text"]