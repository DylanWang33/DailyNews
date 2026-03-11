# Git 同步：安全执行并上报错误（便于快捷指令排错）

import subprocess
import sys
import os

# 在仓库根目录执行
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(cmd, capture=True):
    """执行命令列表，禁止 shell 注入。返回 (returncode, stdout, stderr)。"""
    try:
        out = subprocess.run(
            cmd,
            cwd=_REPO,
            capture_output=capture,
            text=True,
            timeout=120,
        )
        return out.returncode, (out.stdout or ""), (out.stderr or "")
    except FileNotFoundError:
        print("git not found. Install Git or add to PATH.", file=sys.stderr)
        raise
    except subprocess.TimeoutExpired:
        print("git command timed out.", file=sys.stderr)
        raise


def push():
    """add + commit + push。无变更时 commit 会失败，视为正常；push 失败则退出码非 0。"""
    code, _, err = _run(["git", "add", "."])
    if code != 0:
        print(err, file=sys.stderr)
        raise SystemExit(code)

    code, _, err = _run(["git", "commit", "-m", "auto news"])
    if code != 0 and "nothing to commit" not in err.lower():
        print(err, file=sys.stderr)
        raise SystemExit(code)

    code, _, err = _run(["git", "push"])
    if code != 0:
        print(err, file=sys.stderr)
        raise SystemExit(code)
