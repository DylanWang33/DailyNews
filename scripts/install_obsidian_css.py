#!/usr/bin/env python3
"""
将 obsidian-snippets/daily-news-reader.css 安装到 Obsidian 库的 .obsidian/snippets/
片段必须放在【你当前打开的库】的 vault/.obsidian/snippets 下，Obsidian 才能识别。
"""
import os
import shutil

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(_REPO, "obsidian-snippets", "daily-news-reader.css")


def main():
    if not os.path.isfile(SOURCE):
        print("未找到源文件:", SOURCE)
        return 1
    config_path = os.path.join(_REPO, "config.yaml")
    base = None
    if os.path.isfile(config_path):
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if isinstance(cfg, dict):
                # 片段必须放在【库根】.obsidian/snippets；若配置了 obsidian_vault_root 则用库根，否则用 obsidian_base
                base = (cfg.get("obsidian_vault_root") or cfg.get("obsidian_base") or "").strip()
                base = os.path.expanduser(base) if base else None
        except Exception:
            pass
    if not base or not os.path.isdir(base):
        print("请在 config.yaml 中配置 obsidian_base（你 Obsidian 里打开的「库」的路径）。")
        print("或手动执行（把 VAULT 换成你的库路径）：")
        print("  mkdir -p VAULT/.obsidian/snippets")
        print("  cp", SOURCE, "VAULT/.obsidian/snippets/daily-news-reader.css")
        return 1
    dest_dir = os.path.join(base, ".obsidian", "snippets")
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        print("无法创建目录:", dest_dir)
        print("请手动执行：")
        print("  mkdir -p", repr(dest_dir))
        print("  cp", SOURCE, os.path.join(dest_dir, "daily-news-reader.css"))
        return 1
    dest = os.path.join(dest_dir, "daily-news-reader.css")
    try:
        shutil.copy2(SOURCE, dest)
    except OSError as e:
        print("复制失败:", e)
        print("请手动复制：")
        print("  源:", SOURCE)
        print("  目标:", dest)
        return 1
    print("已安装到:", dest)
    print("在 Obsidian 中：设置 -> 外观 -> CSS 代码片段 -> 重新加载 -> 打开 daily-news-reader")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
