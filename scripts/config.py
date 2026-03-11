# 项目配置：路径与安全常量
# 优先读仓库内 config.yaml，其次环境变量，最后用项目根

import os

# 脚本所在目录 → 项目根目录（DailyNewsRepo）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")


def get_project_root():
    """始终返回项目根目录，并确保进程 CWD 为项目根（便于快捷指令任意目录执行）。"""
    root = os.path.abspath(PROJECT_ROOT)
    if os.getcwd() != root:
        os.chdir(root)
    return root


def _read_config():
    """从仓库根 config.yaml 读取配置（可选）。"""
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        import yaml
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_config(key, default=None):
    """读取 config.yaml 中的单项，如 get_config('max_articles_per_run', 30)。"""
    return _read_config().get(key, default)


def _read_obsidian_base_from_config():
    """从仓库根目录 config.yaml 读取 obsidian_base（可选）。"""
    path = _read_config().get("obsidian_base")
    if path and os.path.isdir(str(path).strip()):
        return os.path.abspath(str(path).strip())
    return None


def get_obsidian_base():
    """
    Obsidian 笔记库根目录。顺序：
    1) 仓库根 config.yaml 里的 obsidian_base
    2) 环境变量 DAILY_NEWS_OBSIDIAN_BASE
    3) 项目根（news/briefs 在 DailyNewsRepo 内）
    """
    base = _read_obsidian_base_from_config()
    if base:
        return base
    base = os.environ.get("DAILY_NEWS_OBSIDIAN_BASE", "").strip()
    if base and os.path.isdir(base):
        return os.path.abspath(base)
    return get_project_root()


# 安全：允许的 URL 协议
ALLOWED_URL_SCHEMES = ("http", "https")

# 请求超时（秒）
REQUEST_TIMEOUT = 25

# 单篇文章最大正文长度（字符），防止内存滥用
MAX_ARTICLE_LENGTH = 500_000


def get_fetch_delay():
    """反爬延迟（秒），从 config.yaml 的 fetch_delay_min / fetch_delay_max 读取，默认 0.2～0.5 以加快捕获。"""
    cfg = _read_config()
    lo = cfg.get("fetch_delay_min")
    hi = cfg.get("fetch_delay_max")
    if lo is not None and hi is not None:
        try:
            return float(lo), float(hi)
        except (TypeError, ValueError):
            pass
    return 0.2, 0.5
