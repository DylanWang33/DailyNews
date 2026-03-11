# 事件抽取，新闻真正价值在于事件结构：Actor、Action、Object、Location、Time

import spacy

nlp = spacy.load("en_core_web_sm")

def extract_event(text):

    doc = nlp(text)

    subject=None
    verb=None
    obj=None

    for token in doc:

        if "subj" in token.dep_:
            subject=token.text

        if token.pos_=="VERB":
            verb=token.text

        if "obj" in token.dep_:
            obj=token.text

    return {
        "subject":subject,
        "verb":verb,
        "object":obj
    }