# Daily Brief 自动生成

from pathlib import Path
import datetime


def generate_brief(base_path, articles):

    today = datetime.date.today().isoformat()

    base = Path(base_path)
    briefs_dir = base / "briefs"

    # 自动创建目录
    briefs_dir.mkdir(parents=True, exist_ok=True)

    brief_file = briefs_dir / f"{today}.md"

    with open(brief_file, "w", encoding="utf-8") as f:

        f.write(f"# Daily Brief {today}\n\n")

        for art in articles:
            f.write(f"## {art['title']}\n\n")
            f.write(f"{art['summary']}\n\n")
            f.write(f"[Read more]({art['url']})\n\n")

    print("brief saved:", brief_file)