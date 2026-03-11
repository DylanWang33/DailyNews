import datetime
import os
import subprocess

base = "/Users/kryss/DailyNewsRepo"

today = datetime.date.today().isoformat()

path = os.path.join(base, "news", f"{today}.md")

os.makedirs(os.path.dirname(path), exist_ok=True)

with open(path, "w") as f:
    f.write("# Daily News\n")

print("created:", path)

def run(cmd):
    subprocess.run(cmd, check=False)

run(["git","add","."])
run(["git","commit","-m","auto news"])
run(["git","push"])