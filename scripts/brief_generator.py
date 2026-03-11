# Daily Brief 自动生成

import glob
import datetime

def generate_brief(base):

    today = datetime.date.today().isoformat()

    files = glob.glob(f"{base}/news/**/*.md", recursive=True)

    lines=[]

    for f in files:

        with open(f) as x:

            txt=x.read()

            if today in txt:
                lines.append(txt.split("\n")[0])

    brief = "# Daily Brief\n\n"

    for l in lines:
        brief+=f"- {l}\n"

    with open(f"{base}/briefs/{today}.md","w") as f:
        f.write(brief)