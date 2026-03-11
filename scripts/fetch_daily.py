import os
import datetime

BASE = "/Users/kryss/DailyNewsRepo"

news_dir = os.path.join(BASE, "news")
os.makedirs(news_dir, exist_ok=True)

now = datetime.datetime.now()
date = now.strftime("%Y-%m-%d")
time = now.strftime("%H%M")

filename = f"{date}_{time}.md"
filepath = os.path.join(news_dir, filename)

content = f"""# Daily News {date}

生成时间: {now}

---

## 今日要闻

- 示例新闻1
- 示例新闻2
- 示例新闻3

"""

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("created:", filepath)