def build_links(entities):

    links = []

    for e in entities:

        e = e.replace(" ", "_")

        links.append(f"[[{e}]]")

    return " ".join(links)
