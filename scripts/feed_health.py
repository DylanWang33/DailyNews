# RSS 源健康管理：追踪连续超时，自动备份并从 OPML 删除死链接

import os
import json
import shutil
import datetime
import xml.etree.ElementTree as ET

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATE_FILE = os.path.join(_ROOT, "state", "rss_health.json")
_OPML_PATH = os.path.join(_ROOT, "rss", "feeds-all.opml")
_TIMEOUT_THRESHOLD = 3   # 连续超时次数阈值
_MIN_OK_TO_CONFIRM = 5   # 至少这么多 URL 正常才算"网络可用"


class FeedHealthTracker:
    """
    跟踪每个 RSS URL 的连续超时次数。
    规则：某 URL 连续超时 ≥ 3 次，且本次运行中其他 URL 有 ≥ 5 个正常响应，
    则认为网络可用、该域名有问题，标记为待删除。
    """

    def __init__(self):
        self._state = self._load_state()   # {url: {"consecutive_timeouts": N}}
        self._session_ok = 0               # 本次运行成功数
        self._session_results: dict[str, str] = {}  # url → "ok"|"timeout"|"error"

    # ── 记录结果 ──────────────────────────────────────────────────────────────

    def record(self, url: str, result: str):
        """result: "ok" | "timeout" | "error" """
        url = url.strip()
        self._session_results[url] = result
        entry = self._state.setdefault(url, {"consecutive_timeouts": 0})

        if result == "ok":
            self._session_ok += 1
            entry["consecutive_timeouts"] = 0
            entry["last_ok"] = datetime.datetime.now().isoformat()
        elif result == "timeout":
            entry["consecutive_timeouts"] = entry.get("consecutive_timeouts", 0) + 1
            entry["last_timeout"] = datetime.datetime.now().isoformat()
        else:
            # 普通网络错误不累计超时计数，但也不清零
            entry["last_error"] = datetime.datetime.now().isoformat()

        self._save_state()

    # ── 判断死链接 ────────────────────────────────────────────────────────────

    def get_dead_urls(self) -> list[str]:
        """返回需要从 OPML 删除的 URL 列表。"""
        if self._session_ok < _MIN_OK_TO_CONFIRM:
            return []   # 网络本身可能有问题，不删除任何源
        dead = []
        for url, info in self._state.items():
            if info.get("consecutive_timeouts", 0) >= _TIMEOUT_THRESHOLD:
                dead.append(url)
        return dead

    # ── OPML 清理 ─────────────────────────────────────────────────────────────

    def prune_opml(self, dead_urls: list[str]) -> int:
        """
        备份 OPML，然后删除 dead_urls 对应条目。
        返回实际删除的条目数。
        """
        if not dead_urls or not os.path.isfile(_OPML_PATH):
            return 0

        dead_set = set(u.strip() for u in dead_urls)

        # 备份
        date_str = datetime.date.today().isoformat()
        backup = _OPML_PATH + f".bak.{date_str}"
        if not os.path.isfile(backup):          # 同一天只备份一次
            shutil.copy2(_OPML_PATH, backup)
            print(f"  [健康检查] OPML 已备份到 {os.path.basename(backup)}")

        # 解析 & 删除
        ET.register_namespace("", "")
        tree = ET.parse(_OPML_PATH)
        root = tree.getroot()
        removed = 0

        for cat in list(root.iter("outline")):
            for child in list(cat):
                if child.tag == "outline":
                    xml_url = (child.get("xmlUrl") or "").strip()
                    if xml_url in dead_set:
                        cat.remove(child)
                        removed += 1
                        print(f"  [健康检查] 已删除失效源：{child.get('text', xml_url)}")
                        # 同时清除状态记录，避免下次误删
                        self._state.pop(xml_url, None)

        if removed:
            tree.write(_OPML_PATH, encoding="unicode", xml_declaration=True)
            self._save_state()
            print(f"  [健康检查] 共删除 {removed} 个连续超时源（备份已保存）")

        return removed

    # ── 内部 I/O ──────────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        try:
            if os.path.isfile(_STATE_FILE):
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
            with open(_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
