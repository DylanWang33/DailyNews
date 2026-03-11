# 实体识别

import spacy
import os

nlp = spacy.load("en_core_web_sm")

def extract_entities(text):

    doc = nlp(text)

    entities=[]

    for ent in doc.ents:

        if ent.label_ in ["PERSON","ORG","GPE"]:
            entities.append(ent.text)

    return list(set(entities))


def write_entity(base, entity):

    path=f"{base}/entities/{entity}.md"

    if not os.path.exists(path):

        with open(path,"w") as f:

            f.write(f"# {entity}\n\nentity type: unknown\n")