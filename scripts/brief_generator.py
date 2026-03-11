# Daily Brief：针对关键词过滤后的新闻做 AI 简报总结，写入 Briefs 文件夹

from pathlib import Path
import datetime


def generate_brief(base_path, articles):
    """
    始终在 BASE/briefs/ 下生成当日简报；无文章时也写入说明。
    内容为关键词过滤后的新闻摘要汇总，便于在 Obsidian 中查看。
    """
    today = datetime.date.today().isoformat()
    base = Path(base_path)
    briefs_dir = base / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    brief_file = briefs_dir / f"{today}.md"

    with open(brief_file, "w", encoding="utf-8") as f:
        f.write(f"# Daily Brief {today}\n\n")
        if not articles:
            f.write("今日无匹配关键词的新闻。\n\n")
            f.write("可在 `config.yaml` 中调整 `keywords` 或关闭关键词过滤（留空）以获取更多新闻。\n")
            print("brief saved (empty):", brief_file)
            return
        f.write("以下为今日**关键词过滤后**的新闻摘要。\n\n---\n\n")
        for art in articles:
            f.write(f"## {art['title']}\n\n")
            f.write(f"{art['summary']}\n\n")
            f.write(f"[阅读原文]({art['url']})\n\n")
    print("brief saved:", brief_file)
